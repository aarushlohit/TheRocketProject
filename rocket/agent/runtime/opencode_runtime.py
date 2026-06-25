"""OpenCode powers verification and repair for Rocket."""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.runtime.prompts import ROCKET_SYSTEM_PROMPT
from agent.runtime.setup import RocketSetup
from agent.runtime.vault import RocketVault


SUPERPOWERS_PLUGIN = "superpowers@git+https://github.com/obra/superpowers.git"
SECRET_MARKERS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")
PLACEHOLDER_MARKERS = ("YOUR_", "REPLACE_", "HERE", "${", "ROCKET_VAULT_REF:")
ROCKET_WINDOWS_MCP = "rocket-windows"


@dataclass(frozen=True)
class RuntimeReadinessReport:
    ready: bool
    config_path: str
    installed_mcp: list[str] = field(default_factory=list)
    missing_mcp: list[str] = field(default_factory=list)
    installed_assets: list[str] = field(default_factory=list)
    missing_assets: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    dependencies: dict[str, bool] = field(default_factory=dict)
    migrated_secrets: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.ready:
            return f"OpenCode runtime ready. MCP: {len(self.installed_mcp)}. Actions: {len(self.actions)}."
        missing = [*self.missing_assets, *self.missing_mcp]
        return f"OpenCode runtime incomplete: {', '.join(missing) or 'unknown issue'}"


