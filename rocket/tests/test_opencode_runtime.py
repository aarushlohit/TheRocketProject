from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess

from agent.runtime.opencode_runtime import OpenCodeRuntimeManager
from agent.runtime.setup import RocketSetup
from agent.server.task_quality import assess_task_quality
from agent.utils.config import load_config
from agent.runtime.browser_state import BrowserState, compile_browser_mission, mission_to_task, task_display_text
from agent.runtime.opencode_cli_client import (
    DEFAULT_OPENCODE_MODELS,
    OpenCodeCliClient,
    _extract_message,
    _extract_session_id,
    _tail,
    _configured_timeout,
    _desktop_expectation,
    _expected_calculator_result,
    _has_json_events,
    _normalize_calculator_text,
    _process_visible,
    _server_runtime_error_message,
    _should_cleanup_after_success,
    _should_try_next_model,
    _short_run_message,
)
from agent.runtime.memory import RocketProfile
from agent.runtime.results import RocketExecutionResult


class OpenCodeRuntimeTests(unittest.TestCase):
    def test_opencode_default_models_use_free_priority_list(self) -> None:
        env = os.environ.copy()
        env.pop("ROCKET_OPENCODE_MODEL", None)
        env.pop("ROCKET_OPENCODE_MODELS", None)
        with patch.dict("os.environ", env, clear=True):
            client = OpenCodeCliClient(Path.cwd(), profile=object())  # type: ignore[arg-type]

        self.assertEqual(client.models, list(DEFAULT_OPENCODE_MODELS))
        self.assertEqual(client.model, "opencode/mimo-v2.5-free")

    def test_opencode_timeout_is_disabled_by_default(self) -> None:
        env = os.environ.copy()
        env.pop("ROCKET_OPENCODE_TIMEOUT_SECONDS", None)
        with patch.dict("os.environ", env, clear=True):
            self.assertIsNone(_configured_timeout())

    def test_opencode_direct_fresh_execution_is_default(self) -> None:
        env = os.environ.copy()
        env.pop("ROCKET_OPENCODE_PERSISTENT_SERVER", None)
        env.pop("ROCKET_OPENCODE_REUSE_SESSION", None)
        with patch.dict("os.environ", env, clear=True):
            client = OpenCodeCliClient(Path.cwd(), profile=RocketProfile(), session_id="ses_old")

        self.assertFalse(client.persistent_server)
        self.assertFalse(client.reuse_session)
        self.assertEqual(client.output_format, "default")

    def test_prompt_uses_all_powers_and_compact_human_mission(self) -> None:
        mission = mission_to_task(compile_browser_mission("Search cats", BrowserState(current_site="youtube.com", browser_open=True)))
        client = OpenCodeCliClient(Path.cwd(), profile=RocketProfile(), browser_state={"current_site": "youtube.com"})
        prompt = client._build_prompt(mission)

        self.assertIn("MISSION\n", prompt)
        self.assertIn("Search cats on YouTube", prompt)
        self.assertIn("GOAL\nSearch inside YouTube", prompt)
        self.assertIn("DONE WHEN", prompt)
        self.assertIn("WINDOW POLICY", prompt)
        self.assertIn("AVAILABLE POWERS", prompt)
        self.assertIn("all configured OpenCode MCP servers", prompt)
        self.assertIn("skills", prompt)
        self.assertIn("superpowers", prompt)
        self.assertIn("Browser:", prompt)
        self.assertIn("youtube.com", prompt)
        self.assertNotIn('"predicted_browser_state"', prompt)

    def test_opencode_models_can_be_overridden_as_comma_list(self) -> None:
        env = os.environ.copy()
        env["ROCKET_OPENCODE_MODELS"] = "opencode/a, opencode/b"
        with patch.dict("os.environ", env, clear=True):
            client = OpenCodeCliClient(Path.cwd(), profile=object())  # type: ignore[arg-type]

        self.assertEqual(client.models, ["opencode/a", "opencode/b"])

    def test_desktop_expectation_detects_app_tasks(self) -> None:
        self.assertEqual(_desktop_expectation("Open Chrome")["process"], "chrome")  # type: ignore[index]
        self.assertEqual(_desktop_expectation("Search for yashu in Chrome")["process"], "chrome")  # type: ignore[index]
        self.assertEqual(_desktop_expectation("Open WhatsApp")["process"], "whatsapp")  # type: ignore[index]
        whatsapp_mission = mission_to_task(compile_browser_mission("Open WhatsApp application", BrowserState()))
        self.assertEqual(_desktop_expectation(whatsapp_mission)["process"], "whatsapp")  # type: ignore[index]
        whatsapp_message = mission_to_task(
            compile_browser_mission(
                "Open WhatsApp and in Rocket group chat send message hi from opencode passed isolated testing 3",
                BrowserState(),
            )
        )
        self.assertEqual(_desktop_expectation(whatsapp_message)["process"], "whatsapp")  # type: ignore[index]
        calculator_mission = mission_to_task(compile_browser_mission("Open calc and calc 2+2", BrowserState()))
        self.assertEqual(_desktop_expectation(calculator_mission)["process"], "calculator")  # type: ignore[index]
        self.assertIn("calculatorapp", _desktop_expectation(calculator_mission)["processes"])  # type: ignore[index]
        self.assertNotIn("applicationframehost", _desktop_expectation(calculator_mission)["processes"])  # type: ignore[index]
        self.assertIsNone(_desktop_expectation("Create a file in workspace"))

    def test_application_frame_host_without_title_does_not_verify_calculator(self) -> None:
        snapshot = [{"ProcessName": "ApplicationFrameHost", "MainWindowTitle": ""}]

        self.assertFalse(_process_visible(snapshot, ["calculator", "calculatorapp"], ["calculator"]))

    def test_application_frame_host_with_calculator_title_verifies_calculator(self) -> None:
        snapshot = [{"ProcessName": "ApplicationFrameHost", "MainWindowTitle": "Calculator"}]

        self.assertTrue(_process_visible(snapshot, ["calculator", "calculatorapp"], ["calculator"]))

    def test_calculator_expected_result_is_extracted(self) -> None:
        self.assertEqual(
            _expected_calculator_result("Calculate 2+2 in Calculator and verify the result is 4"),
            "4",
        )
        self.assertEqual(_expected_calculator_result("Calculate 8/2 in Calculator"), "4")

    def test_calculator_display_text_is_normalized(self) -> None:
        self.assertEqual(_normalize_calculator_text("Display is 4"), "4")

    def test_cleanup_policy_closes_temporary_calculator_task(self) -> None:
        mission = mission_to_task(compile_browser_mission("Open calc and calc 2+2", BrowserState()))
        expectation = _desktop_expectation(mission)

        self.assertTrue(_should_cleanup_after_success(mission, expectation))  # type: ignore[arg-type]

    def test_cleanup_policy_keeps_persistent_media_task_open(self) -> None:
        mission = mission_to_task(compile_browser_mission("Open YouTube and play cats", BrowserState()))
        expectation = {"label": "chrome", "process": "chrome"}

        self.assertFalse(_should_cleanup_after_success(mission, expectation))

    def test_opencode_always_skips_permissions_for_cli_runtime(self) -> None:
        client = OpenCodeCliClient(Path.cwd(), profile=RocketProfile())

        def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
            self.assertIn("--dangerously-skip-permissions", command)
            self.assertEqual(command[command.index("--agent") + 1], "rocket-blind")
            self.assertNotIn("--attach", command)
            self.assertNotIn("--session", command)
            return CompletedProcess(command, 0, stdout='{"message":"ok"}\n', stderr="")

        with (
            patch.object(client, "available", return_value=True),
            patch("agent.runtime.opencode_cli_client._ensure_opencode_server", return_value=""),
            patch("agent.runtime.opencode_cli_client.subprocess.run", side_effect=fake_run),
        ):
            result = client.execute("Create a file in workspace")

        self.assertTrue(result.success)

    def test_task_quality_rejects_meaningless_input(self) -> None:
        self.assertFalse(assess_task_quality("").accepted)
        self.assertFalse(assess_task_quality("unknown").accepted)
        self.assertFalse(assess_task_quality("maybe open something").accepted)
        self.assertFalse(assess_task_quality("aa").accepted)
        self.assertFalse(assess_task_quality("open").accepted)
        self.assertTrue(assess_task_quality("Open Chrome").accepted)
        self.assertTrue(assess_task_quality("Calculate 2+2 in Calculator").accepted)
        self.assertTrue(assess_task_quality("calc 2+2").accepted)
        mission = mission_to_task(compile_browser_mission("Search cats", BrowserState(current_site="youtube.com")))
        self.assertTrue(assess_task_quality(mission).accepted)
        unclear_mission = json.dumps(
            {
                "intent": "BROWSER_ACTION",
                "context": "unknown",
                "mission": "try_again",
                "success_criteria": ["input_unclear"],
                "instructions": ["Ask the user to repeat the command"],
            }
        )
        self.assertFalse(assess_task_quality(unclear_mission).accepted)
        unclear_drawing = json.dumps(
            {
                "intent": "BROWSER_ACTION",
                "context": "unknown",
                "mission": "random scribble",
                "success_criteria": ["input_unclear"],
                "instructions": ["Ask the user to draw or write the command again"],
            }
        )
        self.assertFalse(assess_task_quality(unclear_drawing).accepted)
        malformed_drawing = json.dumps(
            {
                "intent": "BROWSER_ACTION",
                "context": "browser",
                "mission": ", 1, 1, 1, 1, 1, 1, 1, 1.5 {\"intent\":\"OPENCODING, 1, 1, 1",
                "success_criteria": ["browser_action_verified"],
                "instructions": ["Reuse active browser"],
            }
        )
        self.assertFalse(assess_task_quality(malformed_drawing).accepted)

    def test_setup_normalizes_access_mode_to_workspace_root(self) -> None:
        setup = RocketSetup.from_dict({"access_mode": "full"})

        self.assertEqual(setup.access_mode, "workspace")
        self.assertFalse(setup.full_access)

    def test_config_uses_runtime_data_dir_env_for_installed_app(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            with patch.dict("os.environ", {"ROCKET_DATA_DIR": root}):
                config = load_config(config_path=Path(root) / "missing.yaml")

        self.assertEqual(config.data_dir, Path(root))

    def test_browser_mission_tracks_tabs_and_context(self) -> None:
        state = BrowserState(current_site="youtube.com", browser_open=True)
        new_tab = compile_browser_mission("Open new tab", state)
        spotify = compile_browser_mission(
            "Search Spotify",
            BrowserState.from_dict(new_tab["predicted_browser_state"]),
        )
        back = compile_browser_mission(
            "Return to YouTube",
            BrowserState.from_dict(spotify["predicted_browser_state"]),
        )

        self.assertEqual(new_tab["intent"], "OPEN_TAB")
        self.assertEqual(spotify["context"], "spotify.com")
        self.assertEqual(back["intent"], "RETURN_TAB")
        self.assertIn("previous_tab_focused", back["success_criteria"])

    def test_browser_search_query_strips_site_context_words(self) -> None:
        mission = compile_browser_mission("Search cats inside YouTube", BrowserState())

        self.assertEqual(mission["context"], "youtube.com")
        self.assertEqual(mission["predicted_browser_state"]["search_query"], "cats")
        self.assertNotIn("inside YouTube", mission["predicted_browser_state"]["search_query"])

    def test_opencode_run_message_stays_short(self) -> None:
        message = _short_run_message("Open YouTube and search for cat videos. " * 50)

        self.assertLess(len(message), 260)
        self.assertIn("attached prompt file", message)

    def test_opencode_run_message_uses_display_task_not_json(self) -> None:
        mission = mission_to_task(compile_browser_mission("Open WhatsApp application", BrowserState()))
        message = _short_run_message(mission)

        self.assertIn("Current task: Open WhatsApp", message)
        self.assertNotIn("{", message)
        self.assertNotIn("OPEN_APP", message)

    def test_mission_display_text_hides_internal_json(self) -> None:
        whatsapp = mission_to_task(compile_browser_mission("Open WhatsApp application", BrowserState()))
        youtube = mission_to_task(compile_browser_mission("Search cats", BrowserState(current_site="youtube.com")))

        self.assertEqual(task_display_text(whatsapp), "Open WhatsApp")
        self.assertEqual(task_display_text(youtube), "Search cats on YouTube")
        self.assertNotIn("{", task_display_text(whatsapp))

    def test_subprocess_stream_parsers_tolerate_none(self) -> None:
        self.assertEqual(_extract_message(None), "")
        self.assertEqual(_extract_session_id(None), "")
        self.assertEqual(_tail(None), "")

    def test_extract_message_prefers_structured_speech(self) -> None:
        stdout = "STATUS: DONE\nSPEECH: Hi there!\nCONTENT:\n"

        self.assertEqual(_extract_message(stdout), "Hi there!")

    def test_server_log_certificate_error_is_retryable(self) -> None:
        message = _server_runtime_error_message(
            'timestamp=x level=ERROR message="stream error" error.error="Error: certificate is not yet valid"'
        )

        self.assertIn("certificate is not yet valid", message)
        self.assertTrue(
            _should_try_next_model(
                RocketExecutionResult(
                    task="Open Calculator",
                    intent="opencode",
                    executor="opencode-cli",
                    success=False,
                    message=message,
                )
            )
        )

    def test_opencode_parser_ignores_synthetic_compaction_events(self) -> None:
        stdout = "\n".join(
            [
                '{"type":"step_finish","sessionID":"ses_old","part":{"type":"step-finish"}}',
                '{"type":"text","sessionID":"ses_old","part":{"type":"text","synthetic":true,"metadata":{"compaction_continue":true},"text":"Continue if you have next steps"}}',
            ]
        )

        self.assertTrue(_has_json_events(stdout))
        self.assertEqual(_extract_message(stdout), "")

    def test_open_whatsapp_does_not_accept_stale_json_log_as_success(self) -> None:
        client = OpenCodeCliClient(Path.cwd(), profile=RocketProfile())
        stale_stdout = (
            '{"type":"step_finish","sessionID":"ses_old","part":{"type":"step-finish"}}\n'
            '{"type":"text","sessionID":"ses_old","part":{"type":"text","synthetic":true,'
            '"metadata":{"compaction_continue":true},"text":"Continue if you have next steps"}}\n'
        )

        def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
            return CompletedProcess(command, 0, stdout=stale_stdout, stderr="")

        with (
            patch.object(client, "available", return_value=True),
            patch("agent.runtime.opencode_cli_client._ensure_opencode_server", return_value=""),
            patch("agent.runtime.opencode_cli_client.subprocess.run", side_effect=fake_run),
            patch("agent.runtime.opencode_cli_client._verify_desktop_expectation", return_value=(False, "Expected whatsapp process/window was not visible after OpenCode returned.")),
        ):
            result = client.execute("Open WhatsApp")

        self.assertFalse(result.success)
        self.assertIn("could not verify", result.message.lower())
        self.assertNotIn("Continue if you have next steps", result.message)

    def test_merges_missing_mcp_and_plugin_without_overwriting_existing(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            powers = _powers_fixture(root_path)
            config_dir = root_path / "opencode"
            config_dir.mkdir()
            (config_dir / "opencode.json").write_text(
                json.dumps(
                    {
                        "mcp": {
                            "github": {
                                "type": "local",
                                "command": ["custom-github"],
                                "enabled": True,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            setup = RocketSetup(
                setup_complete=True,
                opencode_config_dir=str(config_dir),
                powers_source_dir=str(powers),
                workspace_path=str(root_path / "workspace"),
            )
            report = OpenCodeRuntimeManager(root_path / "data", setup).ensure_ready()

            merged = json.loads((config_dir / "opencode.json").read_text(encoding="utf-8"))
            self.assertEqual(merged["permission"], "allow")
            self.assertEqual(merged["mcp"]["github"]["command"], ["custom-github"])
            self.assertIn("rocket-windows", merged["mcp"])
            self.assertIn("windows_mcp.py", " ".join(merged["mcp"]["rocket-windows"]["command"]))
            self.assertIn("shokunin-memory", merged["mcp"])
            self.assertIn("superpowers@git+https://github.com/obra/superpowers.git", merged["plugin"])
            self.assertIn("added MCP config: rocket-windows", report.actions)
            self.assertIn("added MCP config: shokunin-memory", report.actions)

    def test_migrates_plaintext_env_secret_to_vault(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            powers = _powers_fixture(root_path)
            config_dir = root_path / "opencode"
            config_dir.mkdir()
            (config_dir / "opencode.json").write_text(
                json.dumps(
                    {
                        "mcp": {
                            "github": {
                                "type": "local",
                                "command": ["npx", "github"],
                                "enabled": True,
                                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_real_token"},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            setup = RocketSetup(
                setup_complete=True,
                opencode_config_dir=str(config_dir),
                powers_source_dir=str(powers),
                workspace_path=str(root_path / "workspace"),
            )
            manager = OpenCodeRuntimeManager(root_path / "data", setup)
            report = manager.ensure_ready()

            merged = json.loads((config_dir / "opencode.json").read_text(encoding="utf-8"))
            self.assertNotIn("env", merged["mcp"]["github"])
            self.assertEqual(manager.execution_env()["GITHUB_PERSONAL_ACCESS_TOKEN"], "ghp_real_token")
            self.assertIn("github.GITHUB_PERSONAL_ACCESS_TOKEN", report.migrated_secrets)


def _powers_fixture(root: Path) -> Path:
    powers = root / "powers"
    (powers / "skills" / "superpowers").mkdir(parents=True)
    (powers / "skills" / "superpowers.js").write_text("export default {}", encoding="utf-8")
    (powers / "skills" / "superpowers" / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    (powers / "mcp-servers" / "shokunin-memory").mkdir(parents=True)
    (powers / "mcp-servers" / "shokunin-memory" / "mcp-server.py").write_text("print('ok')\n", encoding="utf-8")
    (powers / "mcp-servers" / "shokunin-memory" / "chroma-helper.py").write_text("print('ok')\n", encoding="utf-8")
    (powers / "opencode.json").write_text(
        json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "plugin": ["superpowers@git+https://github.com/obra/superpowers.git"],
                "mcp": {
                    "shokunin-memory": {
                        "type": "local",
                        "command": ["python", "~/.shokunin/memory/mcp-server.py"],
                        "enabled": True,
                    },
                    "github": {
                        "type": "local",
                        "command": ["npx", "-y", "@modelcontextprotocol/server-github"],
                        "enabled": True,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return powers


if __name__ == "__main__":
    unittest.main()
