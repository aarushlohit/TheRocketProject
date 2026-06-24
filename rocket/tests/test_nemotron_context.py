from __future__ import annotations

import unittest

from agent.adapters.nemotron import NemotronAdapter


class NemotronContextTests(unittest.TestCase):
    def test_follow_up_search_stays_in_active_app(self) -> None:
        adapter = NemotronAdapter()
        adapter._remember_task("Open YouTube.")

        self.assertEqual(adapter._contextualize_task("Search cars."), "Search cars on YouTube.")

    def test_follow_up_youtube_reuses_existing_chrome_tab(self) -> None:
        adapter = NemotronAdapter()
        adapter._remember_task("Open Chrome.")

        self.assertEqual(
            adapter._contextualize_task("Go to YouTube."),
            "Navigate existing Chrome tab to https://www.youtube.com.",
        )

    def test_runtime_context_is_included(self) -> None:
        adapter = NemotronAdapter()
        adapter.set_runtime_context(
            {
                "setup_complete": True,
                "access_mode": "workspace",
                "credential_mode": "already_configured",
                "workspace_path": r"C:\Users\Aarush\Documents\OpenCodeWorkspace",
                "credential_refs": {"github": "vault"},
            }
        )

        context = adapter._context_text()
        self.assertIn("Runtime setup:", context)
        self.assertIn("workspace", context)
        self.assertIn("already_configured", context)
        self.assertIn("github", context)


if __name__ == "__main__":
    unittest.main()
