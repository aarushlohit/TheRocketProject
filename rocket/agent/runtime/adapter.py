"""RocketAdapter: task string to OpenCode-only execution."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from agent.runtime.memory import RocketMemory, RocketProfile
from agent.runtime.opencode_cli_client import OpenCodeCliClient
from agent.runtime.opencode_runtime import OpenCodeRuntimeManager, RuntimeReadinessReport
from agent.runtime.results import RocketExecutionResult
from agent.runtime.setup import RocketSetup


class RocketAdapter:
    """Invisible OpenCode CLI adapter behind the Rocket task string."""

    def __init__(self, repo_root: Path, data_dir: Path) -> None:
        self.repo_root = repo_root
        self.data_dir = data_dir / "phase2"
        self.memory = RocketMemory(self.data_dir)
        self.setup = RocketSetup.from_dict(self.memory.get("setup"))
        self.profile = self._load_profile()
        self.runtime = OpenCodeRuntimeManager(self.data_dir, setup=self.setup)
        self.opencode = OpenCodeCliClient(
            repo_root=repo_root,
            profile=self.profile,
            setup=self.setup,
            runtime_env=self.runtime.execution_env(),
            history=self._history(),
            session_id=str(self.memory.get("opencode_session_id", "") or ""),
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

        self.opencode.runtime_env = self.runtime.execution_env()
        self.opencode.history = self._history()
        self.opencode.session_id = str(self.memory.get("opencode_session_id", "") or "")
        result = self.opencode.execute(task)
        self._remember_execution(result)
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
        session_id = _session_id_from_details(result.details)
        if session_id:
            self.memory.set("opencode_session_id", session_id)
        if result.success:
            self.memory.set("last_successful_execution", event)


def _session_id_from_details(details: list[str]) -> str:
    for detail in details:
        if detail.startswith("session_id="):
            return detail.split("=", 1)[1].strip()
    return ""
