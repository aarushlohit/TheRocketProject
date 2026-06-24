"""Encrypted local secret vault for Rocket runtime credentials."""

from __future__ import annotations

import json
from pathlib import Path

from agent.runtime.security import protect_text, unprotect_text


class RocketVault:
    """Small DPAPI-backed JSON vault.

    Values are protected per field so the file can be updated without
    decrypting unrelated secrets into memory.
    """

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "RocketVault.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def set_secret(self, key: str, value: str) -> None:
        if not key.strip() or not value:
            return
        data = self._read_raw()
        data[key] = protect_text(value)
        self._write_raw(data)

    def get_secret(self, key: str) -> str | None:
        raw = self._read_raw().get(key)
        if not isinstance(raw, str):
            return None
        try:
            return unprotect_text(raw)
        except Exception:
            return None

    def build_env(self) -> dict[str, str]:
        env: dict[str, str] = {}
        for key in self._read_raw():
            if key.startswith("env:"):
                value = self.get_secret(key)
                if value:
                    env[key.removeprefix("env:")] = value
        return env

    def _read_raw(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}

    def _write_raw(self, data: dict[str, str]) -> None:
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
