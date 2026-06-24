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
from agent.runtime.prompts import ROCKET_SYSTEM_PROMPT
from agent.runtime.results import RocketExecutionResult
from agent.runtime.setup import RocketSetup


DEFAULT_OPENCODE_MODELS = (
    "opencode/deepseek-v4-flash-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/north-mini-code-free",
    "opencode/big-pickle",
)

_SERVER_PROCESS: subprocess.Popen[str] | None = None
_SERVER_URL = ""


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
    ) -> None:
        self.repo_root = repo_root
        self.profile = profile
        self.setup = setup or RocketSetup()
        self.runtime_env = runtime_env or {}
        self.history = history or []
        self.session_id = session_id
        self.command = os.getenv("ROCKET_OPENCODE_COMMAND", "opencode.cmd")
        self.models = _configured_models()
        self.model = self.models[0]
        self.timeout_seconds = _configured_timeout()
        self.print_logs = os.getenv("ROCKET_OPENCODE_PRINT_LOGS", "1").strip().lower() not in {"0", "false", "no"}
        self.persistent_server = (
            os.getenv("ROCKET_OPENCODE_PERSISTENT_SERVER", "1").strip().lower() not in {"0", "false", "no"}
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
            "build",
            "--format",
            "json",
        ]
        server_url = self._server_url()
        if server_url:
            command.extend(["--attach", server_url])
        if self.session_id:
            command.extend(["--session", self.session_id])
        if self.print_logs:
            command.extend(["--print-logs", "--log-level", os.getenv("ROCKET_OPENCODE_LOG_LEVEL", "INFO")])
        command.append("--dangerously-skip-permissions")
        env = os.environ.copy()
        env.update(self.runtime_env)
        try:
            completed = subprocess.run(
                command,
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
        session_id = _extract_session_id(stdout_text, stderr_text) or self.session_id
        message = _extract_message(stdout_text) or _tail(stdout_text)
        stderr_tail = _tail(stderr_text)
        if completed.returncode != 0:
            message = stderr_tail or message
        if not message and completed.returncode == 0:
            message = "Task completed."
        success = completed.returncode == 0 and not _looks_like_failure(message)
        details = [
            f"returncode={completed.returncode}",
            f"model={model}",
            f"dir={self._execution_dir()}",
        ]
        if server_url:
            details.append(f"attached_server={server_url}")
        if session_id:
            details.append(f"session_id={session_id}")
        if stderr_tail:
            details.append(f"stderr={stderr_tail}")
        if desktop_expectation and success:
            verified, verification_message = _verify_desktop_expectation(desktop_expectation)
            details.append(f"desktop_verification={verification_message}")
            if verified:
                message = verification_message
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
        profile = json.dumps(asdict(self.profile), ensure_ascii=True)
        setup = json.dumps(self.setup.to_dict(), ensure_ascii=True)
        history = json.dumps(self.history[-8:], ensure_ascii=True)
        visible_windows = json.dumps(_visible_window_titles(), ensure_ascii=True)
        credential_names = sorted(self.setup.credential_refs.keys())
        credential_context = ", ".join(credential_names) if credential_names else "none"
        return (
            f"Execute this desktop task now: {task}\n\n"
            "You are running inside Rocket's persistent OpenCode session. Use the same session context and "
            "the current visible desktop state. Do not reset assumptions between tasks.\n\n"
            "Accuracy workflow, in order:\n"
            "1. Read the task and attached prompt once. Do not spend time explaining or doing unnecessary reasoning.\n"
            "2. Observe: inspect Recent execution history, Visible windows, and current task before acting.\n"
            "3. Select tools fast: use all relevant configured MCP servers and skills. Prefer Playwright MCP for "
            "browser/web tasks, rocket-windows for native Windows apps, computer-use/screen tools for GUI vision, "
            "shokunin-memory for durable recall, and superpowers skills only when they directly help execution.\n"
            "4. Reuse: if the requested app/browser/window already exists in Visible windows, focus/reuse it. "
            "Do not open another copy or another browser tab unless the user asks for a new one.\n"
            "5. Act: perform the smallest action that completes the task.\n"
            "6. Verify: cross-check completion with rocket_list_windows, screenshot/vision, browser URL/page "
            "state, process/window state, or tool result.\n"
            "7. Recover: if verification fails, make one focused correction and verify again.\n\n"
            "Hard limits:\n"
            "Use at most 8 desktop/browser tool calls for one Rocket task.\n"
            "Do not call the same failed tool with the same arguments repeatedly.\n"
            "If the task is not complete after one recovery attempt, stop and report verification failed.\n"
            "Never keep acting after the final status.\n\n"
            "Browser rules:\n"
            "For browser automation, prefer Playwright MCP because it is faster and more reliable than visual clicking.\n"
            "For YouTube open/search/play tasks, use Playwright MCP: navigate directly to the target YouTube URL, "
            "search URL, or first result, then verify the page/video state with browser URL/title/page content.\n"
            "Use computer-use or screenshot vision only when Playwright cannot observe or control the needed state.\n"
            "If a task follows an earlier browser task, continue in the existing browser window/tab.\n"
            "If the task says Chrome, target Chrome exactly. Do not use Brave, Edge, or another browser unless "
            "Chrome is not visible/running after observation.\n"
            "When opening Chrome visibly, open/focus Chrome, maximize it to full screen or a maximized window, "
            "then verify a Chrome window is visible before continuing.\n"
            "For existing-browser navigation, focus the exact browser window, press Ctrl+L, type the target URL "
            "or search text, press Enter, then verify the loaded page.\n"
            "For YouTube search, use https://www.youtube.com/results?search_query=<query> directly.\n\n"
            "Completion rule:\n"
            "Only print final status after verification. If verification is weak or failed, say that clearly.\n\n"
            f"System policy:\n{ROCKET_SYSTEM_PROMPT}\n\n"
            f"Profile: {profile}\n"
            f"Runtime setup: {setup}\n"
            f"Available credential refs: {credential_context}\n"
            f"Recent execution history: {history}\n"
            f"Visible windows before action: {visible_windows}\n"
            f"Current OpenCode session id: {self.session_id or 'new'}\n"
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


def _short_run_message(task: str) -> str:
    compact = " ".join(task.strip().split())
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
    for key in ("text", "message", "content", "summary"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    parts = item.get("parts")
    if isinstance(parts, list):
        chunks = [_text_from_json(part) for part in parts]
        return "\n".join(chunk for chunk in chunks if chunk)
    return ""


def _tail(text: str | None, limit: int = 1200) -> str:
    text = text or ""
    text = _strip_ansi(text).strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


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
    value = os.getenv("ROCKET_OPENCODE_TIMEOUT_SECONDS", "").strip().lower()
    if value in {"", "0", "none", "false", "no", "off"}:
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
        ],
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
    )
    return any(marker in text for marker in retry_markers)


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
    if " in chrome" in lower or "chrome" in lower and "search" in lower:
        return {"kind": "app", "label": "chrome", "process": "chrome"}
    return None


def _verify_desktop_expectation(expectation: dict[str, str], attempts: int = 6) -> tuple[bool, str]:
    label = expectation["label"]
    process = expectation["process"]
    for _ in range(attempts):
        snapshot = _windows_process_snapshot()
        if _process_visible(snapshot, process):
            return True, f"Verified desktop action: {label} is visible/running."
        time.sleep(1)
    return False, f"Expected {label} process/window was not visible after OpenCode returned."


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


def _process_visible(snapshot: list[dict[str, str]], process: str) -> bool:
    expected = process.lower()
    for row in snapshot:
        name = str(row.get("ProcessName", "")).lower()
        title = str(row.get("MainWindowTitle", "")).lower()
        if name == expected or name.startswith(expected):
            return True
        if expected in title:
            return True
    return False
