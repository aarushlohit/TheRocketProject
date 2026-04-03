"""Authenticated WebSocket server for Stage 0 — Production-Grade Handler.

PATCHED VERSION:
- Routes ALL message types (drawing, onboarding, confirmation, ping)
- Uses FeedbackManager for all notifications
- Strict WebSocket contract
- NO CLI interaction
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Callable, Optional
from urllib.parse import parse_qs, urlparse

import websockets

from agent.core.nova_stage0 import NovaStageZeroAgent
from agent.core.user_profile import process_onboarding_request, UserProfile
from agent.core.feedback_manager import get_feedback_manager, init_feedback_manager, EventType
from agent.core.confirmation_system import get_confirmation_manager
from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# CLIENT STATE
# =============================================================================

class ClientState:
    """Per-client state tracking."""
    
    def __init__(self, client_id: str, websocket: Any):
        self.client_id = client_id
        self.websocket = websocket
        self.profile: Optional[UserProfile] = None
        self.onboarded = False
    
    async def send(self, message: dict):
        """Send JSON message to client."""
        try:
            print(f"[WS SEND → {self.client_id}] {message.get('type', 'unknown')}")
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send to {self.client_id}: {e}")


# =============================================================================
# MESSAGE HANDLER
# =============================================================================

async def handle_connection(
    websocket: Any,
    *,
    agent: NovaStageZeroAgent,
    token: str,
):
    """Handle a mobile connection with full message routing."""
    client_id = str(uuid.uuid4())[:8]
    path = _extract_request_path(websocket)
    
    # Authentication check
    if not _is_authenticated(path, token):
        logger.warning(f"[{client_id}] Rejected - invalid token")
        await websocket.send(json.dumps({
            "type": "error",
            "message": "Invalid pairing token",
        }))
        await websocket.close(code=4401, reason="Invalid token")
        return
    
    # Create client state
    state = ClientState(client_id, websocket)
    
    # Create WebSocket callback for this client
    async def ws_callback(message: dict):
        await state.send(message)
    
    # Initialize managers with WebSocket callback
    feedback_mgr = init_feedback_manager(
        profile=state.profile,
        websocket_callback=ws_callback,
    )
    
    # Set callback on agent's pipeline (UNIFIED)
    if hasattr(agent, 'pipeline_engine'):
        agent.pipeline_engine.set_websocket_callback(ws_callback)
    
    # DEPRECATED: Legacy engine support (backward compatibility)
    if hasattr(agent, 'engine'):
        agent.engine.set_websocket_callback(ws_callback)
    
    logger.info(f"[{client_id}] Connected")
    print(f"[WS RECEIVE] Client {client_id} connected")
    
    # Send connection confirmation
    await state.send({
        "type": "connected",
        "message": "Rocket backend connected",
        "requires_onboarding": not state.onboarded,
    })
    
    # Notify system ready
    await feedback_mgr.system_ready()
    
    try:
        async for message in websocket:
            try:
                print(f"[WS RECEIVE ← {client_id}] {type(message).__name__} ({len(message) if isinstance(message, (bytes, str)) else 0} bytes)")
                
                await handle_message(
                    state=state,
                    message=message,
                    agent=agent,
                    ws_callback=ws_callback,
                )
            except json.JSONDecodeError as e:
                logger.error(f"[{client_id}] Invalid JSON: {e}")
                await state.send({
                    "type": "error",
                    "message": f"Invalid JSON: {e}",
                })
            except Exception as e:
                logger.error(f"[{client_id}] Error handling message: {e}")
                await state.send({
                    "type": "error",
                    "message": str(e),
                })
    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"[{client_id}] Disconnected")
    except Exception as e:
        logger.error(f"[{client_id}] Connection error: {e}")


async def handle_message(
    state: ClientState,
    message: str | bytes,
    agent: NovaStageZeroAgent,
    ws_callback: Callable[[dict], Any],
):
    """
    Route message to appropriate handler.
    
    MESSAGE TYPES:
    - Binary: Drawing upload
    - JSON:
        - type: "ping" → heartbeat
        - type: "onboarding" → accessibility setup
        - type: "confirmation" → action confirmation response
        - type: "cancel" → cancel pending action
    """
    
    # ==========================================================================
    # BINARY: Drawing upload
    # ==========================================================================
    if isinstance(message, bytes):
        logger.info(f"[{state.client_id}] Drawing: {len(message)} bytes")
        
        # Notify input received
        feedback_mgr = get_feedback_manager()
        if feedback_mgr:
            await feedback_mgr.input_received("drawing")
        
        # Process through agent
        response = await agent.handle_drawing_image(message, ws_callback)
        
        # Response is sent by execution engine via ws_callback
        return
    
    # ==========================================================================
    # JSON: Parse and route
    # ==========================================================================
    data = json.loads(message)
    msg_type = data.get("type", "unknown")
    
    print(f"[WS RECEIVE] type={msg_type}")
    
    # --------------------------------------------------------------------------
    # PING: Heartbeat
    # --------------------------------------------------------------------------
    if msg_type == "ping":
        await state.send({
            "type": "pong",
            "status": "alive",
        })
        return
    
    # --------------------------------------------------------------------------
    # ONBOARDING: Accessibility setup
    # --------------------------------------------------------------------------
    if msg_type == "onboarding":
        selections = data.get("selections", [])
        
        print(f"[ONBOARDING] Selections: {selections}")
        
        # Process onboarding
        result = process_onboarding_request(selections)
        
        if result.get("status") == "success":
            state.profile = result.get("profile")
            state.onboarded = True
            
            # Update feedback manager with profile
            feedback_mgr = get_feedback_manager()
            if feedback_mgr:
                feedback_mgr.update_profile(state.profile)
                await feedback_mgr.onboarding_complete()
            
            # Update agent's pipeline_engine profile (UNIFIED)
            if hasattr(agent, 'pipeline_engine') and state.profile:
                agent.pipeline_engine.update_profile(state.profile)
            
            # DEPRECATED: Legacy engine support
            if hasattr(agent, 'engine') and state.profile:
                agent.engine.profile = state.profile
                agent.engine.feedback.update_profile(state.profile)
            
            await state.send({
                "type": "onboarding_complete",
                "profile": state.profile.to_dict() if state.profile else {},
                "message": "Accessibility profile configured",
            })
        else:
            await state.send({
                "type": "error",
                "message": result.get("message", "Onboarding failed"),
            })
        return
    
    # --------------------------------------------------------------------------
    # CONFIRMATION: Action confirmation response
    # --------------------------------------------------------------------------
    if msg_type == "confirmation":
        confirmation_id = data.get("confirmation_id")
        confirmed = data.get("confirmed", False)
        
        print(f"[CONFIRMATION] id={confirmation_id} confirmed={confirmed}")
        
        # Route to confirmation manager
        confirmation_mgr = get_confirmation_manager()
        if confirmation_mgr:
            handled = confirmation_mgr.handle_response(confirmation_id, confirmed)
            if not handled:
                await state.send({
                    "type": "error",
                    "message": "Confirmation expired or invalid",
                })
        else:
            # Also check agent's engine
            if hasattr(agent, 'engine'):
                handled = agent.engine.handle_confirmation_response(confirmation_id, confirmed)
                if not handled:
                    await state.send({
                        "type": "error",
                        "message": "Confirmation expired or invalid",
                    })
        return
    
    # --------------------------------------------------------------------------
    # CANCEL: Cancel pending action
    # --------------------------------------------------------------------------
    if msg_type == "cancel":
        confirmation_id = data.get("confirmation_id")
        
        print(f"[CANCEL] id={confirmation_id}")
        
        confirmation_mgr = get_confirmation_manager()
        if confirmation_mgr:
            confirmation_mgr.handle_response(confirmation_id, False)
        
        await state.send({
            "type": "cancelled",
            "confirmation_id": confirmation_id,
        })
        return
    
    # --------------------------------------------------------------------------
    # DRAWING (JSON): Drawing URL (alternative to binary)
    # --------------------------------------------------------------------------
    if msg_type == "drawing":
        image_url = data.get("url")
        image_data = data.get("data")  # Base64 encoded
        
        if image_url:
            # URL-based drawing
            logger.info(f"[{state.client_id}] Drawing URL: {image_url}")
            response = await agent.handle_drawing_url(image_url, ws_callback)
        elif image_data:
            # Base64 drawing
            import base64
            binary_data = base64.b64decode(image_data)
            logger.info(f"[{state.client_id}] Drawing base64: {len(binary_data)} bytes")
            response = await agent.handle_drawing_image(binary_data, ws_callback)
        else:
            await state.send({
                "type": "error",
                "message": "Drawing requires 'url' or 'data' field",
            })
        return
    
    # --------------------------------------------------------------------------
    # UNKNOWN: Log and ignore
    # --------------------------------------------------------------------------
    logger.warning(f"[{state.client_id}] Unknown message type: {msg_type}")
    await state.send({
        "type": "error",
        "message": f"Unknown message type: {msg_type}",
    })


# =============================================================================
# SERVER STARTUP
# =============================================================================

async def start_websocket_server(
    agent: NovaStageZeroAgent,
    token: str,
    host: str = "0.0.0.0",
    port: int = 8765,
):
    """Start the Stage 0 WebSocket server."""
    logger.info(f"Starting WebSocket server on {host}:{port}")
    print(f"\n{'='*60}")
    print(f"[WEBSOCKET] Server starting on ws://{host}:{port}")
    print(f"{'='*60}\n")

    async with websockets.serve(
        lambda websocket: handle_connection(
            websocket,
            agent=agent,
            token=token,
        ),
        host,
        port,
        max_size=5 * 1024 * 1024,  # 5MB max message size
    ):
        logger.info(f"WebSocket server listening on ws://{host}:{port}")
        print(f"[WEBSOCKET] Ready for connections")
        print(f"[WEBSOCKET] Use token: {token[:8]}...")
        await asyncio.get_running_loop().create_future()


# =============================================================================
# HELPERS
# =============================================================================

def _is_authenticated(path: str, expected_token: str) -> bool:
    """Check if connection has valid token."""
    parsed = urlparse(path)
    query = parse_qs(parsed.query)
    received_token = query.get("token", [None])[0]
    return received_token == expected_token


def _extract_request_path(websocket: Any) -> str:
    """Extract request path from websocket object."""
    path = getattr(websocket, "path", None)
    if isinstance(path, str):
        return path

    request = getattr(websocket, "request", None)
    request_path = getattr(request, "path", None)
    if isinstance(request_path, str):
        return request_path

    return ""
