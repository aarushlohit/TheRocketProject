"""Durable local memory for Rocket runtime state."""

from __future__ import annotations

import json
import sqlite3
from difflib import get_close_matches
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from agent.runtime.security import protect_text, unprotect_text


@dataclass(frozen=True)
class RocketProfile:
    name: str = ""
    preferred_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    country: str = ""
    browser: str = "default"
    editor: str = "code"
    speech_speed: str = "normal"
    trust_level: str = "trusted"
    access_mode: str = "workspace"
    workspace_path: str = ""
    opencode_config_dir: str = ""
    powers_source_dir: str = ""
    credential_mode: str = "already_configured"
    credential_refs: dict[str, str] = field(default_factory=dict)
    backup_enabled: bool = True
    password_pattern_ref: str = ""


class RocketMemory:
    """SQLite fallback memory used when external memory is unavailable."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.path = data_dir / "RocketProfile.db"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def load_profile(self) -> RocketProfile:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute("select value from kv where key = 'profile'").fetchone()
        if not row:
            return RocketProfile()
        try:
            data = json.loads(unprotect_text(row[0]))
            return RocketProfile(**{key: data.get(key, value) for key, value in asdict(RocketProfile()).items()})
        except Exception:
            return RocketProfile()

    def save_profile(self, profile: RocketProfile) -> None:
        self.set("profile", asdict(profile))

    def load_contact_aliases(self) -> dict[str, str]:
        raw = self.get("contact_aliases", {})
        if not isinstance(raw, dict):
            return {}
        aliases: dict[str, str] = {}
        for key, value in raw.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            normalized_key = _normalize_alias(key)
            normalized_value = value.strip()
            if normalized_key and normalized_value:
                aliases[normalized_key] = normalized_value
        return aliases

    def save_contact_alias(self, spoken_name: str, resolved_name: str) -> None:
        spoken = _normalize_alias(spoken_name)
        resolved = resolved_name.strip()
        if not spoken or not resolved:
            return
        aliases = self.load_contact_aliases()
        aliases[spoken] = resolved
        self.set("contact_aliases", aliases)

    def resolve_contact_alias(self, spoken_name: str) -> str:
        aliases = self.load_contact_aliases()
        if not aliases:
            return spoken_name.strip()
        spoken = _normalize_alias(spoken_name)
        if not spoken:
            return spoken_name.strip()
        if spoken in aliases:
            return aliases[spoken]
        matches = get_close_matches(spoken, aliases.keys(), n=1, cutoff=0.84)
        if matches:
            return aliases[matches[0]]
        return spoken_name.strip()

    def set(self, key: str, value: Any) -> None:
        encoded = protect_text(json.dumps(value, ensure_ascii=True))
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "insert into kv(key, value) values(?, ?) on conflict(key) do update set value = excluded.value",
                (key, encoded),
            )
            connection.commit()

    def get(self, key: str, default: Any = None) -> Any:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute("select value from kv where key = ?", (key,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(unprotect_text(row[0]))
        except Exception:
            return default

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute("create table if not exists kv (key text primary key, value text not null)")
            connection.commit()


def _normalize_alias(value: str) -> str:
    return " ".join(value.strip().lower().split())
