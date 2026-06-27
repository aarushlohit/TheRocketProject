"""RocketAdapter: task string to OpenCode-only execution."""

from __future__ import annotations

import os
import time
import re
from pathlib import Path
from typing import Any

from agent.runtime.memory import RocketMemory, RocketProfile
from agent.runtime.browser_state import BrowserState, parse_mission, predict_browser_state
from agent.runtime.opencode_cli_client import OpenCodeCliClient
from agent.runtime.opencode_runtime import OpenCodeRuntimeManager, RuntimeReadinessReport
from agent.runtime.recovery import RecoveryEngine, RecoveryStrategy
from agent.runtime.results import RocketExecutionResult
from agent.runtime.setup import RocketSetup
from agent.runtime.verifier import VerifierSuite


class RocketAdapter:
    """Invisible OpenCode CLI adapter behind the Rocket task string."""

    def __init__(self, repo_root: Path, data_dir: Path, verifier_suite: VerifierSuite | None = None) -> None:
        self.repo_root = repo_root
        self.data_dir = data_dir / "phase2"
        self.memory = RocketMemory(self.data_dir)
        self.setup = RocketSetup.from_dict(self.memory.get("setup"))
        self.profile = self._load_profile()
        self.verifier_suite = verifier_suite or VerifierSuite()
        self.runtime = OpenCodeRuntimeManager(self.data_dir, setup=self.setup)
        self.opencode = OpenCodeCliClient(
            repo_root=repo_root,
            profile=self.profile,
            setup=self.setup,
            runtime_env=self.runtime.execution_env(),
            history=self._history(),
            session_id=str(self.memory.get("opencode_session_id", "") or ""),
            browser_state=self._browser_state().to_dict(),
        )
        self._last_report: RuntimeReadinessReport | None = None

    def apply_setup(self, setup_data: dict[str, Any]) -> None:
        self.setup = RocketSetup.from_dict(setup_data)
        self.memory.set("setup", self.setup.to_dict())
        self.profile = self._load_profile()
        self.runtime = OpenCodeRuntimeManager(self.data_dir, setup=self.setup)
        self.opencode = OpenCodeCliClient(
            repo_root=self.repo_root,
            profile=self.profile,
            setup=self.setup,
            runtime_env=self.runtime.execution_env(),
            history=self._history(),
            session_id=str(self.memory.get("opencode_session_id", "") or ""),
            browser_state=self._browser_state().to_dict(),
        )

    def apply_profile(self, profile_data: dict[str, Any]) -> None:
        current = self.memory.load_profile()
        profile = RocketProfile(
            **{
                **current.__dict__,
                "name": str(profile_data.get("name", current.name) or current.name),
                "preferred_name": str(profile_data.get("preferred_name", current.preferred_name) or current.preferred_name),
                "email": str(profile_data.get("email", current.email) or current.email),
                "phone": str(profile_data.get("phone", current.phone) or current.phone),
                "address": str(profile_data.get("address", current.address) or current.address),
                "country": str(profile_data.get("country", current.country) or current.country),
                "browser": str(profile_data.get("browser", current.browser) or current.browser),
                "editor": str(profile_data.get("editor", current.editor) or current.editor),
                "speech_speed": str(profile_data.get("speech_speed", current.speech_speed) or current.speech_speed),
                "trust_level": str(profile_data.get("trust_level", current.trust_level) or current.trust_level),
                "password_pattern_ref": str(profile_data.get("password_pattern_ref", current.password_pattern_ref) or current.password_pattern_ref),
            }
        )
        self.memory.save_profile(profile)
        self.profile = self._load_profile()

    def record_permission_response(self, payload: dict[str, Any]) -> None:
        event = {"at": time.time(), "type": "permission_response", "payload": payload}
        self.memory.set("last_permission_response", event)

    def execute(self, task: str) -> RocketExecutionResult:
        if os.getenv("ROCKET_PHASE2_ENABLED", "1").strip().lower() in {"0", "false", "no"}:
            return RocketExecutionResult(task, "disabled", "rocket_adapter", False, "Runtime execution disabled.")

        started = time.perf_counter()
        report = self.runtime.ensure_ready()
        self._last_report = report
        self.memory.set("runtime_readiness", report.__dict__)
        if not report.ready:
            return RocketExecutionResult(
                task=task,
                intent="opencode",
                executor="opencode-runtime",
                success=False,
                message=report.summary(),
                details=report.actions,
            )

        learned_task = self._apply_persistent_learning(task)
        self.opencode.runtime_env = self.runtime.execution_env()
        self.opencode.history = self._history()
        self.opencode.session_id = str(self.memory.get("opencode_session_id", "") or "")
        self.opencode.browser_state = self._browser_state()
        result = run_with_recovery(learned_task, self.opencode.execute, self.verifier_suite)
        result = RocketExecutionResult(
            task=result.task,
            intent=result.intent,
            executor=result.executor,
            success=result.success,
            message=result.message,
            duration_ms=int((time.perf_counter() - started) * 1000),
            details=result.details,
        )
        self._remember_execution(result)
        self._learn_from_execution(task, learned_task, result)
        return result

    def _load_profile(self) -> RocketProfile:
        profile = self.memory.load_profile()
        setup = self.setup
        return RocketProfile(
            **{
                **profile.__dict__,
                "access_mode": setup.access_mode,
                "workspace_path": setup.workspace_path,
                "opencode_config_dir": setup.opencode_config_dir,
                "powers_source_dir": setup.powers_source_dir,
                "credential_mode": setup.credential_mode,
                "credential_refs": setup.credential_refs,
                "backup_enabled": setup.backup_enabled,
            }
        )

    def _history(self) -> list[dict[str, Any]]:
        history = self.memory.get("execution_history", [])
        return history if isinstance(history, list) else []

    def _browser_state(self) -> BrowserState:
        return BrowserState.from_dict(self.memory.get("browser_state"))

    def _remember_execution(self, result: RocketExecutionResult) -> None:
        history = self._history()
        event = {
            "at": time.time(),
            "task": result.task,
            "executor": result.executor,
            "success": result.success,
            "message": result.message,
        }
        history.append(event)
        self.memory.set("execution_history", history[-12:])
        self._remember_browser_state(result)
        session_id = _session_id_from_details(result.details)
        if session_id:
            self.memory.set("opencode_session_id", session_id)
        if result.success:
            self.memory.set("last_successful_execution", event)

    def _apply_persistent_learning(self, task: str) -> str:
        resolved = task
        aliases = self.memory.load_contact_aliases()
        for spoken, actual in aliases.items():
            if not spoken or not actual:
                continue
            pattern = re.compile(rf"\b{re.escape(spoken)}\b", re.IGNORECASE)
            resolved = pattern.sub(actual, resolved)
        spoken_name = _extract_contact_name(resolved)
        if spoken_name:
            learned = self.memory.resolve_contact_alias(spoken_name)
            if learned and learned != spoken_name:
                resolved = resolved.replace(spoken_name, learned)
        return resolved

    def _learn_from_execution(self, original_task: str, learned_task: str, result: RocketExecutionResult) -> None:
        if not result.success:
            return
        if "whatsapp" not in original_task.lower() and "message" not in original_task.lower():
            return
        spoken_name = _extract_contact_name(original_task)
        resolved_name = _extract_contact_name(learned_task)
        if not spoken_name:
            return
        if resolved_name:
            self.memory.save_contact_alias(spoken_name, resolved_name)
            return
        inferred = _extract_contact_name(result.message)
        if inferred:
            self.memory.save_contact_alias(spoken_name, inferred)
            return
        self.memory.save_contact_alias(spoken_name, spoken_name)

    def _remember_browser_state(self, result: RocketExecutionResult) -> None:
        mission = parse_mission(result.task)
        current = self._browser_state()
        if mission and isinstance(mission.get("predicted_browser_state"), dict):
            next_state = BrowserState.from_dict(mission["predicted_browser_state"])
        else:
            next_state = predict_browser_state(current, result.task)
        if result.success:
            self.memory.set("browser_state", next_state.to_dict())


