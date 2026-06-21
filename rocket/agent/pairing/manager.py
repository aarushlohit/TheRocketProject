"""Pairing payload management for RocketTerminal."""

from __future__ import annotations

import json
import secrets
import socket
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PairingPayload:
    ip: str
    port: int
    token: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


class PairingManager:
    def __init__(self, storage_dir: Path, port: int) -> None:
        self.storage_dir = storage_dir
        self.port = port
        self.payload_path = storage_dir / "pairing.json"

    def load_or_create(self) -> PairingPayload:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if self.payload_path.exists():
            data = json.loads(self.payload_path.read_text(encoding="utf-8"))
            existing = PairingPayload(
                ip=str(data["ip"]),
                port=int(data["port"]),
                token=str(data["token"]),
            )
            if existing.port == self.port:
                return existing

        payload = PairingPayload(
            ip=_local_ip(),
            port=self.port,
            token=secrets.token_urlsafe(24),
        )
        self.payload_path.write_text(payload.to_json(), encoding="utf-8")
        return payload


def _local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
        except OSError:
            return "127.0.0.1"
