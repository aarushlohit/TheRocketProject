from __future__ import annotations

import unittest

from agent.runtime.verifier import (
    BluetoothVerifier,
    BrowserVerifier,
    FilesystemVerifier,
    InstallVerifier,
    ProcessVerifier,
    RealityProbe,
    VerifierSuite,
    WifiVerifier,
    WindowInfo,
    WindowVerifier,
)


class FakeProbe(RealityProbe):
    """Fully controllable reality for deterministic tests."""

    def __init__(
        self,
        *,
        processes=None,
        windows=None,
        executable=None,
        path_exists=None,
        bluetooth=None,
        wifi=None,
        browser=None,
    ) -> None:
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


class ProcessVerifierTests(unittest.TestCase):
    def test_running_process_passes(self) -> None:
        verifier = ProcessVerifier(FakeProbe(processes={"chrome.exe", "explorer.exe"}))
        verdict = verifier.verify(["chrome.exe"], label="chrome")
        self.assertTrue(verdict.passed)
        self.assertIn("running", verdict.spoken)

    def test_missing_process_fails(self) -> None:
        verifier = ProcessVerifier(FakeProbe(processes={"explorer.exe"}))
        self.assertFalse(verifier.verify(["chrome.exe"]).passed)

    def test_unknown_reality_never_passes(self) -> None:
        verifier = ProcessVerifier(FakeProbe(processes=None))
        self.assertFalse(verifier.verify(["chrome.exe"]).passed)


class WindowVerifierTests(unittest.TestCase):
    def test_visible_window_passes(self) -> None:
        verifier = WindowVerifier(FakeProbe(windows=[WindowInfo("Google Chrome", is_visible=True)]))
        self.assertTrue(verifier.verify("chrome").passed)

    def test_minimized_window_fails(self) -> None:
        verifier = WindowVerifier(FakeProbe(windows=[WindowInfo("Chrome", is_minimized=True)]))
        self.assertFalse(verifier.verify("chrome").passed)

    def test_require_maximized_enforced(self) -> None:
        verifier = WindowVerifier(FakeProbe(windows=[WindowInfo("Chrome", is_maximized=False)]))
        self.assertFalse(verifier.verify("chrome", require_maximized=True).passed)

    def test_unknown_windows_never_pass(self) -> None:
        verifier = WindowVerifier(FakeProbe(windows=None))
        self.assertFalse(verifier.verify("chrome").passed)


class BrowserVerifierTests(unittest.TestCase):
    def test_correct_site_passes(self) -> None:
        probe = FakeProbe(browser={"browser_open": True, "current_site": "youtube.com"})
        self.assertTrue(BrowserVerifier(probe).verify(expected_site="youtube.com").passed)

    def test_wrong_site_fails(self) -> None:
        probe = FakeProbe(browser={"browser_open": True, "current_site": "google.com"})
        self.assertFalse(BrowserVerifier(probe).verify(expected_site="youtube.com").passed)

    def test_play_state_enforced(self) -> None:
        probe = FakeProbe(browser={"browser_open": True, "current_site": "youtube.com", "video_playing": False})
        self.assertFalse(BrowserVerifier(probe).verify(expected_site="youtube.com", expect_playing=True).passed)
        probe2 = FakeProbe(browser={"browser_open": True, "current_site": "youtube.com", "video_playing": True})
        self.assertTrue(BrowserVerifier(probe2).verify(expected_site="youtube.com", expect_playing=True).passed)

    def test_closed_browser_fails(self) -> None:
        probe = FakeProbe(browser={"browser_open": False})
        self.assertFalse(BrowserVerifier(probe).verify(expected_site="youtube.com").passed)


class FilesystemVerifierTests(unittest.TestCase):
    def test_existing_path_passes(self) -> None:
        self.assertTrue(FilesystemVerifier(FakeProbe(path_exists=True)).verify("C:/x").passed)

    def test_missing_path_fails(self) -> None:
        self.assertFalse(FilesystemVerifier(FakeProbe(path_exists=False)).verify("C:/x").passed)

    def test_unknown_never_passes(self) -> None:
        self.assertFalse(FilesystemVerifier(FakeProbe(path_exists=None)).verify("C:/x").passed)


