"""Terminal wrapper for runtime execution and terminal display."""

from __future__ import annotations

from typing import Any

from agent.runtime.adapter import RocketAdapter


class RuntimeTerminalBridge:
    """Delegate terminal UI calls while executing generated tasks in background."""

    def __init__(self, terminal: Any, adapter: RocketAdapter) -> None:
        self._terminal = terminal
        self._adapter = adapter

    def __getattr__(self, name: str) -> Any:
        return getattr(self._terminal, name)

    def received_task(self, client_id: str, source: str, task: str, latency_ms: int) -> None:
        self._terminal.received_task(client_id=client_id, source=source, task=task, latency_ms=latency_ms)

    def execute_task(self, client_id: str, task: str) -> dict[str, Any]:
        self._terminal.log(f"{client_id}: Runtime executing: {task}")
        try:
            result = self._adapter.execute(task)
        except Exception as error:
            message = f"Runtime failed: {error}"
            self._terminal.error(f"{client_id}: {message}")
            return {
                "task": task,
                "success": False,
                "executor": "rocket-runtime",
                "message": message,
                "verification": "Runtime exception before verification.",
                "details": [],
            }

        verification = _verification_from_details(result.details)
        if result.success:
            self._terminal.log(f"{client_id}: Runtime complete via {result.executor}: {result.message}")
        else:
            self._terminal.error(f"{client_id}: Runtime stopped via {result.executor}: {result.message}")
        return {
            "task": result.task,
            "success": result.success,
            "executor": result.executor,
            "message": result.message,
            "verification": verification,
            "details": result.details,
        }

    def apply_setup(self, setup: dict[str, Any]) -> None:
        self._adapter.apply_setup(setup)
        self._terminal.log("Rocket setup saved. OpenCode runtime will use the updated access mode.")

    def apply_profile(self, profile: dict[str, Any]) -> None:
        self._adapter.apply_profile(profile)
        self._terminal.log("Rocket profile saved to backend memory.")

    def permission_response(self, payload: dict[str, Any]) -> None:
        self._adapter.record_permission_response(payload)
        self._terminal.log("Permission response recorded for Rocket runtime.")


Phase2TerminalBridge = RuntimeTerminalBridge


def _verification_from_details(details: list[str]) -> str:
    for detail in details:
        if detail.startswith("desktop_verification="):
            return detail.split("=", 1)[1].strip()
    return "Runtime completed without a dedicated verification note."
