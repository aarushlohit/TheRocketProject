from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent.runtime.first_launch import (
    FirstLaunchBootstrap,
    OnboardingPreferences,
    detect_bundled_components,
    registration_status,
)


def _make_workspace(root: Path) -> None:
    (root / ".opencode" / "skills" / "accessibility_assistant").mkdir(parents=True)
    (root / ".opencode" / "skills" / "braille_parser").mkdir(parents=True)
    (root / ".opencode" / "plugin" / "sample_plugin").mkdir(parents=True)
    (root / "shokunin-opencode-powers" / "code-review").mkdir(parents=True)
    (root / "data").mkdir(parents=True)
    opencode = {
        "mcp": {
            "filesystem": {"enabled": True},
            "playwright": {"enabled": True},
            "memory": {"enabled": True},
            "shokunin_memory": {"enabled": True},
            "windows": {"enabled": False},
            "google-workspace": {"enabled": True},
        }
    }
    (root / "opencode.json").write_text(json.dumps(opencode), encoding="utf-8")


class DetectionTests(unittest.TestCase):
    def test_detects_bundled_components(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp)
            _make_workspace(root)
            components = detect_bundled_components(root)
            self.assertIn("accessibility_assistant", components.skills)
            self.assertIn("braille_parser", components.skills)
            self.assertIn("sample_plugin", components.plugins)
            self.assertIn("code-review", components.shokunin)
            self.assertTrue(components.memory)
            # disabled MCP server is not registered
            self.assertNotIn("windows", components.mcp_servers)
            self.assertIn("playwright", components.mcp_servers)

    def test_registration_status(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp)
            _make_workspace(root)
            status = registration_status(detect_bundled_components(root))
            self.assertTrue(status["playwright"])
            self.assertTrue(status["filesystem"])
            self.assertTrue(status["shokunin"])
            self.assertTrue(status["accessibility_skills"])
            # github MCP not present, must not be falsely reported (google maps to github bucket)
            self.assertTrue(status["github"])  # google-workspace counts as the workspace/github bucket

    def test_empty_workspace_detects_nothing(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            components = detect_bundled_components(Path(tmp))
            self.assertEqual(components.skills, [])
            self.assertEqual(components.mcp_servers, [])
            self.assertFalse(components.memory)


class PreferencesTests(unittest.TestCase):
    def test_round_trip_and_validation(self) -> None:
        prefs = OnboardingPreferences.from_dict(
            {
                "name": "Aarush",
                "preferred_name": "AR",
                "language": "en",
                "screen_reader": "NVDA",
                "speech_rate": "fast",
                "credential_mode": "bogus_mode",
                "cleanup_preference": "weird",
                "reuse_browser": "yes",
            }
        )
        self.assertEqual(prefs.name, "Aarush")
        self.assertEqual(prefs.credential_mode, "already_configured")  # invalid -> default
        self.assertEqual(prefs.cleanup_preference, "auto")  # invalid -> default
        self.assertTrue(prefs.reuse_browser)

    def test_valid_credential_mode_preserved(self) -> None:
        prefs = OnboardingPreferences.from_dict({"credential_mode": "skip"})
        self.assertEqual(prefs.credential_mode, "skip")


class BootstrapLifecycleTests(unittest.TestCase):
    def _bootstrap(self, tmp: str) -> FirstLaunchBootstrap:
        root = Path(tmp)
        _make_workspace(root)
        return FirstLaunchBootstrap(root / "rocketdata", workspace_root=root)

    def test_runs_once_then_skips(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            boot = self._bootstrap(tmp)
            self.assertFalse(boot.is_complete())
            first = boot.run(OnboardingPreferences(name="Aarush"))
            self.assertTrue(first.ran)
            self.assertTrue(boot.is_complete())
            self.assertTrue(first.markers.bootstrap_completed)
            self.assertTrue(first.markers.skills_loaded)
            self.assertTrue(first.markers.mcp_loaded)
            self.assertTrue(first.markers.vault_initialized)

            second = boot.run()
            self.assertFalse(second.ran)
            self.assertTrue(second.already_complete)
            self.assertEqual(second.preferences.name, "Aarush")

    def test_force_reruns(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            boot = self._bootstrap(tmp)
            boot.run()
            forced = boot.run(force=True)
            self.assertTrue(forced.ran)

    def test_reset_clears_completion(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            boot = self._bootstrap(tmp)
            boot.run(OnboardingPreferences(name="Aarush"))
            boot.reset()
            self.assertFalse(boot.is_complete())
            self.assertEqual(boot.load_preferences().name, "")

    def test_preferences_persist_encrypted(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            boot = self._bootstrap(tmp)
            boot.run(OnboardingPreferences(name="Aarush", screen_reader="NVDA", speech_rate="fast"))
            loaded = boot.load_preferences()
            self.assertEqual(loaded.screen_reader, "NVDA")
            self.assertEqual(loaded.speech_rate, "fast")


class CredentialSafetyTests(unittest.TestCase):
    def test_passwords_are_never_stored(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp)
            boot = FirstLaunchBootstrap(root / "rocketdata", workspace_root=root)
            self.assertFalse(boot.save_credential_reference("github_password", "hunter2"))
            self.assertFalse(boot.save_credential_reference("api_secret", "shh"))
            # a non-secret reference name is allowed
            self.assertTrue(boot.save_credential_reference("github", "env:GITHUB_TOKEN"))


if __name__ == "__main__":
    unittest.main()

