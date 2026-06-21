"""Small Phase 1 configuration loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Config:
    host: str = "0.0.0.0"
    port: int = 8765
    log_level: str = "INFO"
    data_dir: Path = Path("data/rocket")


def load_config(config_path: Path | None = None) -> Config:
    config = Config()
    path = config_path or Path.home() / ".rocket" / "config.yaml"
    if not path.exists():
        return config

    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    server = data.get("server", {})
    storage = data.get("storage", {})
    if isinstance(server, dict):
        config.host = str(server.get("host", config.host))
        config.port = int(server.get("port", config.port))
        config.log_level = str(server.get("log_level", config.log_level))
    if isinstance(storage, dict) and storage.get("data_dir"):
        config.data_dir = Path(str(storage["data_dir"]))
    return config
