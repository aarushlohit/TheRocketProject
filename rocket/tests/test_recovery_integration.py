from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.runtime.adapter import run_with_recovery
from agent.runtime.browser_state import BrowserState, compile_browser_mission, mission_to_task
from agent.runtime.results import RocketExecutionResult
from agent.runtime.verifier import RealityProbe, VerifierSuite


class FakeProbe(RealityProbe):
    def __init__(self, *, processes=None, windows=None, executable=None, path_exists=None, bluetooth=None, wifi=None, browser=None):
        self._processes = processes
        self._windows = windows
        self._executable = executable
        self._path_exists = path_exists
        self._bluetooth = bluetooth
        self._wifi = wifi
        self._browser = browser

    def running_processes(self):
        return self._processes

    def windows(self):
        return self._windows

    def find_executable(self, executables, search_paths):
        return self._executable

    def path_exists(self, path):
        return self._path_exists

    def bluetooth_enabled(self):
        return self._bluetooth

    def wifi_connected(self):
        return self._wifi

    def browser_state(self):
        return self._browser


def _result(success: bool, message: str = "done") -> RocketExecutionResult:
    return RocketExecutionResult(
        task="t", intent="opencode", executor="opencode-cli",
        success=success, message=message, details=["returncode=0"],
    )


def _bluetooth_task() -> str:
    return mission_to_task(compile_browser_mission("Turn on Bluetooth", BrowserState()))


class ScriptedExecutor:
    """Returns a queued sequence of results, one per call."""

    def __init__(self, results):
        self._results = list(results)
        self.calls = 0

    def __call__(self, task):
        self.calls += 1
        if self._results:
            return self._results.pop(0)
        return _result(False, "could not verify")


class RecoveryLoopTests(unittest.TestCase):
    def test_success_first_try_no_recovery(self) -> None:
        executor = ScriptedExecutor([_result(True)])
        suite = VerifierSuite(FakeProbe(bluetooth=True))
        out = run_with_recovery(_bluetooth_task(), executor, suite)
        self.assertTrue(out.success)
        self.assertEqual(executor.calls, 1)
        self.assertNotIn("recovery_attempts=1", " ".join(out.details))

    def test_verifier_overturn_then_recovered_on_retry(self) -> None:
        # First run: OpenCode claims success but radio is off (overturned).
        # Retry: radio is on -> verified success.
        executor = ScriptedExecutor([_result(True), _result(True)])
        suites = [VerifierSuite(FakeProbe(bluetooth=False)), VerifierSuite(FakeProbe(bluetooth=True))]

        # A suite whose reality changes between attempts.
        class ChangingSuite:
            def __init__(self):
                self._i = 0

            def can_verify(self, mission):
                return suites[0].can_verify(mission)

            def verify_mission(self, mission):
                suite = suites[min(self._i, 1)]
                self._i += 1
                return suite.verify_mission(mission)

        out = run_with_recovery(_bluetooth_task(), executor, ChangingSuite(), max_retries=2)
        self.assertTrue(out.success)
        self.assertEqual(executor.calls, 2)
        joined = " ".join(out.details)
        self.assertIn("recovery_success=True", joined)
        self.assertIn("recovery_reason=", joined)

    def test_persistent_failure_asks_user_and_stays_failed(self) -> None:
        executor = ScriptedExecutor([_result(True), _result(True), _result(True)])
        suite = VerifierSuite(FakeProbe(bluetooth=False))  # never on
        feedback: list[str] = []
        out = run_with_recovery(_bluetooth_task(), executor, suite, max_retries=2, feedback=feedback.append)
        self.assertFalse(out.success)
        self.assertIn("recovery_attempts=", " ".join(out.details))
        self.assertTrue(any("need your help" in m.lower() for m in feedback))

    def test_recovery_disabled_does_not_retry(self) -> None:
        executor = ScriptedExecutor([_result(True), _result(True)])
        suite = VerifierSuite(FakeProbe(bluetooth=False))
        with patch.dict("os.environ", {"ROCKET_RECOVERY_ENABLED": "0"}):
            out = run_with_recovery(_bluetooth_task(), executor, suite)
        self.assertFalse(out.success)
        self.assertEqual(executor.calls, 1)

    def test_feedback_announces_recovery_in_progress(self) -> None:
        executor = ScriptedExecutor([_result(True), _result(True)])
        suites_iter = [FakeProbe(bluetooth=False), FakeProbe(bluetooth=True)]

        class ChangingSuite:
            def __init__(self):
                self._i = 0

            def can_verify(self, mission):
                return True

            def verify_mission(self, mission):
                probe = suites_iter[min(self._i, 1)]
                self._i += 1
                return VerifierSuite(probe).verify_mission(mission)

        feedback: list[str] = []
        run_with_recovery(_bluetooth_task(), executor, ChangingSuite(), max_retries=2, feedback=feedback.append)
        self.assertTrue(any("recovery in progress" in m.lower() for m in feedback))

    def test_unverifiable_failure_still_retries_then_gives_up(self) -> None:
        # Executor reports failure honestly; verifier cannot map the mission.
        task = mission_to_task(compile_browser_mission("Create a notes file in workspace", BrowserState()))
        executor = ScriptedExecutor([_result(False, "tool failed with exception"), _result(False, "tool failed")])
        suite = VerifierSuite(FakeProbe())
        out = run_with_recovery(task, executor, suite, max_retries=1)
        self.assertFalse(out.success)
        self.assertGreaterEqual(executor.calls, 2)


if __name__ == "__main__":
    unittest.main()
