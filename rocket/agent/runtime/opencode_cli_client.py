"""OpenCode CLI backend injection client."""

from __future__ import annotations

import json
import os
import re
import socket
import shutil
import subprocess
import time
import atexit
from dataclasses import asdict
from pathlib import Path
from typing import Any

from agent.runtime.memory import RocketProfile
from agent.runtime.browser_state import BrowserState, parse_mission, task_display_text
from agent.runtime.mission_brief import build_mission_brief, cleanup_policy
from agent.runtime.results import RocketExecutionResult
from agent.runtime.setup import RocketSetup


DEFAULT_OPENCODE_MODELS = (
    "opencode/mimo-v2.5-free",
    "opencode/deepseek-v4-flash-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/north-mini-code-free",
    "opencode/big-pickle",
)

_SERVER_PROCESS: subprocess.Popen[str] | None = None
_SERVER_URL = ""


def _powershell_quote(arg: str) -> str:
    """Single-quote an argument for PowerShell, escaping embedded quotes."""

    return "'" + str(arg).replace("'", "''") + "'"


def _powershell_wrap(command: list[str]) -> list[str]:
    """Wrap an OpenCode command list into a PowerShell (not cmd) invocation."""

    inner = "& " + " ".join(_powershell_quote(part) for part in command)
    return [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        inner,
    ]


