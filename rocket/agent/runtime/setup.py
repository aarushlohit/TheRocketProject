"""Rocket runtime setup state for OpenCode execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_OPENCODE_CONFIG_DIR = Path.home() / ".config" / "opencode"
DEFAULT_POWERS_SOURCE_DIR = Path(r"C:\Users\Aarush\shokunin-opencode-powers")
DEFAULT_WORKSPACE_PATH = Path.home() / "Documents" / "OpenCodeWorkspace"


@dataclass(frozen=True)
class RocketSetup:
    setup_complete: bool = False
    access_mode: str = "workspace"
    workspace_path: str = str(DEFAULT_WORKSPACE_PATH)
    opencode_config_dir: str = str(DEFAULT_OPENCODE_CONFIG_DIR)
    powers_source_dir: str = str(DEFAULT_POWERS_SOURCE_DIR)
    credential_mode: str = "already_configured"
    credential_refs: dict[str, str] = field(default_factory=dict)
    backup_enabled: bool = True

    @property
    def full_access(self) -> bool:
        return self.access_mode.strip().lower() == "full"

    @property
    def workspace(self) -> Path:
        return Path(self.workspace_path).expanduser()

    @property
    def opencode_dir(self) -> Path:
        return Path(self.opencode_config_dir).expanduser()

    @property
    def powers_dir(self) -> Path:
        return Path(self.powers_source_dir).expanduser()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "RocketSetup":
        if not isinstance(value, dict):
            return cls()
        defaults = cls()
        credential_refs = value.get("credential_refs")
        return cls(
            setup_complete=bool(value.get("setup_complete", defaults.setup_complete)),
            access_mode=_access_mode(str(value.get("access_mode", defaults.access_mode))),
            workspace_path=str(value.get("workspace_path", defaults.workspace_path) or defaults.workspace_path),
            opencode_config_dir=str(value.get("opencode_config_dir", defaults.opencode_config_dir) or defaults.opencode_config_dir),
            powers_source_dir=str(value.get("powers_source_dir", defaults.powers_source_dir) or defaults.powers_source_dir),
            credential_mode=_credential_mode(str(value.get("credential_mode", defaults.credential_mode))),
            credential_refs=credential_refs if isinstance(credential_refs, dict) else {},
            backup_enabled=bool(value.get("backup_enabled", defaults.backup_enabled)),
        )


def _access_mode(value: str) -> str:
    return "workspace"


def _credential_mode(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"add_now", "skip"}:
        return normalized
    return "already_configured"
