from __future__ import annotations

import unittest

from agent.adapters.nemotron import NemotronAdapter, _audio_format, _should_remember_task
from agent.adapters.prompts import parser_user_prompt
from agent.runtime.browser_state import parse_mission


class NemotronContextTests(unittest.TestCase):
    def test_follow_up_search_stays_in_active_app(self) -> None:
        adapter = NemotronAdapter()
        adapter._remember_task("Open YouTube.")

        mission = parse_mission(adapter._compile_task("Search cars."))

        self.assertIsNotNone(mission)
        self.assertEqual(mission["intent"], "SEARCH")
        self.assertEqual(mission["context"], "youtube.com")
        self.assertEqual(mission["mission"], "Search cars inside youtube.com")
        self.assertTrue(any("Do not perform Google Search" in item for item in mission["instructions"]))

    def test_follow_up_youtube_reuses_existing_chrome_tab(self) -> None:
        adapter = NemotronAdapter()
        adapter._remember_task("Open Chrome.")

        self.assertEqual(
            adapter._contextualize_task("Go to YouTube."),
            "Navigate existing Chrome tab to https://www.youtube.com.",
        )

    def test_multi_turn_youtube_playback_state(self) -> None:
        adapter = NemotronAdapter()
        open_mission = parse_mission(adapter._compile_task("Open YouTube."))
        adapter._remember_task(adapter._compile_task("Open YouTube."))
        search_mission = parse_mission(adapter._compile_task("Search cats."))
        adapter._remember_task(adapter._compile_task("Search cats."))
        play_mission = parse_mission(adapter._compile_task("Play first result."))
        adapter._remember_task(adapter._compile_task("Play first result."))
        pause_mission = parse_mission(adapter._compile_task("Pause."))

        self.assertEqual(open_mission["context"], "youtube.com")
        self.assertEqual(search_mission["context"], "youtube.com")
        self.assertEqual(play_mission["intent"], "PLAY")
        self.assertEqual(play_mission["context"], "youtube.com")
        self.assertEqual(pause_mission["intent"], "PAUSE")
        self.assertEqual(pause_mission["context"], "youtube.com")

    def test_model_json_search_mission_is_normalized(self) -> None:
        adapter = NemotronAdapter()
        raw = (
            '{"intent":"SEARCH","context":"youtube.com","mission":"Search cats inside YouTube",'
            '"complexity":"LOW","estimated_steps":2,"success_criteria":["youtube_search_completed"],'
            '"instructions":["Search inside YouTube"]}'
        )

        mission = parse_mission(adapter._compile_task(raw))

        self.assertEqual(mission["context"], "youtube.com")
        self.assertEqual(mission["mission"], "Search cats inside youtube.com")
        self.assertEqual(mission["predicted_browser_state"]["search_query"], "cats")

    def test_install_game_breaks_out_of_youtube_context(self) -> None:
        adapter = NemotronAdapter()
        adapter._remember_task(adapter._compile_task("Open YouTube."))

        mission = parse_mission(adapter._compile_task("Install Beach Buggy game."))

        self.assertEqual(mission["intent"], "INSTALL")
        self.assertEqual(mission["context"], "browser")
        self.assertIn("Microsoft Store", mission["mission"])
        self.assertNotIn("inside youtube.com", mission["mission"].lower())
        self.assertTrue(any("not a YouTube" in item for item in mission["instructions"]))

    def test_model_added_youtube_is_removed_from_install_task(self) -> None:
        adapter = NemotronAdapter()
        adapter._remember_task(adapter._compile_task("Open YouTube."))
        raw = (
            '{"intent":"BROWSER_ACTION","context":"youtube.com",'
            '"mission":"Install beach buggy on YouTube youtube.com",'
            '"complexity":"MEDIUM","estimated_steps":3,'
            '"success_criteria":["browser_action_verified"],'
            '"instructions":["Perform the action inside youtube.com"]}'
        )

        mission = parse_mission(adapter._compile_task(raw))

        self.assertEqual(mission["intent"], "INSTALL")
        self.assertEqual(mission["context"], "browser")
        self.assertIn("Install beach buggy", mission["mission"])
        self.assertNotIn("YouTube", mission["mission"])
        self.assertNotIn("youtube.com", mission["mission"])

    def test_desktop_app_command_breaks_out_of_current_site_context(self) -> None:
        adapter = NemotronAdapter()
        adapter._remember_task(adapter._compile_task("Open YouTube."))

        mission = parse_mission(adapter._compile_task("Open Windows Settings."))

        self.assertEqual(mission["intent"], "OPEN_APP")
        self.assertEqual(mission["context"], "settings")
        self.assertNotIn("youtube.com", mission["mission"].lower())
        self.assertFalse(any("Perform the action inside youtube.com" in item for item in mission["instructions"]))

    def test_open_whatsapp_compiles_as_desktop_app_not_browser(self) -> None:
        adapter = NemotronAdapter()

        mission = parse_mission(adapter._compile_task("Open WhatsApp application."))

        self.assertEqual(mission["intent"], "OPEN_APP")
        self.assertEqual(mission["context"], "whatsapp")
        self.assertIn("Open installed WhatsApp application", mission["mission"])
        self.assertIn("whatsapp_visible", mission["success_criteria"])
        self.assertFalse(any("Reuse active browser" in item for item in mission["instructions"]))

    def test_whatsapp_send_message_preserves_message_intent(self) -> None:
        adapter = NemotronAdapter()

        mission = parse_mission(
            adapter._compile_task(
                "Open WhatsApp and in Rocket group chat send message hi from opencode passed isolated testing 3."
            )
        )

        self.assertEqual(mission["intent"], "SEND_MESSAGE")
        self.assertEqual(mission["context"], "whatsapp")
        self.assertIn("Rocket group", mission["mission"])
        self.assertIn("hi from opencode passed isolated testing 3", mission["mission"])
        self.assertNotIn("Open WhatsApp and", mission["mission"])
        self.assertIn("message_sent_visible", mission["success_criteria"])
        self.assertTrue(any("Verify the sent message" in item for item in mission["instructions"]))

    def test_calculator_expression_is_goal_not_open_only(self) -> None:
        adapter = NemotronAdapter()

        mission = parse_mission(adapter._compile_task("Open calc and calc 2+2."))

        self.assertEqual(mission["intent"], "CALCULATE")
        self.assertEqual(mission["context"], "calculator")
        self.assertIn("Calculate 2+2", mission["mission"])
        self.assertIn("result is 4", mission["mission"])
        self.assertIn("calculator_result_visible", mission["success_criteria"])
        self.assertTrue(any("Do not report success merely because Calculator opened" in item for item in mission["instructions"]))

    def test_plain_calculate_uses_calculator_context(self) -> None:
        adapter = NemotronAdapter()

        mission = parse_mission(adapter._compile_task("Calculate 2+2."))

        self.assertEqual(mission["intent"], "CALCULATE")
        self.assertEqual(mission["context"], "calculator")

    def test_model_added_youtube_is_removed_from_desktop_app_task(self) -> None:
        adapter = NemotronAdapter()
        adapter._remember_task(adapter._compile_task("Open YouTube."))
        raw = (
            '{"intent":"BROWSER_ACTION","context":"youtube.com",'
            '"mission":"Open Windows Settings on YouTube youtube.com",'
            '"complexity":"LOW","estimated_steps":2,'
            '"success_criteria":["browser_action_verified"],'
            '"instructions":["Perform the action inside youtube.com"]}'
        )

        mission = parse_mission(adapter._compile_task(raw))

        self.assertEqual(mission["intent"], "OPEN_APP")
        self.assertEqual(mission["context"], "settings")
        self.assertIn("Open installed Windows Settings application", mission["mission"])
        self.assertNotIn("YouTube", mission["mission"])
        self.assertNotIn("youtube.com", mission["mission"])

    def test_file_task_does_not_preserve_current_site_context(self) -> None:
        adapter = NemotronAdapter()
        adapter._remember_task(adapter._compile_task("Open YouTube."))

        mission = parse_mission(adapter._compile_task("Create a notes file in workspace."))

        self.assertEqual(mission["context"], "browser")
        self.assertNotIn("youtube.com", mission["mission"].lower())

    def test_parser_garbage_becomes_try_again(self) -> None:
        adapter = NemotronAdapter()
        raw = ', 1, 1, 1, 1, 1, 1, 1, 1.5 {"intent":"OPENCODING, 1, 1, 1, 1, 1, 1'

        mission = parse_mission(adapter._compile_task(raw))

        self.assertEqual(mission["mission"], "try_again")
        self.assertIn("input_unclear", mission["success_criteria"])

    def test_try_again_is_not_remembered_as_browser_history(self) -> None:
        adapter = NemotronAdapter()
        adapter._remember_task(adapter._compile_task("Open YouTube."))
        before = adapter._browser_state.to_dict()
        garbage_task = adapter._compile_task(
            ', 1, 1, 1, 1, 1, 1, 1, 1.5 {"intent":"OPENCODING, 1, 1, 1, 1, 1, 1'
        )

        self.assertFalse(_should_remember_task(garbage_task))
        self.assertEqual(adapter._browser_state.to_dict(), before)

    def test_new_tab_spotify_then_return_youtube(self) -> None:
        adapter = NemotronAdapter()
        adapter._remember_task(adapter._compile_task("Open YouTube."))
        adapter._remember_task(adapter._compile_task("Open new tab."))
        spotify_mission = parse_mission(adapter._compile_task("Search Spotify."))
        adapter._remember_task(adapter._compile_task("Search Spotify."))
        return_mission = parse_mission(adapter._compile_task("Return to YouTube."))
        adapter._remember_task(adapter._compile_task("Return to YouTube."))
        youtube_search = parse_mission(adapter._compile_task("Search lofi music."))

        self.assertEqual(spotify_mission["context"], "spotify.com")
        self.assertEqual(return_mission["intent"], "RETURN_TAB")
        self.assertIn("previous_tab_focused", return_mission["success_criteria"])
        self.assertEqual(youtube_search["context"], "youtube.com")

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

    def test_audio_format_normalization(self) -> None:
        self.assertEqual(_audio_format("wav"), "wav")
        self.assertEqual(_audio_format("audio/wav"), "wav")
        self.assertEqual(_audio_format("audio/mpeg"), "mp3")
        self.assertEqual(_audio_format("unknown"), "wav")

    def test_audio_prompt_is_transcription_first_and_context_aware(self) -> None:
        prompt = parser_user_prompt(
            "audio",
            context='BrowserState: {"current_site":"youtube.com","browser_open":true}',
        )

        self.assertIn("Silently transcribe the command into one safe", prompt)
        self.assertIn("you tube=YouTube", prompt)
        self.assertIn("calc=Calculator", prompt)
        self.assertIn("Calculate <expression> in Calculator", prompt)
        self.assertIn("exact group/contact names", prompt)
        self.assertIn("search inside YouTube", prompt)
        self.assertIn("try_again", prompt)

    def test_drawing_prompt_is_visual_command_first_and_safe(self) -> None:
        prompt = parser_user_prompt(
            "image",
            context='BrowserState: {"current_site":"youtube.com","browser_open":true}',
        )

        self.assertIn("Rocket drawing mode", prompt)
        self.assertIn("readable handwriting", prompt)
        self.assertIn("play triangle means PLAY", prompt)
        self.assertIn("Calculate 2+2 in Calculator", prompt)
        self.assertIn("use only readable letters/words", prompt)
        self.assertIn("random scribble", prompt)
        self.assertIn("try_again", prompt)


if __name__ == "__main__":
    unittest.main()
