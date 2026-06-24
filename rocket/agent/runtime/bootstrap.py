"""OpenCode-only runtime bootstrap for Rocket."""

from __future__ import annotations

from pathlib import Path

from agent.runtime.memory import RocketMemory
from agent.runtime.opencode_runtime import OpenCodeRuntimeManager, RuntimeReadinessReport
from agent.runtime.setup import RocketSetup


def rocket_bootstrap(
    data_dir: Path,
    non_interactive: bool = True,
    workspace_root: Path | None = None,
) -> bool:
    """Verify and repair the global OpenCode powers runtime.

    Returns True when the verifier changed config/assets during this call.
    """

    del non_interactive, workspace_root
    phase2_dir = data_dir / "phase2"
    memory = RocketMemory(phase2_dir)
    setup = RocketSetup.from_dict(memory.get("setup"))
    report = sync_opencode_runtime(data_dir, setup)
    memory.set("runtime_readiness", report.__dict__)
    return bool(report.actions)


def sync_opencode_runtime(data_dir: Path, setup: RocketSetup | None = None) -> RuntimeReadinessReport:
    manager = OpenCodeRuntimeManager(data_dir / "phase2", setup=setup)
    return manager.ensure_ready()
