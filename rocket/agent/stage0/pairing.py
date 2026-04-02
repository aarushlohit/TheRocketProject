"""QR pairing support for the Stage 0 mobile-to-PC flow."""

from __future__ import annotations

import json
import secrets
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agent.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class PairingPayload:
    """Payload embedded in the pairing QR code."""

    ip: str
    port: int
    token: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


class PairingManager:
    """Creates and persists a reusable pairing token."""

    def __init__(self, storage_dir: Path, port: int):
        self.storage_dir = storage_dir
        self.port = port
        self.pairing_file = self.storage_dir / "pairing.json"
        self.qr_image_file = self.storage_dir / "pairing_qr.png"

    def load_or_create(self) -> PairingPayload:
        """Load a saved pairing token or create a new one."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        existing = self._load_existing()
        token = existing.get("token") if existing else None

        payload = PairingPayload(
            ip=get_local_ip(),
            port=self.port,
            token=token or secrets.token_urlsafe(24),
        )

        self.pairing_file.write_text(
            json.dumps(asdict(payload), indent=2),
            encoding="utf-8",
        )
        return payload

    def print_qr(self, payload: PairingPayload) -> None:
        """Render the QR pairing code as ASCII and save a PNG copy."""
        import qrcode

        qr = qrcode.QRCode(border=1)
        qr.add_data(payload.to_json())
        qr.make(fit=True)

        logger.info("Nova pairing QR:")
        qr.print_ascii(invert=True)

        image = qr.make_image(fill_color="black", back_color="white")
        image.save(self.qr_image_file)
        logger.info(f"Pairing QR saved to {self.qr_image_file}")

    def _load_existing(self) -> dict[str, Any] | None:
        if not self.pairing_file.exists():
            return None

        try:
            data = json.loads(self.pairing_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Existing pairing.json is invalid, generating a new token")
            return None

        if not isinstance(data, dict):
            return None

        return data


def get_local_ip() -> str:
    """Resolve the LAN IP used by the desktop for mobile pairing."""
    probe_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        probe_socket.connect(("8.8.8.8", 80))
        ip = probe_socket.getsockname()[0]
        if ip:
            return ip
    except OSError:
        logger.warning("Could not infer LAN IP via UDP probe, falling back to hostname")
    finally:
        probe_socket.close()

    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"
