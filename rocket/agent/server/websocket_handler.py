"""Phase 1 websocket intake for Rocket mobile clients."""

from __future__ import annotations

import base64
import json
import socket
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

import websockets

from agent.adapters.nemotron import NemotronAdapter
from agent.terminal.rocket_terminal import RocketTerminal


@dataclass(frozen=True)
class RocketWebSocketServer:
    """Authenticated websocket server for mobile input capture."""

    adapter: NemotronAdapter
    terminal: RocketTerminal
    token: str
    host: str = "0.0.0.0"
    port: int = 8765

    async def serve_forever(self) -> None:
        self.terminal.log(f"Websocket listening on ws://{self.host}:{self.port}")
        async with websockets.serve(
            lambda websocket: self._handle_connection(websocket),
            self.host,
            self.port,
            max_size=12 * 1024 * 1024,
        ):
            await self.adapter.health_check()
            self.terminal.show_health(self.adapter.status)
            await self._wait_forever()

    async def _handle_connection(self, websocket: Any) -> None:
        client_id = str(uuid.uuid4())[:8]
        path = _extract_request_path(websocket)
        if not _is_authenticated(path, self.token):
            await websocket.send(json.dumps({"type": "error", "message": "Invalid pairing token"}))
            await websocket.close(code=4401, reason="Invalid token")
            return

        self.terminal.connection_open(client_id)
        await _send(websocket, {"type": "connected", "message": "Connection established"})

        try:
            async for raw_message in websocket:
                await self._handle_message(websocket, client_id, raw_message)
        except websockets.exceptions.ConnectionClosed:
            self.terminal.connection_closed(client_id)

    async def _handle_message(self, websocket: Any, client_id: str, raw_message: str | bytes) -> None:
        started = time.perf_counter()
        try:
            if isinstance(raw_message, bytes):
                task = await self.adapter.process_image(raw_message)
                await self._send_task(websocket, client_id, "drawing", task, started)
                return

            message = json.loads(raw_message)
            message_type = str(message.get("type", "")).strip().lower()

            if message_type == "ping":
                await _send(websocket, {"type": "pong", "status": "alive"})
                return
            if message_type == "audio":
                audio_bytes = _decode_base64(message.get("data"))
                task = await self.adapter.process_audio(audio_bytes)
                await self._send_task(websocket, client_id, "voice", task, started)
                return
            if message_type == "braille":
                cells = str(message.get("text", "")).strip()
                task = await self.adapter.process_braille(cells)
                await self._send_task(websocket, client_id, "braille", task, started)
                return
            if message_type == "drawing":
                image_bytes = _decode_base64(message.get("data"))
                task = await self.adapter.process_image(image_bytes)
                await self._send_task(websocket, client_id, "drawing", task, started)
                return

            await _send(websocket, {"type": "error", "message": f"Unsupported message type: {message_type}"})
        except Exception as error:
            self.terminal.error(f"{client_id}: {error}")
            await _send(websocket, {"type": "error", "message": str(error)})

    async def _send_task(
        self,
        websocket: Any,
        client_id: str,
        source: str,
        task: str,
        started: float,
    ) -> None:
        latency_ms = int((time.perf_counter() - started) * 1000)
        self.terminal.received_task(client_id=client_id, source=source, task=task, latency_ms=latency_ms)
        await _send(
            websocket,
            {
                "type": "task",
                "source": source,
                "task": task,
                "latency_ms": latency_ms,
                "message": "Task generated",
            },
        )

    @staticmethod
    async def _wait_forever() -> None:
        import asyncio

        await asyncio.get_running_loop().create_future()


def pick_available_port(host: str, starting_port: int, max_tries: int = 50) -> int:
    """Return the first available TCP port at or above starting_port."""

    for offset in range(max_tries):
        port = starting_port + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
            except OSError:
                continue
            return port
    raise OSError(f"No free port found starting at {starting_port}")


async def _send(websocket: Any, payload: dict[str, Any]) -> None:
    await websocket.send(json.dumps(payload))


def _decode_base64(value: Any) -> bytes:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected base64 data.")
    return base64.b64decode(value)


def _is_authenticated(path: str, expected_token: str) -> bool:
    parsed = urlparse(path)
    query = parse_qs(parsed.query)
    return query.get("token", [None])[0] == expected_token


def _extract_request_path(websocket: Any) -> str:
    path = getattr(websocket, "path", None)
    if isinstance(path, str):
        return path
    request = getattr(websocket, "request", None)
    request_path = getattr(request, "path", None)
    return request_path if isinstance(request_path, str) else ""