class InstallVerifierTests(unittest.TestCase):
    def test_binary_on_disk_passes(self) -> None:
        probe = FakeProbe(executable=r"C:\Users\x\AppData\Local\Programs\Microsoft VS Code\Code.exe")
        verdict = InstallVerifier(probe).verify("vscode")
        self.assertTrue(verdict.passed)
        self.assertIn("installed", verdict.spoken)

    def test_no_binary_means_not_installed(self) -> None:
        # Store/website opened but binary absent -> NOT installed.
        verdict = InstallVerifier(FakeProbe(executable=None)).verify("vlc")
        self.assertFalse(verdict.passed)
        self.assertIn("not installed", verdict.spoken)

    def test_unknown_app_without_executable_fails_closed(self) -> None:
        self.assertFalse(InstallVerifier(FakeProbe(executable=None)).verify("someunknownapp").passed)


class BluetoothVerifierTests(unittest.TestCase):
    def test_radio_on_passes(self) -> None:
        self.assertTrue(BluetoothVerifier(FakeProbe(bluetooth=True)).verify().passed)

    def test_radio_off_fails(self) -> None:
        self.assertFalse(BluetoothVerifier(FakeProbe(bluetooth=False)).verify().passed)

    def test_settings_open_but_unknown_radio_fails(self) -> None:
        # Settings panel visible is NOT evidence the radio is on.
        self.assertFalse(BluetoothVerifier(FakeProbe(bluetooth=None)).verify().passed)


class WifiVerifierTests(unittest.TestCase):
    def test_connected_passes(self) -> None:
        self.assertTrue(WifiVerifier(FakeProbe(wifi=True)).verify().passed)

    def test_disconnected_fails(self) -> None:
        self.assertFalse(WifiVerifier(FakeProbe(wifi=False)).verify().passed)

    def test_unknown_fails(self) -> None:
        self.assertFalse(WifiVerifier(FakeProbe(wifi=None)).verify().passed)


class VerifierSuiteDispatchTests(unittest.TestCase):
    def test_install_mission_uses_disk_not_window(self) -> None:
        # Mission says install VSCode; a window/Store being open must not pass.
        suite = VerifierSuite(FakeProbe(executable=None, windows=[WindowInfo("Microsoft Store")]))
        mission = {"intent": "INSTALL", "context": "browser", "mission": "Install Visual Studio Code"}
        self.assertFalse(suite.verify_mission(mission).passed)

    def test_install_mission_passes_when_binary_present(self) -> None:
        suite = VerifierSuite(FakeProbe(executable=r"C:\Program Files\Git\cmd\git.exe"))
        mission = {"intent": "INSTALL", "context": "browser", "mission": "Install git"}
        self.assertTrue(suite.verify_mission(mission).passed)

    def test_bluetooth_mission_requires_radio(self) -> None:
        suite = VerifierSuite(FakeProbe(bluetooth=None))
        mission = {"intent": "OPEN_APP", "context": "settings", "mission": "Turn on Bluetooth"}
        self.assertFalse(suite.verify_mission(mission).passed)
        suite_on = VerifierSuite(FakeProbe(bluetooth=True))
        self.assertTrue(suite_on.verify_mission(mission).passed)

    def test_browser_mission_checks_site(self) -> None:
        suite = VerifierSuite(FakeProbe(browser={"browser_open": True, "current_site": "youtube.com"}))
        mission = {"intent": "OPEN", "context": "youtube.com", "mission": "Open youtube.com"}
        self.assertTrue(suite.verify_mission(mission).passed)

    def test_open_app_mission_checks_process(self) -> None:
        suite = VerifierSuite(FakeProbe(processes={"calculatorapp.exe"}))
        mission = {"intent": "OPEN_APP", "context": "calculator", "mission": "Open Calculator"}
        self.assertTrue(suite.verify_mission(mission).passed)

    def test_unmappable_mission_fails_closed(self) -> None:
        suite = VerifierSuite(FakeProbe())
        mission = {"intent": "MYSTERY", "context": "void", "mission": "do something undefined"}
        self.assertFalse(suite.verify_mission(mission).passed)


if __name__ == "__main__":
    unittest.main()
