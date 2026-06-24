"""Terminal wrapper that starts runtime execution after task display."""

from __future__ import annotations

from threading import Thread
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
        worker = Thread(
            target=self._execute,
            args=(client_id, task),
            name=f"rocket-runtime-{client_id}",
            daemon=True,
        )
        worker.start()

    def apply_setup(self, setup: dict[str, Any]) -> None:
        self._adapter.apply_setup(setup)
        self._terminal.log("Rocket setup saved. OpenCode runtime will use the updated access mode.")

    def apply_profile(self, profile: dict[str, Any]) -> None:
        self._adapter.apply_profile(profile)
        self._terminal.log("Rocket profile saved to backend memory.")

    def permission_response(self, payload: dict[str, Any]) -> None:
        self._adapter.record_permission_response(payload)
        self._terminal.log("Permission response recorded for Rocket runtime.")

    def _execute(self, client_id: str, task: str) -> None:
        self._terminal.log(f"{client_id}: Runtime executing: {task}")
        try:
            result = self._adapter.execute(task)
        except Exception as error:
            self._terminal.error(f"{client_id}: Runtime failed: {error}")
            return

        if result.success:
            self._terminal.log(f"{client_id}: Runtime complete via {result.executor}: {result.message}")
        else:
            self._terminal.error(f"{client_id}: Runtime stopped via {result.executor}: {result.message}")


Phase2TerminalBridge = RuntimeTerminalBridge
