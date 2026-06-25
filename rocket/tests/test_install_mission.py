from __future__ import annotations

import unittest

from agent.runtime.install_mission import (
    ADMIN_APPROVED_SPEECH,
    ADMIN_REQUIRED_SPEECH,
    ADMIN_WAITING_SPEECH,
    InstallMissionRunner,
    InstallMissionVerifier,
    UacProbe,
    install_key_from_mission,
)
from agent.runtime.verifier import RealityProbe


class FakeRealityProbe(RealityProbe):
    def __init__(self, *, executable=None, processes=None, windows=None):
        self._executable = executable
        self._processes = processes
        self._windows = windows

    def find_executable(self, executables, search_paths):
        return self._executable

    def running_processes(self):
        return self._processes

    def windows(self):
        return self._windows


class ScriptedUacProbe(UacProbe):
    """Returns a scripted sequence of UAC states, last value sticks."""

    def __init__(self, sequence):
        self._sequence = list(sequence)

    def uac_active(self):
        if not self._sequence:
            return False
        if len(self._sequence) == 1:
            return self._sequence[0]
        return self._sequence.pop(0)


class _Clock:
    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now


class InstallKeyTests(unittest.TestCase):
    def test_resolves_known_apps(self) -> None:
        self.assertEqual(install_key_from_mission("Install Visual Studio Code"), "vscode")
        self.assertEqual(install_key_from_mission("Install git"), "git")
        self.assertEqual(install_key_from_mission("download VLC media player"), "vlc")
        self.assertEqual(install_key_from_mission({"mission": "Install Python", "context": "browser"}), "python")

    def test_unknown_app_returns_empty(self) -> None:
        self.assertEqual(install_key_from_mission("Install SomeRandomApp"), "")


class InstallProofTests(unittest.TestCase):
    def test_binary_on_disk_is_installed(self) -> None:
        probe = FakeRealityProbe(executable=r"C:\Program Files\VideoLAN\VLC\vlc.exe")
        verdict = InstallMissionVerifier(probe).verify("vlc")
        self.assertTrue(verdict.passed)
        self.assertIn("installed", verdict.spoken)

    def test_website_open_is_not_installed(self) -> None:
        # A browser window on the VSCode site, but no Code.exe on disk.
        from agent.runtime.verifier import WindowInfo

        probe = FakeRealityProbe(executable=None, windows=[WindowInfo("Visual Studio Code - Chrome")])
        self.assertFalse(InstallMissionVerifier(probe).verify("vscode").passed)

    def test_store_open_is_not_installed(self) -> None:
        from agent.runtime.verifier import WindowInfo

        probe = FakeRealityProbe(executable=None, windows=[WindowInfo("Microsoft Store")])
        self.assertFalse(InstallMissionVerifier(probe).verify("vlc").passed)

    def test_installer_running_is_not_installed(self) -> None:
        # The installer process is running, but the binary is not on disk yet.
        probe = FakeRealityProbe(executable=None, processes={"vscodesetup.exe"})
        self.assertFalse(InstallMissionVerifier(probe).verify("vscode").passed)


class UacFlowTests(unittest.TestCase):
    def test_no_uac_means_not_required(self) -> None:
        runner = InstallMissionRunner(
            FakeRealityProbe(executable=None),
            uac_probe=ScriptedUacProbe([False]),
        )
        self.assertEqual(runner.wait_for_admin(), "not_required")
        self.assertEqual(runner.spoken, [])

    def test_uac_detected_announced_then_approved(self) -> None:
        clock = _Clock()
        # active, active, then cleared (approved)
        runner = InstallMissionRunner(
            FakeRealityProbe(executable=None),
            uac_probe=ScriptedUacProbe([True, True, False]),
            sleep=lambda _s: None,
            clock=clock.time,
            poll_interval=1.0,
            timeout=10.0,
        )

        def advance(_seconds):
            clock.now += 1.0

        runner._sleep = advance  # type: ignore[assignment]
        result = runner.wait_for_admin()
        self.assertEqual(result, "approved")
        self.assertIn(ADMIN_REQUIRED_SPEECH, runner.spoken)
        self.assertIn(ADMIN_WAITING_SPEECH, runner.spoken)
        self.assertIn(ADMIN_APPROVED_SPEECH, runner.spoken)

    def test_uac_timeout_never_falsely_completes(self) -> None:
        clock = _Clock()
        runner = InstallMissionRunner(
            FakeRealityProbe(executable=r"C:\Program Files\Git\cmd\git.exe"),  # even if binary exists
            uac_probe=ScriptedUacProbe([True]),  # UAC never clears
            sleep=lambda _s: None,
            clock=clock.time,
            poll_interval=1.0,
            timeout=3.0,
        )

        def advance(_seconds):
            clock.now += 1.0

        runner._sleep = advance  # type: ignore[assignment]
        status = runner.run("git")
        self.assertFalse(status.installed)
        self.assertTrue(status.awaiting_admin)
        self.assertEqual(status.admin_result, "timeout")


class RunMissionTests(unittest.TestCase):
    def test_run_verifies_disk_after_no_uac(self) -> None:
        runner = InstallMissionRunner(
            FakeRealityProbe(executable=r"C:\Users\x\AppData\Local\Programs\Microsoft VS Code\Code.exe"),
            uac_probe=ScriptedUacProbe([False]),
        )
        status = runner.run_mission("Install Visual Studio Code")
        self.assertTrue(status.installed)
        self.assertFalse(status.awaiting_admin)
        self.assertEqual(status.admin_result, "not_required")
        self.assertIn("installed", status.spoken)

    def test_run_reports_not_installed_when_binary_absent(self) -> None:
        runner = InstallMissionRunner(
            FakeRealityProbe(executable=None),
            uac_probe=ScriptedUacProbe([False]),
        )
        status = runner.run_mission("Install VLC")
        self.assertFalse(status.installed)
        self.assertIn("not installed", status.spoken)


if __name__ == "__main__":
    unittest.main()