def _session_id_from_details(details: list[str]) -> str:
    for detail in details:
        if detail.startswith("session_id="):
            return detail.split("=", 1)[1].strip()
    return ""


def _extract_contact_name(task: str) -> str:
    text = " ".join(task.strip().split())
    patterns = (
        r"(?:contact named|named|to|message|send message to|send to|chat with)\s+([A-Za-z][A-Za-z .'-]{1,60})",
        r"WhatsApp\s+to\s+([A-Za-z][A-Za-z .'-]{1,60})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" .,:;!?")
            candidate = re.split(r"\b(?:using|on|in|with|via|and)\b", candidate, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            if candidate:
                return candidate
    return ""


def apply_verifier(
    result: RocketExecutionResult,
    task: str,
    suite: VerifierSuite,
) -> RocketExecutionResult:
    """Let reality decide the outcome for missions the suite can verify.

    Rocket trusts the verifier, not OpenCode's words. When the suite has a
    concrete check for this mission, its verdict is authoritative: it can both
    confirm a success and overturn a false success. Missions the suite cannot
    map (e.g. file edits) keep the executor's own result.
    """

    if os.getenv("ROCKET_VERIFIER_ENABLED", "1").strip().lower() in {"0", "false", "no"}:
        return result
    mission = parse_mission(task)
    if mission is None or not suite.can_verify(mission):
        return result
    verdict = suite.verify_mission(mission)
    details = [
        *result.details,
        f"verifier={verdict.verifier}",
        f"verifier_passed={verdict.passed}",
        f"opencode_reported_success={result.success}",
    ]
    return RocketExecutionResult(
        task=result.task,
        intent=result.intent,
        executor=result.executor,
        success=verdict.passed,
        message=verdict.spoken,
        details=details,
    )


def _recovery_enabled() -> bool:
    return os.getenv("ROCKET_RECOVERY_ENABLED", "1").strip().lower() not in {"0", "false", "no"}


def _recovery_retries() -> int:
    try:
        return max(0, int(os.getenv("ROCKET_RECOVERY_MAX_RETRIES", "1")))
    except ValueError:
        return 1


_RECOVERY_SPEECH = {
    RecoveryStrategy.RETRY: "Recovery in progress. Retrying.",
    RecoveryStrategy.REUSE_BROWSER: "Recovery in progress. Reusing the open browser.",
    RecoveryStrategy.RESTORE_BROWSER: "Recovery in progress. Restoring the browser window.",
    RecoveryStrategy.RECONNECT_PLAYWRIGHT: "Recovery in progress. Reconnecting the browser controller.",
    RecoveryStrategy.RECONNECT_OPENCODE: "Recovery in progress. Reconnecting the runtime.",
    RecoveryStrategy.REUSE_SESSION: "Recovery in progress. Reusing the previous session.",
    RecoveryStrategy.ALTERNATIVE_MCP: "Recovery in progress. Trying another tool.",
    RecoveryStrategy.VISION_FALLBACK: "Recovery in progress. Looking at the screen.",
    RecoveryStrategy.ALTERNATIVE_STRATEGY: "Recovery in progress. Trying a different approach.",
    RecoveryStrategy.ASK_USER: "I could not complete this safely. I need your help.",
}


def _recovery_speech(strategy: RecoveryStrategy) -> str:
    return _RECOVERY_SPEECH.get(strategy, "Recovery in progress.")


def run_with_recovery(
    task: str,
    executor,
    suite: VerifierSuite,
    *,
    max_retries: int | None = None,
    engine: RecoveryEngine | None = None,
    feedback=None,
) -> RocketExecutionResult:
    """Execute, verify, and heal until reality confirms the goal or help is needed.

    Loop: OpenCode executes -> verifier proves -> on failure the recovery engine
    picks the next strategy and we retry + re-verify. Asking the user is the last
    resort. Recovery metrics are attached to the result details.
    """

    feedback = feedback or (lambda _message: None)
    retries = _recovery_retries() if max_retries is None else max_retries
    engine = engine or RecoveryEngine(max_attempts=max(1, retries))

    result = apply_verifier(executor(task), task, suite)
    if result.success or not _recovery_enabled() or retries <= 0:
        return _with_recovery_details(result, engine)

    engine.begin(result.message)
    while not result.success:
        strategy = engine.next_strategy()
        if strategy is RecoveryStrategy.ASK_USER:
            feedback(_recovery_speech(strategy))
            break
        feedback(_recovery_speech(strategy))
        result = apply_verifier(executor(task), task, suite)

    if result.success:
        engine.record_success()
        feedback(result.message)
    return _with_recovery_details(result, engine)


def _with_recovery_details(result: RocketExecutionResult, engine: RecoveryEngine) -> RocketExecutionResult:
    metrics = engine.metrics
    if metrics.attempts == 0 and not metrics.recovery_reason:
        return result
    details = [
        *result.details,
        f"recovery_attempts={metrics.attempts}",
        f"recovery_count={metrics.recovery_count}",
        f"recovery_reason={metrics.recovery_reason}",
        f"recovery_success={metrics.recovery_success}",
    ]
    return RocketExecutionResult(
        task=result.task,
        intent=result.intent,
        executor=result.executor,
        success=result.success,
        message=result.message,
        details=details,
    )