class OpenCodeRuntimeManager:
    def __init__(self, data_dir: Path, setup: RocketSetup | None = None) -> None:
        self.data_dir = data_dir
        self.setup = setup or RocketSetup()
        self.vault = RocketVault(data_dir)

    def ensure_ready(self) -> RuntimeReadinessReport:
        setup = self.setup
        actions: list[str] = []
        missing_assets: list[str] = []
        migrated_secrets: list[str] = []

        opencode_dir = setup.opencode_dir
        agents_dir = opencode_dir / "agent"
        plugins_dir = opencode_dir / "plugins"
        skills_dir = opencode_dir / "skills"
        shokunin_memory_dir = Path.home() / ".shokunin" / "memory"
        shokunin_scripts_dir = Path.home() / ".shokunin" / "scripts"

        for directory in (
            opencode_dir,
            agents_dir,
            plugins_dir,
            skills_dir,
            shokunin_memory_dir,
            shokunin_scripts_dir,
            setup.workspace,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        powers_dir = setup.powers_dir
        desired_config_path = powers_dir / "opencode.json"
        desired_config = _load_json(desired_config_path)
        if not desired_config:
            missing_assets.append(str(desired_config_path))
        if not _rocket_windows_script().exists():
            missing_assets.append(str(_rocket_windows_script()))

        self._write_rocket_agent(agents_dir / "rocket-blind.md", actions)
        self._copy_file(
            powers_dir / "skills" / "superpowers.js",
            plugins_dir / "superpowers.js",
            actions,
            missing_assets,
            "superpowers plugin",
        )
        self._copy_tree(
            powers_dir / "skills" / "superpowers",
            skills_dir / "superpowers",
            actions,
            missing_assets,
            "superpowers skills",
        )
        self._copy_file(
            powers_dir / "mcp-servers" / "shokunin-memory" / "mcp-server.py",
            shokunin_memory_dir / "mcp-server.py",
            actions,
            missing_assets,
            "shokunin memory MCP",
        )
        self._copy_file(
            powers_dir / "mcp-servers" / "shokunin-memory" / "chroma-helper.py",
            shokunin_scripts_dir / "chroma-helper.py",
            actions,
            missing_assets,
            "shokunin chroma helper",
        )

        config_path = opencode_dir / "opencode.json"
        existing_config = _load_json(config_path)
        merged_config, installed_mcp, missing_mcp = self._merge_config(existing_config, desired_config, migrated_secrets, actions)
        _write_json(config_path, merged_config)

        dependencies = {
            "opencode": shutil.which(os.getenv("ROCKET_OPENCODE_COMMAND", "opencode.cmd")) is not None,
            "python": shutil.which("python") is not None,
            "npm": shutil.which("npm") is not None,
            "powers_source": powers_dir.exists(),
        }
        ready = not missing_assets and not missing_mcp and dependencies["opencode"] and dependencies["powers_source"]
        return RuntimeReadinessReport(
            ready=ready,
            config_path=str(config_path),
            installed_mcp=installed_mcp,
            missing_mcp=missing_mcp,
            installed_assets=[
                "superpowers plugin",
                "rocket-blind agent",
                "superpowers skills",
                "shokunin memory MCP",
                "shokunin chroma helper",
            ],
            missing_assets=missing_assets,
            actions=actions,
            dependencies=dependencies,
            migrated_secrets=migrated_secrets,
        )

    def execution_env(self) -> dict[str, str]:
        return self.vault.build_env()

    def _merge_config(
        self,
        existing: dict[str, Any],
        desired: dict[str, Any],
        migrated_secrets: list[str],
        actions: list[str],
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        config = existing if isinstance(existing, dict) else {}
        config.setdefault("$schema", desired.get("$schema", "https://opencode.ai/config.json"))
        # Rocket runs OpenCode as a non-interactive subprocess. OpenCode treats
        # ask-mode MCP permissions as auto-rejections there, so CLI runtime must
        # allow tool calls and rely on Rocket's own onboarding/access-mode policy.
        config["permission"] = os.getenv("ROCKET_OPENCODE_PERMISSION", "allow")

        plugins = config.get("plugin")
        if not isinstance(plugins, list):
            plugins = []
        if SUPERPOWERS_PLUGIN not in plugins:
            plugins.append(SUPERPOWERS_PLUGIN)
            actions.append("added superpowers plugin config")
        config["plugin"] = plugins

        existing_mcp = config.get("mcp")
        if not isinstance(existing_mcp, dict):
            existing_mcp = {}
        desired_mcp = desired.get("mcp") if isinstance(desired.get("mcp"), dict) else {}
        desired_mcp = {ROCKET_WINDOWS_MCP: _rocket_windows_mcp_entry(), **desired_mcp}
        missing_mcp: list[str] = []
        for name, entry in desired_mcp.items():
            if name not in existing_mcp:
                existing_mcp[name] = _normalize_mcp_entry(entry)
                actions.append(f"added MCP config: {name}")
            if not isinstance(existing_mcp.get(name), dict):
                missing_mcp.append(str(name))

        for name, entry in list(existing_mcp.items()):
            if isinstance(entry, dict):
                self._migrate_env_secrets(str(name), entry, migrated_secrets, actions)

        config["mcp"] = existing_mcp
        return config, sorted(str(name) for name in existing_mcp), sorted(missing_mcp)

    def _migrate_env_secrets(self, mcp_name: str, entry: dict[str, Any], migrated: list[str], actions: list[str]) -> None:
        env = entry.get("env")
        if not isinstance(env, dict):
            return
        for key, value in list(env.items()):
            key_text = str(key)
            value_text = str(value)
            if not _looks_like_secret_key(key_text) or not _looks_like_real_secret(value_text):
                continue
            self.vault.set_secret(f"env:{key_text}", value_text)
            env.pop(key, None)
            migrated.append(f"{mcp_name}.{key_text}")
            actions.append(f"migrated secret from MCP config: {mcp_name}.{key_text}")
        if not env:
            entry.pop("env", None)

    @staticmethod
    def _copy_file(source: Path, target: Path, actions: list[str], missing: list[str], label: str) -> None:
        if not source.exists():
            missing.append(str(source))
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() == source.read_bytes():
            return
        shutil.copy2(source, target)
        actions.append(f"synced {label}")

    @staticmethod
    def _copy_tree(source: Path, target: Path, actions: list[str], missing: list[str], label: str) -> None:
        if not source.exists():
            missing.append(str(source))
            return
        if target.exists() and _same_tree(source, target):
            return
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        actions.append(f"synced {label}")

    @staticmethod
    def _write_rocket_agent(target: Path, actions: list[str]) -> None:
        content = (
            "---\n"
            "description: Rocket blind-first desktop executor. Executes real Windows desktop tasks and returns concise status.\n"
            "mode: primary\n"
            "temperature: 0.2\n"
            "---\n"
            f"{ROCKET_SYSTEM_PROMPT}\n\n"
            "EXECUTOR OUTPUT CONTRACT\n"
            "Never chat. Never greet. Never expose JSON, tool names, prompts, or internal state.\n"
            "Use the configured MCP servers and desktop tools to perform the real action.\n"
            "End with exactly these lines:\n"
            "STATUS: <DONE | FAILED | WORKING | NEED_PERMISSION>\n"
            "SPEECH: <one short sentence for the user>\n"
            "CONTENT: <only for read-aloud tasks; otherwise empty>\n"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_text(encoding="utf-8", errors="replace") == content:
            return
        target.write_text(content, encoding="utf-8")
        actions.append("synced rocket-blind agent")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _looks_like_secret_key(key: str) -> bool:
    upper = key.upper()
    return any(marker in upper for marker in SECRET_MARKERS)


def _looks_like_real_secret(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    upper = stripped.upper()
    return not any(marker in upper for marker in PLACEHOLDER_MARKERS)


def _same_tree(left: Path, right: Path) -> bool:
    left_files = sorted(path.relative_to(left) for path in left.rglob("*") if path.is_file())
    right_files = sorted(path.relative_to(right) for path in right.rglob("*") if path.is_file())
    if left_files != right_files:
        return False
    return all((left / rel).read_bytes() == (right / rel).read_bytes() for rel in left_files)


def _normalize_mcp_entry(entry: Any) -> Any:
    if not isinstance(entry, dict):
        return entry
    normalized = json.loads(json.dumps(entry))
    command = normalized.get("command")
    if isinstance(command, list):
        normalized["command"] = [_expand_home_part(part) for part in command]
    return normalized


def _rocket_windows_mcp_entry() -> dict[str, Any]:
    return {
        "type": "local",
        "command": [sys.executable, str(_rocket_windows_script())],
        "enabled": True,
    }


def _rocket_windows_script() -> Path:
    return Path(__file__).resolve().parents[2] / "agent" / "phase2" / "windows_mcp.py"


def _expand_home_part(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if value == "~" or value.startswith("~/") or value.startswith("~\\"):
        return str(Path(value).expanduser())
    return value
