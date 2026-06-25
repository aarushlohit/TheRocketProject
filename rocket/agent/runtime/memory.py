"""Durable local memory for Rocket runtime state."""

from __future__ import annotations

import json
import sqlite3
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
