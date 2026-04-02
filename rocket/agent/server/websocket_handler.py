"""Authenticated WebSocket server for Stage 0 drawing uploads."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any
from urllib.parse import parse_qs, urlparse

import websockets

from agent.core.nova_stage0 import NovaStageZeroAgent
from agent.utils.logger import get_logger


logger = get_logger(__name__)


async def handle_connection(
    websocket: Any,
    *,
    agent: NovaStageZeroAgent,
    token: str,
):
    """Handle a mobile connection after validating its pairing token."""
    client_id = str(uuid.uuid4())[:8]
    path = _extract_request_path(websocket)
    if not _is_authenticated(path, token):
        logger.warning(f"Rejected unauthenticated client: {client_id}")
        await websocket.send(
            json.dumps(
                {
                    "status": "error",
                    "intent": None,
                    "message": "Invalid pairing token",
                }
            )
        )
        await websocket.close(code=4401, reason="Invalid token")
        return

    logger.info(f"Client connected: {client_id}")
    await websocket.send(
        json.dumps(
            {
                "status": "connected",
                "intent": None,
                "message": "Nova backend connected",
            }
        )
    )

    try:
        async for message in websocket:
            try:
                await handle_message(
                    websocket=websocket,
                    message=message,
                    client_id=client_id,
                    agent=agent,
                )
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await websocket.send(
                    json.dumps(
                        {
                            "status": "error",
                            "intent": None,
                            "message": str(e),
                        }
                    )
                )

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Connection error: {e}")


async def handle_message(
    websocket: Any,
    message: str | bytes,
    client_id: str,
    agent: NovaStageZeroAgent,
):
    """Handle either a binary drawing upload or a small JSON control message."""
    if isinstance(message, bytes):
        logger.info(f"Drawing upload received from {client_id}: {len(message)} bytes")
        response = await agent.handle_drawing_image(message)
        await websocket.send(json.dumps(response))
        return

    logger.debug(f"Text message from {client_id}: {message}")
    msg_data = json.loads(message)
    if msg_data.get("type") == "ping":
        await websocket.send(
            json.dumps(
                {
                    "status": "alive",
                    "intent": None,
                    "message": "pong",
                }
            )
        )
        return

    raise ValueError("Expected binary drawing data or a ping message")


async def start_websocket_server(
    agent: NovaStageZeroAgent,
    token: str,
    host: str = "0.0.0.0",
    port: int = 8765,
):
    """Start the Stage 0 WebSocket server."""
    logger.info(f"Starting WebSocket server on {host}:{port}")

    async with websockets.serve(
        lambda websocket: handle_connection(
            websocket,
            agent=agent,
            token=token,
        ),
        host,
        port,
        max_size=5 * 1024 * 1024,
    ):
        logger.info(f"WebSocket server listening on ws://{host}:{port}")
        await asyncio.get_running_loop().create_future()


def _is_authenticated(path: str, expected_token: str) -> bool:
    parsed = urlparse(path)
    query = parse_qs(parsed.query)
    received_token = query.get("token", [None])[0]
    return received_token == expected_token


def _extract_request_path(websocket: Any) -> str:
    path = getattr(websocket, "path", None)
    if isinstance(path, str):
        return path

    request = getattr(websocket, "request", None)
    request_path = getattr(request, "path", None)
    if isinstance(request_path, str):
        return request_path

    return ""
