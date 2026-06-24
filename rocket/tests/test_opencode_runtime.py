from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.runtime.opencode_runtime import OpenCodeRuntimeManager
from agent.runtime.setup import RocketSetup
from agent.runtime.opencode_cli_client import (
    DEFAULT_OPENCODE_MODELS,
    OpenCodeCliClient,
    _extract_message,
    _extract_session_id,
    _tail,
    _configured_timeout,
    _desktop_expectation,
    _short_run_message,
)
from agent.runtime.memory import RocketProfile


class OpenCodeRuntimeTests(unittest.TestCase):
    def test_opencode_default_models_use_free_priority_list(self) -> None:
        env = os.environ.copy()
        env.pop("ROCKET_OPENCODE_MODEL", None)
        env.pop("ROCKET_OPENCODE_MODELS", None)
        with patch.dict("os.environ", env, clear=True):
            client = OpenCodeCliClient(Path.cwd(), profile=object())  # type: ignore[arg-type]

        self.assertEqual(client.models, list(DEFAULT_OPENCODE_MODELS))
        self.assertEqual(client.model, "opencode/deepseek-v4-flash-free")

    def test_opencode_timeout_is_disabled_by_default(self) -> None:
        env = os.environ.copy()
        env.pop("ROCKET_OPENCODE_TIMEOUT_SECONDS", None)
        with patch.dict("os.environ", env, clear=True):
            self.assertIsNone(_configured_timeout())

    def test_prompt_prefers_playwright_for_browser_tasks(self) -> None:
        client = OpenCodeCliClient(Path.cwd(), profile=RocketProfile())
        prompt = client._build_prompt("Open YouTube and search for cats.")

        self.assertIn("prefer Playwright MCP", prompt)
        self.assertIn("Do not spend time explaining", prompt)
        self.assertIn("maximize", prompt)

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
        self.assertIsNone(_desktop_expectation("Create a file in workspace"))

    def test_opencode_run_message_stays_short(self) -> None:
        message = _short_run_message("Open YouTube and search for cat videos. " * 50)

        self.assertLess(len(message), 260)
        self.assertIn("attached prompt file", message)

    def test_subprocess_stream_parsers_tolerate_none(self) -> None:
        self.assertEqual(_extract_message(None), "")
        self.assertEqual(_extract_session_id(None), "")
        self.assertEqual(_tail(None), "")

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