class OpenCodeCliClient:
    """Execute Rocket tasks through OpenCode without using any chat UI."""

    def __init__(
        self,
        repo_root: Path,
        profile: RocketProfile,
        setup: RocketSetup | None = None,
        runtime_env: dict[str, str] | None = None,
        history: list[dict[str, Any]] | None = None,
        session_id: str = "",
        browser_state: dict[str, Any] | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.profile = profile
        self.setup = setup or RocketSetup()
        self.runtime_env = runtime_env or {}
        self.history = history or []
        self.session_id = session_id
        self.browser_state = BrowserState.from_dict(browser_state)
        self.command = os.getenv("ROCKET_OPENCODE_COMMAND", "opencode")
        self.agent = os.getenv("ROCKET_OPENCODE_AGENT", "rocket-blind")
        self.models = _configured_models()
        self.model = self.models[0]
        self.timeout_seconds = _configured_timeout()
        self.output_format = os.getenv("ROCKET_OPENCODE_FORMAT", "default").strip().lower() or "default"
        self.print_logs = os.getenv("ROCKET_OPENCODE_PRINT_LOGS", "1").strip().lower() not in {"0", "false", "no"}
        self.persistent_server = (
            os.getenv("ROCKET_OPENCODE_PERSISTENT_SERVER", "1").strip().lower() in {"1", "true", "yes", "on"}
        )
        self.reuse_session = (
            os.getenv("ROCKET_OPENCODE_REUSE_SESSION", "1").strip().lower() in {"1", "true", "yes", "on"}
        )

    def available(self) -> bool:
        return shutil.which(self.command) is not None

    def execute(self, task: str) -> RocketExecutionResult:
        if not self.available():
            return RocketExecutionResult(
                task=task,
                intent="opencode",
                executor="opencode-cli",
                success=False,
                message=f"OpenCode CLI not found: {self.command}",
            )

        prompt = self._build_prompt(task)
        desktop_expectation = _desktop_expectation(task)
        last_result: RocketExecutionResult | None = None
        for model in self.models:
            result = self._execute_once(task, prompt, model, desktop_expectation)
            if _is_verification_failure(result):
                correction_prompt = _correction_prompt(prompt, result)
                corrected = self._execute_once(task, correction_prompt, model, desktop_expectation)
                corrected.details.append("correction_attempted=true")
                return corrected
            if result.success or not _should_try_next_model(result):
                return result
            last_result = result
        return last_result or RocketExecutionResult(task, "opencode", "opencode-cli", False, "OpenCode did not run.")

    def _execute_once(
        self,
        task: str,
        prompt: str,
        model: str,
        desktop_expectation: dict[str, str] | None,
    ) -> RocketExecutionResult:
        command = [
            self.command,
            "run",
            _short_run_message(task),
            "--file",
            str(_write_prompt_file(self._execution_dir(), prompt)),
            "--dir",
            str(self._execution_dir()),
            "--model",
            model,
            "--agent",
            self.agent,
        ]
        if self.output_format in {"json", "default"}:
            command.extend(["--format", self.output_format])
        server_url = self._server_url()
        server_log_offsets = _server_log_offsets(self._execution_dir()) if server_url else {}
        if server_url:
            command.extend(["--attach", server_url])
        if self.reuse_session and self.session_id:
            command.extend(["--session", self.session_id])
        if self.print_logs:
            command.extend(["--print-logs", "--log-level", os.getenv("ROCKET_OPENCODE_LOG_LEVEL", "INFO")])
        command.append("--dangerously-skip-permissions")
        # Attach drawing images directly so the vision model (MIMO) can see them.
        mission = parse_mission(task)
        image_paths = _mission_image_paths(mission)
        for image_path in image_paths:
            if image_path and os.path.exists(image_path):
                command.extend(["--file", image_path])
        env = os.environ.copy()
        env.update(self.runtime_env)
        try:
            completed = subprocess.run(
                _powershell_wrap(command),
                cwd=self._execution_dir(),
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            if self.persistent_server:
                _stop_opencode_server()
            return RocketExecutionResult(
                task=task,
                intent="opencode",
                executor="opencode-cli",
                success=False,
                message=(
                    f"OpenCode timed out after {self.timeout_seconds} seconds. "
                    "Persistent OpenCode server was restarted to stop any runaway desktop actions."
                ),
            )

        stdout_text = completed.stdout or ""
        stderr_text = completed.stderr or ""
        server_log_delta = _server_log_delta(self._execution_dir(), server_log_offsets) if server_url else ""
        session_id = _extract_session_id(stdout_text, stderr_text) or self.session_id
        message = _extract_message(stdout_text)
        if not message and not _has_json_events(stdout_text):
            message = _tail(stdout_text)
        stderr_tail = _tail(stderr_text)
        if completed.returncode != 0:
            message = stderr_tail or message
        server_error = _server_runtime_error_message(server_log_delta)
        if server_error:
            completed_returncode = completed.returncode if completed.returncode != 0 else 1
            completed = CompletedShim(completed_returncode)
            message = server_error
        if not message and completed.returncode == 0:
            message = "Task completed."
        success = completed.returncode == 0 and not _looks_like_failure(message)
        details = [
            f"returncode={completed.returncode}",
            f"model={model}",
            f"agent={self.agent}",
            f"dir={self._execution_dir()}",
        ]
        if server_url:
            details.append(f"attached_server={server_url}")
        if session_id:
            details.append(f"session_id={session_id}")
        if stderr_tail:
            details.append(f"stderr={stderr_tail}")
        if server_error:
            details.append(f"server_error={server_error}")
        if desktop_expectation and success:
            verified, verification_message = _verify_desktop_expectation(desktop_expectation)
            details.append(f"desktop_verification={verification_message}")
            if verified:
                message = verification_message
                cleanup_message = _cleanup_after_success(task, desktop_expectation)
                if cleanup_message:
                    details.append(f"cleanup={cleanup_message}")
            else:
                success = False
                message = (
                    "OpenCode subprocess finished, but Rocket could not verify the desktop action. "
                    f"{verification_message}"
                )
        return RocketExecutionResult(
            task=task,
            intent="opencode",
            executor="opencode-cli",
            success=success,
            message=message or f"OpenCode exited with code {completed.returncode}.",
            details=details,
        )

    def _build_prompt(self, task: str) -> str:
        mission = parse_mission(task)
        instructions = mission.get("instructions", []) if mission else []
        brief = build_mission_brief(task)
        profile = json.dumps(asdict(self.profile), ensure_ascii=True)
        setup = json.dumps(self.setup.to_dict(), ensure_ascii=True)
        history = _compact_history(self.history[-8:])
        browser_state = _compact_browser_context(self.browser_state)
        visible_windows = json.dumps(_visible_window_titles(), ensure_ascii=True)
        credential_names = sorted(self.setup.credential_refs.keys())
        credential_context = ", ".join(credential_names) if credential_names else "none"
        return (
            "HARD RULES (NEVER VIOLATE)\n"
            "1. NEVER open an app that is ALREADY OPEN. Check processes/windows FIRST. "
            "If it exists: FOCUS it, RESTORE it, MAXIMIZE it. NEVER launch a duplicate.\n"
            "2. CLOSE apps after task completion UNLESS the user needs them (YouTube playing, Spotify, active browsing). "
            "Calculator: CLOSE after result. Settings: CLOSE after toggle. Weather: CLOSE tab.\n"
            "3. EVERY window you interact with MUST be MAXIMIZED and in the FOREGROUND. "
            "Never work in small/background/minimized windows. Maximize IMMEDIATELY after focus.\n"
            "4. REUSE over LAUNCH. If Chrome exists, reuse it. If a tab exists for the site, switch to it. "
            "Never open a new window or tab when one already exists for the target.\n"
            "5. Use REAL Chrome with default profile. Never use sandbox/isolated/temporary browsers. "
            "If Chrome is already open, use computer-use/vision tools to control it directly. "
            "Only use Playwright when Chrome is NOT already running.\n"
            "6. ACT FAST. Do NOT reason or plan at length. Execute the action IMMEDIATELY. "
            "One screenshot, one action, verify, done. No multi-paragraph thinking. No step-by-step explanations. "
            "Only reason when the task is genuinely ambiguous or recovery is needed.\n\n"
            f"{brief}\n\n"
            "MISSION INSTRUCTIONS\n"
            f"{_compact_list(instructions)}\n\n"
            "AVAILABLE POWERS\n"
            "Use all configured OpenCode MCP servers, skills, plugins, superpowers, rocket-windows, Playwright/browser "
            "tools, vision/computer-use tools, shokunin-memory, shell, and filesystem tools. Choose the tool that best "
            "proves the user's goal in observable reality.\n\n"
            "WINDOWS APP HINTS\n"
            "For Calculator missions, open the installed Windows Calculator with Start-Process calc.exe or the Windows "
            "app launcher, focus the visible Calculator window, enter the expression, and verify the displayed result. "
            "Do not report success only because a command returned.\n\n"
            "CURRENT CONTEXT\n"
            f"Browser: {browser_state}\n"
            f"Recent execution history: {history}\n"
            f"Visible windows before action: {visible_windows}\n"
            f"Available credential refs: {credential_context}\n"
            f"Current OpenCode session id: {self.session_id or 'new'}\n\n"
            f"Profile: {profile}\n"
            f"Runtime setup: {setup}\n"
        )

    def _execution_dir(self) -> Path:
        if self.setup.full_access:
            return self.repo_root
        workspace = self.setup.workspace
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def _server_url(self) -> str:
        if not self.persistent_server:
            return ""
        return _ensure_opencode_server(self.command, self._execution_dir(), self.runtime_env)


def _extract_message(stdout: str | None) -> str:
    stdout = stdout or ""
    structured = _structured_speech(stdout)
    if structured:
        return structured
    best = ""
    for line in stdout.splitlines():
        line = _strip_ansi(line).strip()
        if not line:
            continue
        try:
            item: Any = json.loads(line)
        except json.JSONDecodeError:
            best = line
            continue
        text = _text_from_json(item)
        if text:
            best = text
    return best.strip()


def _structured_speech(text: str) -> str:
    speech = ""
    content = ""
    for raw_line in text.splitlines():
        line = _strip_ansi(raw_line).strip()
        if line.upper().startswith("SPEECH:"):
            speech = line.split(":", 1)[1].strip()
        elif line.upper().startswith("CONTENT:"):
            content = line.split(":", 1)[1].strip()
    return speech or content


def _short_run_message(task: str) -> str:
    compact = " ".join(task_display_text(task).strip().split())
    if len(compact) > 180:
        compact = compact[:177].rstrip() + "..."
    return (
        "Execute the Rocket desktop task using the attached prompt file. "
        f"Current task: {compact}"
    )


def _write_prompt_file(execution_dir: Path, prompt: str) -> Path:
    prompt_dir = execution_dir / ".rocket" / "opencode-prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    path = prompt_dir / "latest-rocket-task.md"
    path.write_text(prompt, encoding="utf-8")
    return path


def _extract_session_id(*streams: str | None) -> str:
    for stream in streams:
        stream = stream or ""
        for line in stream.splitlines():
            clean = _strip_ansi(line).strip()
            if not clean:
                continue
            try:
                item: Any = json.loads(clean)
            except json.JSONDecodeError:
                match = re.search(r"\bsessionID[=:]\"?([A-Za-z0-9_:-]+)", clean)
                if match:
                    return match.group(1)
                continue
            session_id = _session_id_from_json(item)
            if session_id:
                return session_id
    return ""


def _session_id_from_json(item: Any) -> str:
    if isinstance(item, dict):
        for key in ("sessionID", "sessionId", "session_id"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in item.values():
            nested = _session_id_from_json(value)
            if nested:
                return nested
    if isinstance(item, list):
        for value in item:
            nested = _session_id_from_json(value)
            if nested:
                return nested
    return ""


def _text_from_json(item: Any) -> str:
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return ""
    if item.get("synthetic") is True:
        return ""
    metadata = item.get("metadata")
    if isinstance(metadata, dict) and metadata.get("compaction_continue") is True:
        return ""
    item_type = str(item.get("type", "")).lower()
    if item_type in {"step-start", "step-finish", "tool", "tool-call", "tool-result"}:
        return ""
    part = item.get("part")
    if isinstance(part, dict):
        part_text = _text_from_json(part)
        if part_text:
            return part_text
    for key in ("text", "message", "content", "summary"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    parts = item.get("parts")
    if isinstance(parts, list):
        chunks = [_text_from_json(part) for part in parts]
        return "\n".join(chunk for chunk in chunks if chunk)
    return ""


def _has_json_events(stdout: str | None) -> bool:
    stdout = stdout or ""
    for line in stdout.splitlines():
        clean = _strip_ansi(line).strip()
        if not clean:
            continue
        try:
            item: Any = json.loads(clean)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and ("type" in item or "sessionID" in item or "part" in item):
            return True
    return False


def _tail(text: str | None, limit: int = 1200) -> str:
    text = text or ""
    text = _strip_ansi(text).strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def _compact_list(values: Any) -> str:
    if not isinstance(values, list):
        return "none"
    items = [str(item).strip() for item in values if str(item).strip()]
    return ", ".join(items[:8]) if items else "none"


def _compact_browser_context(state: BrowserState) -> str:
    data = state.to_dict()
    compact = {
        "browser": data.get("current_browser", "chrome"),
        "site": data.get("current_site", ""),
        "tab": data.get("current_tab", 1),
        "previous_tab": data.get("previous_tab"),
        "search_query": data.get("search_query", ""),
        "video_playing": data.get("video_playing", False),
        "browser_open": data.get("browser_open", False),
        "last_action": data.get("last_action", ""),
    }
    return json.dumps(compact, ensure_ascii=True)


def _compact_history(history: list[dict[str, Any]]) -> str:
    compact: list[str] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        task = task_display_text(str(item.get("task") or item.get("display_task") or "").strip())
        message = str(item.get("message", "")).strip()
        success = item.get("success")
        if task:
            compact.append(f"{task} => success={success}; {message[:120]}")
    return json.dumps(compact[-8:], ensure_ascii=True)


def _strip_ansi(text: str | None) -> str:
    text = text or ""
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def _looks_like_failure(message: str) -> bool:
    lower = message.lower()
    failure_markers = (
        "cannot perform this task",
        "unable to complete",
        "failed to",
        "could not",
        "error:",
        "not able to",
    )
    return any(marker in lower for marker in failure_markers)


def _configured_models() -> list[str]:
    configured = os.getenv("ROCKET_OPENCODE_MODELS", "") or os.getenv("ROCKET_OPENCODE_MODEL", "")
    if not configured.strip():
        return list(DEFAULT_OPENCODE_MODELS)
    models = [item.strip() for item in configured.split(",") if item.strip()]
    return models or list(DEFAULT_OPENCODE_MODELS)


def _configured_timeout() -> int | None:
    value = os.getenv("ROCKET_OPENCODE_TIMEOUT_SECONDS", "120").strip().lower()
    if value in {"0", "none", "false", "no", "off"}:
        return None
    return int(value)


def _ensure_opencode_server(command: str, execution_dir: Path, runtime_env: dict[str, str]) -> str:
    global _SERVER_PROCESS, _SERVER_URL
    host = os.getenv("ROCKET_OPENCODE_SERVER_HOST", "127.0.0.1")
    if _SERVER_PROCESS is not None and _SERVER_PROCESS.poll() is None:
        return _SERVER_URL
    port = _select_server_port(host, int(os.getenv("ROCKET_OPENCODE_SERVER_PORT", "4096")))
    url = f"http://{host}:{port}"

    env = os.environ.copy()
    env.update(runtime_env)
    log_dir = execution_dir / ".rocket"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout = (log_dir / "opencode_server.log").open("a", encoding="utf-8")
    stderr = (log_dir / "opencode_server.err").open("a", encoding="utf-8")
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    _SERVER_PROCESS = subprocess.Popen(
        _powershell_wrap(
            [
                command,
                "serve",
                "--hostname",
                host,
                "--port",
                str(port),
                "--print-logs",
                "--log-level",
                os.getenv("ROCKET_OPENCODE_SERVER_LOG_LEVEL", "INFO"),
            ]
        ),
        cwd=execution_dir,
        env=env,
        text=True,
        stdout=stdout,
        stderr=stderr,
        creationflags=creationflags,
    )
    _SERVER_URL = url
    atexit.register(_stop_opencode_server)
    if not _wait_for_port(host, port, timeout_seconds=12):
        return ""
    return url


def _stop_opencode_server() -> None:
    global _SERVER_PROCESS
    if _SERVER_PROCESS is None or _SERVER_PROCESS.poll() is not None:
        return
    _SERVER_PROCESS.terminate()
    try:
        _SERVER_PROCESS.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _SERVER_PROCESS.kill()


def _wait_for_port(host: str, port: int, timeout_seconds: int) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _is_port_open(host, port):
            return True
        time.sleep(0.25)
    return False


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.3)
        try:
            probe.connect((host, port))
        except OSError:
            return False
    return True


def _select_server_port(host: str, preferred_port: int) -> int:
    for offset in range(50):
        port = preferred_port + offset
        if not _is_port_open(host, port):
            return port
    raise RuntimeError(f"No free OpenCode server port found starting at {preferred_port}.")


def _should_try_next_model(result: RocketExecutionResult) -> bool:
    text = "\n".join([result.message, *result.details]).lower()
    retry_markers = (
        "providermodelnotfounderror",
        "model not found",
        "rate limit",
        "quota",
        "overloaded",
        "temporarily unavailable",
        "certificate is not yet valid",
        "certificate has expired",
        "stream error",
        "provider/runtime error",
    )
    return any(marker in text for marker in retry_markers)


class CompletedShim:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode


def _server_log_offsets(execution_dir: Path) -> dict[Path, int]:
    offsets: dict[Path, int] = {}
    for path in (execution_dir / ".rocket" / "opencode_server.log", execution_dir / ".rocket" / "opencode_server.err"):
        try:
            offsets[path] = path.stat().st_size
        except OSError:
            offsets[path] = 0
    return offsets


def _server_log_delta(execution_dir: Path, offsets: dict[Path, int], limit: int = 12000) -> str:
    chunks: list[str] = []
    for path, offset in offsets.items():
        try:
            with path.open("rb") as handle:
                handle.seek(offset)
                data = handle.read(limit)
        except OSError:
            continue
        if data:
            chunks.append(data.decode("utf-8", errors="replace"))
    return "\n".join(chunks)


def _server_runtime_error_message(log_delta: str) -> str:
    text = _strip_ansi(log_delta)
    lower = text.lower()
    if "certificate is not yet valid" in lower:
        return "OpenCode provider/runtime error: certificate is not yet valid."
    if "certificate has expired" in lower:
        return "OpenCode provider/runtime error: certificate has expired."
    if "stream error" in lower and "error.error=" in lower:
        match = re.search(r'error\.error="([^"]+)"', text)
        if match:
            return f"OpenCode provider/runtime error: {match.group(1)}"
        return "OpenCode provider/runtime stream error."
    return ""


def _is_verification_failure(result: RocketExecutionResult) -> bool:
    if result.success:
        return False
    text = "\n".join([result.message, *result.details]).lower()
    return "could not verify" in text or "not visible after opencode returned" in text


def _correction_prompt(prompt: str, result: RocketExecutionResult) -> str:
    return (
        f"{prompt}\n\n"
        "Correction attempt required:\n"
        f"Previous final message: {result.message}\n"
        "Rocket could not verify the desktop state. Do exactly one focused corrective action, "
        "then verify with visible window/process/browser evidence. Do not explain. Do not repeat "
        "the same failed action unless the observed state proves it is needed.\n"
    )


def _desktop_expectation(task: str) -> dict[str, str] | None:
    mission = parse_mission(task)
    if mission:
        intent = str(mission.get("intent", "")).upper()
        context = str(mission.get("context", ""))
        task = f"{mission.get('mission', '')} {context}"
        if intent in {"OPEN_APP", "SEND_MESSAGE", "CALCULATE"}:
            expectation = {
                "whatsapp": "whatsapp",
                "settings": "systemsettings",
                "chrome": "chrome",
                "edge": "msedge",
                "vscode": "code",
                "explorer": "explorer",
                "notepad": "notepad",
                "calculator": "calculator",
                "terminal": "windowsterminal",
            }.get(context.lower())
            if expectation:
                item = {"kind": "app", "label": context.lower(), "process": expectation}
                if context.lower() == "calculator":
                    item["processes"] = "calculator,calculatorapp"
                    item["title_keywords"] = "calculator"
                    expected = _expected_calculator_result(task)
                    if intent == "CALCULATE" and expected:
                        item["expected_result"] = expected
                return item
    lower = task.lower()
    app_patterns = (
        (r"\bopen\s+(google\s+chrome|chrome)\b", "chrome", "chrome"),
        (r"\bopen\s+(whatsapp)\b", "whatsapp", "whatsapp"),
        (r"\bopen\s+(settings|windows settings)\b", "settings", "systemsettings"),
        (r"\bopen\s+(notepad)\b", "notepad", "notepad"),
        (r"\bopen\s+(edge|microsoft edge)\b", "edge", "msedge"),
    )
    for pattern, label, process in app_patterns:
        if re.search(pattern, lower):
            return {"kind": "app", "label": label, "process": process}
    if re.search(r"\b(open|launch|start|calculate|calc)\b.*\b(calculator|calc)\b|\b\d+\s*[+\-*/]\s*\d+\b", lower):
        return {
            "kind": "app",
            "label": "calculator",
            "process": "calculator",
            "processes": "calculator,calculatorapp",
            "title_keywords": "calculator",
            "expected_result": _expected_calculator_result(task),
        }
    if " in chrome" in lower or "chrome" in lower and "search" in lower:
        return {"kind": "app", "label": "chrome", "process": "chrome"}
    return None


def _cleanup_after_success(task: str, expectation: dict[str, str]) -> str:
    if not _should_cleanup_after_success(task, expectation):
        return ""
    return _close_expected_app(expectation)


def _should_cleanup_after_success(task: str, expectation: dict[str, str]) -> bool:
    label = str(expectation.get("label", "")).lower()
    # Persistent apps are always kept open for reuse regardless of mission text.
    if label in {"chrome", "edge", "youtube", "spotify", "whatsapp", "vscode", "code"}:
        return False
    return cleanup_policy(parse_mission(task)) == "temporary"


def _mission_image_paths(mission: dict[str, Any] | None) -> list[str]:
    if not isinstance(mission, dict):
        return []
    paths: list[str] = []
    raw_paths = mission.get("image_paths")
    if isinstance(raw_paths, list):
        for value in raw_paths:
            if isinstance(value, str) and value.strip():
                paths.append(value.strip())
    raw_path = mission.get("image_path")
    if isinstance(raw_path, str) and raw_path.strip():
        paths.append(raw_path.strip())
    return paths


def _close_expected_app(expectation: dict[str, str]) -> str:
    label = str(expectation.get("label", "app")).lower()
    processes = [
        item.strip()
        for item in str(expectation.get("processes") or expectation.get("process") or "").split(",")
        if item.strip()
    ]
    title_keywords = [
        item.strip()
        for item in str(expectation.get("title_keywords", label)).split(",")
        if item.strip()
    ]
    process_list = ",".join(processes)
    title_list = ",".join(title_keywords)
    script = rf"""
$processes = '{process_list}'.Split(',') | Where-Object {{ $_ }}
$titles = '{title_list}'.Split(',') | Where-Object {{ $_ }}
$closed = @()
foreach ($p in Get-Process) {{
  $name = ($p.ProcessName ?? '').ToLowerInvariant()
  $title = ($p.MainWindowTitle ?? '').ToLowerInvariant()
  $matchProcess = $false
  foreach ($candidate in $processes) {{
    $candidate = $candidate.ToLowerInvariant()
    if ($name -eq $candidate -or $name.StartsWith($candidate)) {{ $matchProcess = $true }}
  }}
  $matchTitle = $false
  foreach ($candidate in $titles) {{
    $candidate = $candidate.ToLowerInvariant()
    if ($candidate -and $title.Contains($candidate)) {{ $matchTitle = $true }}
  }}
  if ($name -eq 'applicationframehost' -and -not $matchTitle) {{ continue }}
  if ($matchProcess -or $matchTitle) {{
    try {{
      if ($p.MainWindowHandle -ne 0) {{ [void]$p.CloseMainWindow(); Start-Sleep -Milliseconds 350 }}
      if (-not $p.HasExited -and $name -ne 'applicationframehost') {{ $p.Kill() }}
      $closed += $p.ProcessName
    }} catch {{}}
  }}
}}
if ($closed.Count -eq 0) {{ 'no matching {label} window to close' }} else {{ 'closed ' + (($closed | Select-Object -Unique) -join ', ') }}
"""
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception as error:
        return f"cleanup failed for {label}: {error}"
    output = (completed.stdout or completed.stderr or "").strip()
    return output or f"cleanup attempted for {label}"


def _verify_desktop_expectation(expectation: dict[str, str], attempts: int = 6) -> tuple[bool, str]:
    label = expectation["label"]
    processes = [
        item.strip()
        for item in str(expectation.get("processes") or expectation.get("process") or "").split(",")
        if item.strip()
    ]
    title_keywords = [
        item.strip().lower()
        for item in str(expectation.get("title_keywords", "")).split(",")
        if item.strip()
    ]
    last_calculator_message = ""
    for _ in range(attempts):
        snapshot = _windows_process_snapshot()
        if label == "calculator" and expectation.get("expected_result"):
            verified, message = _verify_calculator_result(str(expectation["expected_result"]))
            if verified:
                return True, message
            last_calculator_message = message
            time.sleep(1)
            continue
        if _process_visible(snapshot, processes, title_keywords):
            return True, f"Verified desktop action: {label} is visible/running."
        time.sleep(1)
    if last_calculator_message:
        return False, last_calculator_message
    return False, f"Expected {label} process/window was not visible after OpenCode returned."


def _expected_calculator_result(task: str) -> str:
    result_match = re.search(r"\bresult\s+is\s+(-?\d+(?:\.\d+)?)\b", task, flags=re.IGNORECASE)
    if result_match:
        return result_match.group(1)
    expression_match = re.search(r"(-?\d+(?:\.\d+)?\s*[+\-*/]\s*-?\d+(?:\.\d+)?)", task)
    if not expression_match:
        return ""
    expression = expression_match.group(1).replace(" ", "")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?[+\-*/]-?\d+(?:\.\d+)?", expression):
        return ""
    try:
        # Safe because the expression is regex-limited to two numeric operands.
        value = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
    except Exception:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _verify_calculator_result(expected_result: str) -> tuple[bool, str]:
    state = _calculator_accessibility_state()
    if not state:
        return False, "Calculator result was not visible through accessibility state."
    display = str(state.get("display", "")).strip()
    expression = str(state.get("expression", "")).strip()
    normalized_display = _normalize_calculator_text(display)
    expected = expected_result.strip()
    if expected and expected in normalized_display:
        return True, f"Verified Calculator result: {display or expected}."
    return False, (
        "Calculator was visible, but the expected result was not confirmed. "
        f"Expected {expected}; expression={expression or 'unknown'}; display={display or 'unknown'}."
    )


def _calculator_accessibility_state() -> dict[str, str]:
    script = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
$calc = $null
for ($i = 0; $i -lt $windows.Count; $i++) {
  $name = $windows.Item($i).Current.Name
  if ($name -like '*Calculator*') { $calc = $windows.Item($i); break }
}
if ($null -eq $calc) { exit 2 }
$resultCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'CalculatorResults')
$exprCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'CalculatorExpression')
$result = $calc.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $resultCond)
$expr = $calc.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $exprCond)
[pscustomobject]@{
  display = if ($null -eq $result) { '' } else { $result.Current.Name }
  expression = if ($null -eq $expr) { '' } else { $expr.Current.Name }
} | ConvertTo-Json -Compress
"""
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return {}
    if completed.returncode != 0 or not completed.stdout.strip():
        return {}
    try:
        data: Any = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _normalize_calculator_text(value: str) -> str:
    return value.replace(",", "").replace("Display is", "").strip()


def _windows_process_snapshot() -> list[dict[str, str]]:
    script = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "Get-Process | "
        "Where-Object { $_.ProcessName -or $_.MainWindowTitle } | "
        "Select-Object ProcessName,MainWindowTitle | "
        "ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return []
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    try:
        data: Any = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    rows = data if isinstance(data, list) else [data]
    return [row for row in rows if isinstance(row, dict)]


def _visible_window_titles() -> list[str]:
    titles: list[str] = []
    for row in _windows_process_snapshot():
        title = str(row.get("MainWindowTitle", "")).strip()
        if title:
            titles.append(title)
    return titles[:50]


def _process_visible(snapshot: list[dict[str, str]], processes: list[str], title_keywords: list[str] | None = None) -> bool:
    expected_processes = [process.lower() for process in processes]
    expected_titles = title_keywords or []
    for row in snapshot:
        name = str(row.get("ProcessName", "")).lower()
        title = str(row.get("MainWindowTitle", "")).lower()
        if name == "applicationframehost":
            if any(expected in title for expected in expected_titles):
                return True
            continue
        if any(name == expected or name.startswith(expected) for expected in expected_processes):
            return True
        if any(expected in title for expected in [*expected_processes, *expected_titles]):
            return True
    return False
