"""WebSocket server handler."""

import asyncio
import json
import uuid
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol

from agent.core.agent import Agent
from agent.utils.logger import get_logger


logger = get_logger(__name__)


async def handle_connection(websocket: WebSocketServerProtocol, path: str):
    """Handle WebSocket connection from mobile app.
    
    Args:
        websocket: WebSocket connection
        path: Connection path
    """
    client_id = str(uuid.uuid4())[:8]
    logger.info(f"Client connected: {client_id}")

    try:
        async for message in websocket:
            try:
                await handle_message(websocket, message, client_id)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from {client_id}")
                await websocket.send(
                    json.dumps(
                        {
                            "id": "unknown",
                            "type": "error",
                            "payload": {
                                "error_code": "INVALID_JSON",
                                "message": "Invalid JSON message",
                            },
                        }
                    )
                )
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await websocket.send(
                    json.dumps(
                        {
                            "id": "unknown",
                            "type": "error",
                            "payload": {
                                "error_code": "INTERNAL_ERROR",
                                "message": str(e),
                            },
                        }
                    )
                )

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Connection error: {e}")


async def handle_message(
    websocket: WebSocketServerProtocol, message: str, client_id: str
):
    """Handle incoming WebSocket message.
    
    Args:
        websocket: WebSocket connection
        message: Incoming message JSON
        client_id: Client identifier
    """
    msg_data = json.loads(message)
    msg_type = msg_data.get("type")
    msg_id = msg_data.get("id", "unknown")
    payload = msg_data.get("payload", {})

    logger.debug(f"Message from {client_id}: type={msg_type}, id={msg_id}")

    # Route by message type
    if msg_type == "voice_input":
        await handle_voice_input(websocket, msg_id, payload)
    elif msg_type == "drawing_input":
        await handle_drawing_input(websocket, msg_id, payload)
    elif msg_type == "heartbeat":
        await handle_heartbeat(websocket, msg_id)
    else:
        logger.warning(f"Unknown message type: {msg_type}")
        await websocket.send(
            json.dumps(
                {
                    "id": msg_id,
                    "type": "error",
                    "payload": {
                        "error_code": "UNKNOWN_MESSAGE_TYPE",
                        "message": f"Unknown message type: {msg_type}",
                    },
                }
            )
        )


async def handle_voice_input(
    websocket: WebSocketServerProtocol, msg_id: str, payload: dict
):
    """Handle voice input message.
    
    Args:
        websocket: WebSocket connection
        msg_id: Message ID for tracking
        payload: Message payload
    """
    text = payload.get("text", "")
    confidence = payload.get("confidence", 1.0)

    logger.info(f"Voice input: '{text}' (confidence: {confidence})")

    # In real implementation, this would get the agent instance
    # For now, placeholder response
    result_payload = {
        "status": "executing",
        "message": f"Processing: {text}",
        "action_id": str(uuid.uuid4()),
    }

    await websocket.send(
        json.dumps({"id": msg_id, "type": "response", "payload": result_payload})
    )


async def handle_drawing_input(
    websocket: WebSocketServerProtocol, msg_id: str, payload: dict
):
    """Handle drawing input message.
    
    Args:
        websocket: WebSocket connection
        msg_id: Message ID
        payload: Message payload
    """
    strokes = payload.get("strokes", [])
    logger.info(f"Drawing input: {len(strokes)} strokes")

    result_payload = {
        "status": "executing",
        "recognized_action": "gesture_processing",
        "action_id": str(uuid.uuid4()),
    }

    await websocket.send(
        json.dumps({"id": msg_id, "type": "response", "payload": result_payload})
    )


async def handle_heartbeat(websocket: WebSocketServerProtocol, msg_id: str):
    """Handle heartbeat message.
    
    Args:
        websocket: WebSocket connection
        msg_id: Message ID
    """
    logger.debug(f"Heartbeat received: {msg_id}")
    await websocket.send(
        json.dumps(
            {
                "id": msg_id,
                "type": "heartbeat",
                "payload": {"sender": "agent", "status": "alive"},
            }
        )
    )


async def start_websocket_server(
    agent: Agent, host: str = "localhost", port: int = 8765
):
    """Start WebSocket server.
    
    Args:
        agent: Agent instance
        host: Server host
        port: Server port
    """
    logger.info(f"Starting WebSocket server on {host}:{port}")

    async with websockets.serve(handle_connection, host, port):
        logger.info(f"WebSocket server listening on ws://{host}:{port}")
        await asyncio.Event().wait()
