"""Small HTTP dashboard server for packaged Rocket Backend builds."""

from __future__ import annotations

import asyncio
import json
import mimetypes
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from agent.pairing.manager import PairingPayload


@dataclass(frozen=True)
class DashboardState:
    web_root: Path
    pairing: PairingPayload
    websocket_port: int
    host: str = "127.0.0.1"
    port: int = 8790


async def serve_dashboard(state: DashboardState) -> None:
    """Serve Flutter web dashboard files and basic JSON status endpoints."""

    server = ThreadingHTTPServer((state.host, state.port), _handler_for(state))
    try:
        await asyncio.to_thread(server.serve_forever)
    finally:
        server.shutdown()
        server.server_close()


def _handler_for(state: DashboardState) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            body, status, headers = _route(self.path, state)
            self.send_response(status)
            for key, value in headers:
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
            return

    return DashboardHandler


def _route(path: str, state: DashboardState) -> tuple[bytes, int, list[tuple[str, str]]]:
    route = path.split("?", 1)[0]
    if route == "/api/status":
        return _json(
            {
                "running": True,
                "message": "Rocket Backend is running.",
                "websocket": f"ws://{state.pairing.ip}:{state.websocket_port}",
                "pairing": state.pairing.to_json(),
            }
        )
    if route == "/api/pairing":
        return _json(json.loads(state.pairing.to_json()))
    return _static(route, state.web_root)


def _json(payload: dict[str, Any]) -> tuple[bytes, int, list[tuple[str, str]]]:
    return (
        json.dumps(payload, ensure_ascii=True).encode("utf-8"),
        200,
        [("Content-Type", "application/json; charset=utf-8"), ("Access-Control-Allow-Origin", "*")],
    )


def _static(path: str, web_root: Path) -> tuple[bytes, int, list[tuple[str, str]]]:
    safe_path = "index.html" if path in {"", "/"} else path.lstrip("/")
    target = (web_root / safe_path).resolve()
    root = web_root.resolve()
    if root not in target.parents and target != root:
        return b"Not found", 404, [("Content-Type", "text/plain; charset=utf-8")]
    if not target.exists() or target.is_dir():
        target = web_root / "index.html"
    if not target.exists():
        return b"Dashboard assets missing", 404, [("Content-Type", "text/plain; charset=utf-8")]
    content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    return target.read_bytes(), 200, [("Content-Type", content_type)]
