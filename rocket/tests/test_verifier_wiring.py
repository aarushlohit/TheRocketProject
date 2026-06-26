from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.runtime.adapter import apply_verifier
from agent.runtime.browser_state import compile_browser_mission, mission_to_task, BrowserState
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


def _result(success: bool, message: str = "OpenCode says done") -> RocketExecutionResult:
    return RocketExecutionResult(
        task="t",
        intent="opencode",
        executor="opencode-cli",
        success=success,
        message=message,
        details=["returncode=0"],
    )


def _task(user_text: str, state: BrowserState | None = None) -> str:
    return mission_to_task(compile_browser_mission(user_text, state or BrowserState()))


class VerifierAuthorityTests(unittest.TestCase):
    def test_bluetooth_settings_visible_is_not_success(self) -> None:
        # OpenCode reports success, but the radio cannot be confirmed -> failure.
        suite = VerifierSuite(FakeProbe(bluetooth=None))
        task = _task("Turn on Bluetooth")
        out = apply_verifier(_result(True), task, suite)
        self.assertFalse(out.success)

    def test_bluetooth_enabled_is_success(self) -> None:
        suite = VerifierSuite(FakeProbe(bluetooth=True))
        out = apply_verifier(_result(True), _task("Turn on Bluetooth"), suite)
        self.assertTrue(out.success)
        self.assertIn("Bluetooth is on", out.message)

    def test_install_website_open_is_not_success(self) -> None:
        # No Code.exe on disk -> not installed even though OpenCode claims success.
        suite = VerifierSuite(FakeProbe(executable=None))
        out = apply_verifier(_result(True), _task("Install VSCode"), suite)
        self.assertFalse(out.success)
        self.assertIn("not installed", out.message)

    def test_install_binary_present_is_success(self) -> None:
        suite = VerifierSuite(FakeProbe(executable=r"C:\Code.exe"))
        out = apply_verifier(_result(True), _task("Install VSCode"), suite)
        self.assertTrue(out.success)

    def test_play_tab_open_is_not_success_without_playback(self) -> None:
        suite = VerifierSuite(
            FakeProbe(browser={"browser_open": True, "current_site": "youtube.com", "video_playing": False})
        )
        task = _task("Play first video", BrowserState(current_site="youtube.com", browser_open=True))
        out = apply_verifier(_result(True), task, suite)
        self.assertFalse(out.success)

    def test_play_video_playing_is_success(self) -> None:
        suite = VerifierSuite(
            FakeProbe(browser={"browser_open": True, "current_site": "youtube.com", "video_playing": True})
        )
        task = _task("Play first video", BrowserState(current_site="youtube.com", browser_open=True))
        out = apply_verifier(_result(True), task, suite)
        self.assertTrue(out.success)

    def test_verifier_can_overturn_a_reported_failure(self) -> None:
        # Reality wins both ways: confirmed reality makes it a success.
        suite = VerifierSuite(FakeProbe(bluetooth=True))
        out = apply_verifier(_result(False), _task("Turn on Bluetooth"), suite)
        self.assertTrue(out.success)


class VerifierDeferralTests(unittest.TestCase):
    def test_unmappable_mission_keeps_executor_result(self) -> None:
        suite = VerifierSuite(FakeProbe())
        task = _task("Create a notes file in workspace")
        out = apply_verifier(_result(True, "file created"), task, suite)
        # Suite cannot verify file creation -> defer to OpenCode success.
        self.assertTrue(out.success)
        self.assertEqual(out.message, "file created")

    def test_non_mission_task_is_passthrough(self) -> None:
        suite = VerifierSuite(FakeProbe())
        out = apply_verifier(_result(True, "done"), "not-json-task", suite)
        self.assertTrue(out.success)

    def test_disabled_via_env_is_passthrough(self) -> None:
        suite = VerifierSuite(FakeProbe(bluetooth=None))
        with patch.dict("os.environ", {"ROCKET_VERIFIER_ENABLED": "0"}):
            out = apply_verifier(_result(True), _task("Turn on Bluetooth"), suite)
        self.assertTrue(out.success)


class CanVerifyTests(unittest.TestCase):
    def test_can_verify_known_missions(self) -> None:
        suite = VerifierSuite(FakeProbe())
        self.assertTrue(suite.can_verify(compile_browser_mission("Install VSCode", BrowserState())))
        self.assertTrue(suite.can_verify(compile_browser_mission("Turn on Bluetooth", BrowserState())))

    def test_cannot_verify_file_mission(self) -> None:
        suite = VerifierSuite(FakeProbe())
        self.assertFalse(suite.can_verify(compile_browser_mission("Create a notes file in workspace", BrowserState())))


class DispatchRegressionTests(unittest.TestCase):
    """Compiled OPEN_APP missions read 'Open installed X application'.

    That must route to process verification, not the install verifier.
    """

    def test_open_app_with_installed_word_is_not_install(self) -> None:
        suite = VerifierSuite(FakeProbe(processes={"calculatorapp.exe"}, executable=None))
        mission = compile_browser_mission("Open calculator", BrowserState())
        self.assertIn("installed", mission["mission"].lower())
        verdict = suite.verify_mission(mission)
        # Routed to process check (passes), not install (which would fail: no binary).
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.verifier, "ProcessVerifier")

    def test_open_settings_routes_to_process(self) -> None:
        suite = VerifierSuite(FakeProbe(processes={"systemsettings.exe"}))
        mission = compile_browser_mission("Open settings", BrowserState())
        self.assertEqual(suite.verify_mission(mission).verifier, "ProcessVerifier")

    def test_real_install_still_routes_to_install(self) -> None:
        suite = VerifierSuite(FakeProbe(executable=r"C:\Code.exe"))
        mission = compile_browser_mission("Install VSCode", BrowserState())
        self.assertEqual(suite.verify_mission(mission).verifier, "InstallVerifier")


if __name__ == "__main__":
    unittest.main()
