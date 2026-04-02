"""Helpers for loading local environment files safely."""

from __future__ import annotations

import os
from pathlib import Path


ENV_FILES = (".env", ".ENV")


def load_local_env(base_dir: Path | None = None) -> None:
    """Load local env files into process environment without overriding existing values."""
    root = base_dir or Path.cwd()

    for name in ENV_FILES:
        env_path = root / name
        if not env_path.exists():
            continue

        for line in env_path.read_text(encoding="utf-8").splitlines():
            cleaned = line.strip()
            if not cleaned or cleaned.startswith("#") or "=" not in cleaned:
                continue

            key, value = cleaned.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key:
                os.environ.setdefault(key, value)
