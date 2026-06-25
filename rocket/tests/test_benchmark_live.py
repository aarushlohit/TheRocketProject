from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent.runtime.benchmark import BenchmarkTask
from agent.runtime.benchmark_live import RocketAdapterExecutor, run_live_benchmark
from agent.runtime.browser_state import BrowserState, compile_browser_mission
from agent.runtime.results import RocketExecutionResult
from agent.runtime.verifier import RealityProbe


class FakeAdapter:
    """Stands in for a live RocketAdapter. Records calls; runs nothing real."""

    def __init__(self, result: RocketExecutionResult) -> None:
        self._result = result
        self.calls: list[str] = []

    def execute(self, task: str) -> RocketExecutionResult:
        self.calls.append(task)
        return self._result


class FakeProbe(RealityProbe):
    def __init__(self, *, processes=None, executable=None, bluetooth=None, wifi=None):
        self._processes = processes
        self._executable = executable
        self._bluetooth = bluetooth
        self._wifi = wifi

    def running_processes(self):
        return self._processes

    def find_executable(self, executables, search_paths):
        return self._executable

    def bluetooth_enabled(self):
        return self._bluetooth

    def wifi_connected(self):
        return self._wifi


def _task(prompt: str) -> BenchmarkTask:
    mission = compile_browser_mission(prompt, BrowserState())
    return BenchmarkTask(
        id="install-000", category="install", modality="voice",
        prompt=prompt, mission=mission, reality={}, expected_success=True,
    )


def _result(success: bool, *, details=None, message="done") -> RocketExecutionResult:
    return RocketExecutionResult(
        task="t", intent="opencode", executor="opencode-cli",
        success=success, message=message, details=details or [],
    )


class SafetyGateTests(unittest.TestCase):
    def test_executor_is_inert_unless_armed(self) -> None:
        adapter = FakeAdapter(_result(True))
        executor = RocketAdapterExecutor(adapter, probe=FakeProbe(), armed=False)
        with self.assertRaises(RuntimeError):
            executor(_task("Install VSCode"))
        # Nothing was executed on the (fake) adapter.
        self.assertEqual(adapter.calls, [])

    def test_armed_executor_runs_adapter(self) -> None:
        adapter = FakeAdapter(_result(True, details=["opencode_reported_success=True"]))
        executor = RocketAdapterExecutor(
            adapter, probe=FakeProbe(executable=r"C:\Code.exe"), armed=True
        )
        outcome = executor(_task("Install VSCode"))
        self.assertEqual(len(adapter.calls), 1)
        self.assertTrue(outcome.reported_success)
        self.assertEqual(outcome.reality.get("executable"), r"C:\Code.exe")


class RealitySnapshotTests(unittest.TestCase):
    def test_snapshot_captures_real_facts(self) -> None:
        adapter = FakeAdapter(_result(True))
        probe = FakeProbe(processes={"chrome.exe"}, bluetooth=True, wifi=False)
        executor = RocketAdapterExecutor(adapter, probe=probe, armed=True)
        outcome = executor(_task("Install Git"))
        self.assertIn("processes", outcome.reality)
        self.assertTrue(outcome.reality["bluetooth"])
        self.assertFalse(outcome.reality["wifi"])

    def test_recovery_metrics_extracted_from_details(self) -> None:
        adapter = FakeAdapter(
            _result(True, details=["opencode_reported_success=True", "recovery_attempts=2", "recovery_success=True"])
        )
        executor = RocketAdapterExecutor(adapter, probe=FakeProbe(executable=r"C:\Code.exe"), armed=True)
        outcome = executor(_task("Install VSCode"))
        self.assertEqual(outcome.retries, 2)
        self.assertTrue(outcome.recovered)


class FalsePositiveScoringTests(unittest.TestCase):
    def test_claimed_success_but_no_binary_is_false_positive(self) -> None:
        # OpenCode claims success; real disk has no Code.exe -> false positive.
        adapter = FakeAdapter(_result(True, details=["opencode_reported_success=True"]))
        report = run_live_benchmark(
            adapter,
            tasks=[_task("Install VSCode")],
            armed=True,
            probe=FakeProbe(executable=None),
            output=Path(tempfile.gettempdir()) / "rocket_test_live.json",
        )
        overall = report.overall()
        self.assertEqual(report.mode, "live")
        self.assertEqual(overall["false_positives"], 1)

    def test_claimed_success_with_binary_is_clean(self) -> None:
        adapter = FakeAdapter(_result(True, details=["opencode_reported_success=True"]))
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            report = run_live_benchmark(
                adapter,
                tasks=[_task("Install VLC")],
                armed=True,
                probe=FakeProbe(executable=r"C:\vlc.exe"),
                output=Path(tmp) / "benchmark_live.json",
            )
            self.assertEqual(report.overall()["false_positives"], 0)
            self.assertTrue((Path(tmp) / "benchmark_live.json").exists())

    def test_run_live_benchmark_unarmed_raises(self) -> None:
        adapter = FakeAdapter(_result(True))
        with self.assertRaises(RuntimeError):
            run_live_benchmark(
                adapter, tasks=[_task("Install Git")], armed=False, probe=FakeProbe(),
                output=Path(tempfile.gettempdir()) / "rocket_test_live2.json",
            )


if __name__ == "__main__":
    unittest.main()
