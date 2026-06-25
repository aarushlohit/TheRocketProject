"""Live benchmark wiring for Rocket.

Prepares a real executor that runs the benchmark suite through a live
:class:`RocketAdapter` (real OpenCode, Playwright, Windows MCP, Chrome) and
scores every task against observed machine reality via the existing
:func:`agent.runtime.benchmark.run_benchmark`. No simulated executor.

SAFETY: this module is inert by default. The executor refuses to run unless it
is explicitly *armed*, and the CLI additionally requires
``ROCKET_LIVE_BENCHMARK=1`` and ``NVIDIA_API_KEY``. Nothing here drives the
desktop, installs software, or toggles radios on import, construction, or test.
Arming and running is a deliberate operator action on a real machine.

Honest limitation: browser-page verification needs a live browser_state source
(Playwright). ``WindowsRealityProbe`` does not provide one, so browser missions
are scored as deferred (executor result) rather than reality-verified. Process,
install, Bluetooth, and Wi-Fi missions are reality-verified.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable

from agent.runtime.benchmark import (
    BenchmarkReport,
    BenchmarkTask,
    ExecOutcome,
    generate_default_suite,
    run_benchmark,
)
from agent.runtime.browser_state import mission_to_task
from agent.runtime.install_mission import install_key_from_mission
from agent.runtime.verifier import INSTALL_TARGETS, RealityProbe, WindowsRealityProbe

NOT_ARMED_MESSAGE = (
    "Live benchmark executor is not armed. This drives the real desktop. "
    "Construct with armed=True and run with ROCKET_LIVE_BENCHMARK=1 and NVIDIA_API_KEY set."
)


def _raw_reported_success(result) -> bool:
    """OpenCode's raw claim (pre-verifier), so false positives can be measured."""

    for detail in getattr(result, "details", []) or []:
        if detail.startswith("opencode_reported_success="):
            return detail.split("=", 1)[1].strip().lower() == "true"
    return bool(getattr(result, "success", False))


def _recovery_from_details(details) -> tuple[int, bool]:
    attempts = 0
    recovered = False
    for detail in details or []:
        if detail.startswith("recovery_attempts="):
            try:
                attempts = int(detail.split("=", 1)[1])
            except ValueError:
                attempts = 0
        elif detail.startswith("recovery_success="):
            recovered = detail.split("=", 1)[1].strip().lower() == "true"
    return attempts, recovered


class RocketAdapterExecutor:
    """Runs benchmark tasks through a live RocketAdapter and observes reality.

    Inert unless ``armed=True``. The reality probe and adapter are injectable so
    the wiring is testable without touching the real machine.
    """

    def __init__(
        self,
        adapter,
        *,
        probe: RealityProbe | None = None,
        armed: bool = False,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.adapter = adapter
        self.probe = probe or WindowsRealityProbe()
        self.armed = armed
        self._clock = clock

    def __call__(self, task: BenchmarkTask) -> ExecOutcome:
        if not self.armed:
            raise RuntimeError(NOT_ARMED_MESSAGE)
        start = self._clock()
        result = self.adapter.execute(mission_to_task(task.mission))
        latency_ms = (self._clock() - start) * 1000.0
        retries, recovered = _recovery_from_details(getattr(result, "details", []))
        timed_out = "timed out" in str(getattr(result, "message", "")).lower()
        return ExecOutcome(
            reported_success=_raw_reported_success(result),
            reality=self._snapshot(task.mission),
            message=str(getattr(result, "message", "")),
            retries=retries,
            recovered=recovered,
            timed_out=timed_out,
            latency_ms=latency_ms,
        )

    def _snapshot(self, mission: dict) -> dict:
        """Capture the real machine facts relevant to this mission."""

        reality: dict = {}
        processes = self.probe.running_processes()
        if processes is not None:
            reality["processes"] = sorted(processes)
        bluetooth = self.probe.bluetooth_enabled()
        if bluetooth is not None:
            reality["bluetooth"] = bluetooth
        wifi = self.probe.wifi_connected()
        if wifi is not None:
            reality["wifi"] = wifi
        key = install_key_from_mission(mission)
        if key in INSTALL_TARGETS:
            target = INSTALL_TARGETS[key]
            reality["executable"] = self.probe.find_executable(target.executables, target.search_paths)
        browser = self.probe.browser_state()
        if browser is not None:
            reality["browser"] = browser
        return reality


def run_live_benchmark(
    adapter,
    tasks: list[BenchmarkTask] | None = None,
    *,
    armed: bool = False,
    probe: RealityProbe | None = None,
    output: Path | None = None,
) -> BenchmarkReport:
    """Run the suite through a live adapter and write ``benchmark_live.json``.

    Caller must pass ``armed=True`` to actually drive the desktop.
    """

    executor = RocketAdapterExecutor(adapter, probe=probe, armed=armed)
    report = run_benchmark(tasks or generate_default_suite(), executor=executor, mode="live")
    report.write(output or Path("benchmark_live.json"))
    return report


def main() -> None:
    """Operator entry point. Refuses to run unless explicitly armed."""

    if os.getenv("ROCKET_LIVE_BENCHMARK") != "1":
        print("[benchmark-live] Refusing to run. Set ROCKET_LIVE_BENCHMARK=1 to drive the real desktop.")
        return
    if not os.getenv("NVIDIA_API_KEY"):
        print("[benchmark-live] Refusing to run. NVIDIA_API_KEY is not set.")
        return

    from agent.runtime.adapter import RocketAdapter

    data_dir = Path(os.getenv("ROCKET_DATA_DIR", str(Path.home() / ".rocket")))
    adapter = RocketAdapter(repo_root=Path.cwd(), data_dir=data_dir)
    report = run_live_benchmark(adapter, armed=True, output=Path("benchmark_live.json"))
    overall = report.overall()
    print(
        f"[benchmark-live] tasks={overall['total']} success_rate={overall['success_rate']} "
        f"false_positives={overall['false_positives']} timeouts={overall['timeouts']} "
        f"avg_latency_ms={overall['avg_latency_ms']} -> benchmark_live.json"
    )


if __name__ == "__main__":
    main()
