from __future__ import annotations

import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from agent.runtime.memory import RocketMemory, RocketProfile


class ProfileCountryMigrationTests(unittest.TestCase):
    def test_profile_has_country_field_defaulting_empty(self) -> None:
        self.assertEqual(RocketProfile().country, "")
        self.assertIn("country", asdict(RocketProfile()))

    def test_legacy_rows_without_country_load_safely(self) -> None:
        # Simulate a stored profile that predates the country field.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            memory = RocketMemory(Path(tmp))
            legacy = {
                "name": "Aarush",
                "preferred_name": "AR",
                "email": "a@example.com",
                "browser": "chrome",
            }
            memory.set("profile", legacy)
            loaded = memory.load_profile()
            self.assertEqual(loaded.name, "Aarush")
            self.assertEqual(loaded.country, "")  # missing field -> safe default

    def test_country_round_trips(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            memory = RocketMemory(Path(tmp))
            memory.save_profile(RocketProfile(name="Aarush", country="India"))
            self.assertEqual(memory.load_profile().country, "India")


class ApplyProfileTests(unittest.TestCase):
    def _adapter(self, tmp: str):
        from agent.runtime.adapter import RocketAdapter

        return RocketAdapter(repo_root=Path(tmp), data_dir=Path(tmp) / "data")

    def test_apply_profile_with_country_no_longer_raises(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            adapter = self._adapter(tmp)
            adapter.apply_profile({"name": "Aarush", "country": "India", "browser": "chrome"})
            self.assertEqual(adapter.profile.country, "India")
            self.assertEqual(adapter.profile.name, "Aarush")

    def test_apply_profile_without_country_preserves_existing(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            adapter = self._adapter(tmp)
            adapter.apply_profile({"country": "Canada"})
            adapter.apply_profile({"name": "AR"})  # no country key in this update
            self.assertEqual(adapter.profile.country, "Canada")
            self.assertEqual(adapter.profile.name, "AR")


if __name__ == "__main__":
    unittest.main()
