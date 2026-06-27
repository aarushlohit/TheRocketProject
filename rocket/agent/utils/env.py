"""Helpers for loading local environment files safely."""

from __future__ import annotations

import os
from pathlib import Path


ENV_FILES = (".env", ".ENV")
PERSISTED_ENV_LOCATIONS = (
    Path.home() / ".rocket" / "backend.env",
    Path(os.getenv("LOCALAPPDATA", "")) / "RocketBackend" / "backend.env",
)


def load_local_env(base_dir: Path | None = None) -> None:
    """Load local env files into process environment without overriding existing values."""
    roots: list[Path] = []
    if base_dir is not None:
        roots.append(base_dir)
    roots.append(Path.cwd())
    roots.extend(parent for parent in Path.cwd().parents)
    roots.extend(
        location.parent
        for location in PERSISTED_ENV_LOCATIONS
        if str(location.parent) not in {"", "."}
    )

    seen: set[Path] = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        for name in ENV_FILES:
            _load_env_file(root / name)

    for env_path in PERSISTED_ENV_LOCATIONS:
        _load_env_file(env_path)


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or "=" not in cleaned:
            continue

        key, value = cleaned.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key:
            os.environ.setdefault(key, value)
