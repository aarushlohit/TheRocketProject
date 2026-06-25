from __future__ import annotations

import unittest

from agent.adapters.nemotron import NemotronAdapter
from agent.runtime.browser_state import mission_to_task
from agent.runtime.mission_brief import (
    WindowPolicy,
    build_mission_brief,
    cleanup_policy,
    window_policy,
)


def _compile(adapter: NemotronAdapter, text: str) -> dict:
    from agent.runtime.browser_state import parse_mission

    return parse_mission(adapter._compile_task(text))


class MissionBriefTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = NemotronAdapter()

    def test_brief_has_required_sections(self) -> None:
        self.adapter._remember_task(self.adapter._compile_task("Open YouTube."))
        brief = build_mission_brief(self.adapter._compile_task("Search cats."))
        for header in ("MISSION", "CONTEXT", "GOAL", "DONE WHEN", "WINDOW POLICY", "AFTER GOAL"):
            self.assertIn(header, brief)

    def test_search_inside_youtube_goal(self) -> None:
        self.adapter._remember_task(self.adapter._compile_task("Open YouTube."))
        brief = build_mission_brief(self.adapter._compile_task("Search cats."))
        self.assertIn("Search inside YouTube", brief)

    def test_brief_never_contains_json(self) -> None:
        mission_task = self.adapter._compile_task("Search cats on YouTube.")
        brief = build_mission_brief(mission_task)
        self.assertNotIn("{", brief)
        self.assertNotIn("}", brief)
        self.assertNotIn("success_criteria", brief)
        self.assertNotIn("predicted_browser_state", brief)

    def test_context_reflects_open_site(self) -> None:
        self.adapter._remember_task(self.adapter._compile_task("Open YouTube."))
        brief = build_mission_brief(self.adapter._compile_task("Search cats."))
        self.assertIn("YouTube", brief.split("CONTEXT")[1].split("GOAL")[0])

    def test_done_when_is_human_readable(self) -> None:
        brief = build_mission_brief(self.adapter._compile_task("Search cats on YouTube."))
        done = brief.split("DONE WHEN")[1].split("WINDOW POLICY")[0]
        self.assertIn("Search results are visible", done)

    def test_install_brief_done_when(self) -> None:
        brief = build_mission_brief(self.adapter._compile_task("Install VSCode."))
        self.assertIn("install source is open", brief.lower())

    def test_unparseable_task_still_produces_brief(self) -> None:
        brief = build_mission_brief("just do something")
        self.assertIn("MISSION", brief)
        self.assertIn("just do something", brief)

    def test_accepts_mission_dict(self) -> None:
        mission = _compile(self.adapter, "Search cats on YouTube.")
        brief = build_mission_brief(mission)
        self.assertIn("MISSION", brief)


class CleanupPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = NemotronAdapter()

    def test_youtube_is_persistent(self) -> None:
        mission = _compile(self.adapter, "Open YouTube.")
        self.assertEqual(cleanup_policy(mission), "persistent")

    def test_chrome_is_persistent(self) -> None:
        mission = _compile(self.adapter, "Open Chrome.")
        self.assertEqual(cleanup_policy(mission), "persistent")

    def test_calculator_oneshot_is_temporary(self) -> None:
        mission = _compile(self.adapter, "Open calc and calc 2+2.")
        self.assertEqual(cleanup_policy(mission), "temporary")

    def test_keep_open_phrase_forces_persistent(self) -> None:
        # The policy itself honours a keep-open phrase carried in the mission text.
        mission = {
            "intent": "CALCULATE",
            "context": "calculator",
            "mission": "Calculate 2+2 in Calculator, keep open",
        }
        self.assertEqual(cleanup_policy(mission), "persistent")

    def test_unknown_defaults_persistent(self) -> None:
        self.assertEqual(cleanup_policy(None), "persistent")
        self.assertEqual(cleanup_policy({"intent": "OPEN", "context": "browser", "mission": "x"}), "persistent")


class WindowPolicyTests(unittest.TestCase):
    def test_policy_is_strict_by_default(self) -> None:
        policy = window_policy({"intent": "OPEN", "context": "youtube.com"})
        self.assertIsInstance(policy, WindowPolicy)
        self.assertTrue(policy.reuse_existing)
        self.assertTrue(policy.foreground)
        self.assertTrue(policy.maximize)
        self.assertFalse(policy.allow_minimized)
        self.assertFalse(policy.allow_duplicate)

    def test_describe_mentions_reuse_and_no_duplicate(self) -> None:
        text = WindowPolicy().describe("Chrome")
        self.assertIn("Reuse", text)
        self.assertIn("duplicate", text)
        self.assertIn("maximize", text)


class ConversationalBrowserFlowTests(unittest.TestCase):
    """The full requested flow keeps coherent browser context end to end."""

    def test_full_flow_context_is_coherent(self) -> None:
        adapter = NemotronAdapter()
        steps = [
            "Open YouTube.",
            "Search cats.",
            "Play first video.",
            "Pause.",
            "Resume.",
            "Open new tab.",
            "Search Spotify.",
            "Go back.",
            "Return to YouTube.",
        ]
        briefs = []
        for step in steps:
            task = adapter._compile_task(step)
            briefs.append(build_mission_brief(task))
            adapter._remember_task(task)

        # Every brief is JSON-free and human-readable.
        for brief in briefs:
            self.assertNotIn("{", brief)
            self.assertIn("MISSION", brief)

        # "Search cats" right after opening YouTube must search inside YouTube.
        self.assertIn("Search inside YouTube", briefs[1])
        # Returning to YouTube ends back in YouTube context.
        self.assertIn("YouTube", briefs[-1])


if __name__ == "__main__":
    unittest.main()
