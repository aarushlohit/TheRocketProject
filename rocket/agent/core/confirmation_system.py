"""Confirmation System — Async Confirmation Loop with WebSocket.

Implements proper confirmation flow:
1. Detect dangerous action
2. Send confirmation_request via WebSocket
3. WAIT for response
4. Execute only if confirmed

NO FAKE CONFIRMATIONS.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
from datetime import datetime


# =============================================================================
# CONFIRMATION REQUEST
# =============================================================================

@dataclass
class ConfirmationRequest:
    """A pending confirmation request."""
    id: str
    action: str
    intent_data: dict
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    timeout_seconds: float = 30.0
    
    # Response
    confirmed: Optional[bool] = None
    responded_at: Optional[float] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if confirmation has expired."""
        elapsed = datetime.now().timestamp() - self.created_at
        return elapsed > self.timeout_seconds
    
    @property
    def is_pending(self) -> bool:
        """Check if still waiting for response."""
        return self.confirmed is None and not self.is_expired


# =============================================================================
# CONFIRMATION MANAGER
# =============================================================================

class ConfirmationManager:
    """
    Manages confirmation requests and responses.
    
    Usage:
        manager = ConfirmationManager(websocket_send)
        
        # Request confirmation
        confirmed = await manager.request_confirmation(
            action="Execute rm -rf command",
            intent_data={...},
            timeout=10,
        )
        
        # In WebSocket handler:
        manager.handle_response(confirmation_id, confirmed=True)
    """
    
    def __init__(
        self,
        websocket_callback: Optional[Callable[[dict], Any]] = None,
    ):
        self.websocket_callback = websocket_callback
        self._pending: Dict[str, ConfirmationRequest] = {}
        self._response_events: Dict[str, asyncio.Event] = {}
    
    def set_websocket_callback(self, callback: Callable[[dict], Any]):
        """Set WebSocket callback for sending messages."""
        self.websocket_callback = callback
    
    async def request_confirmation(
        self,
        action: str,
        intent_data: dict,
        timeout: float = 30.0,
    ) -> bool:
        """
        Request user confirmation for an action.
        
        Sends confirmation_request via WebSocket and WAITS for response.
        
        Args:
            action: Description of action to confirm
            intent_data: The intent data that needs confirmation
            timeout: Seconds to wait for response
        
        Returns:
            True if confirmed, False if denied or timeout
        """
        # Generate unique ID
        confirmation_id = str(uuid.uuid4())[:8]
        
        # Create request
        request = ConfirmationRequest(
            id=confirmation_id,
            action=action,
            intent_data=intent_data,
            timeout_seconds=timeout,
        )
        
        # Store pending
        self._pending[confirmation_id] = request
        
        # Create event for waiting
        event = asyncio.Event()
        self._response_events[confirmation_id] = event
        
        print(f"\n========== [CONFIRMATION REQUEST] ==========")
        print(f"[ID] {confirmation_id}")
        print(f"[ACTION] {action}")
        print(f"[TIMEOUT] {timeout}s")
        
        # Send via WebSocket
        ws_message = {
            "type": "confirmation_request",
            "id": confirmation_id,
            "confirmation_id": confirmation_id,
            "text": f"Confirm: {action}?",
            "action": action,
            "timeout": timeout,
            "haptic_pattern": "confirmation_required",
            "haptic_data": [500],  # Long hold
            "priority": "critical",
        }
        
        print(f"[WS SEND] confirmation_request")
        
        if self.websocket_callback:
            if asyncio.iscoroutinefunction(self.websocket_callback):
                await self.websocket_callback(ws_message)
            else:
                self.websocket_callback(ws_message)
        
        # WAIT for response
        print(f"[CONFIRMATION WAIT] Waiting for response...")
        
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            
            # Check response
            response = self._pending.get(confirmation_id)
            if response and response.confirmed is not None:
                print(f"[CONFIRMATION RECEIVED] confirmed={response.confirmed}")
                return response.confirmed
            else:
                print(f"[CONFIRMATION] No valid response")
                return False
                
        except asyncio.TimeoutError:
            print(f"[CONFIRMATION TIMEOUT] No response after {timeout}s")
            
            # Send timeout notification
            timeout_msg = {
                "type": "feedback",
                "event": "confirmation_timeout",
                "text": "Confirmation timed out",
                "haptic_pattern": "confirmation_timeout",
                "haptic_data": [300, 100, 300],
                "priority": "high",
            }
            
            if self.websocket_callback:
                if asyncio.iscoroutinefunction(self.websocket_callback):
                    await self.websocket_callback(timeout_msg)
                else:
                    self.websocket_callback(timeout_msg)
            
            return False
            
        finally:
            # Cleanup
            self._pending.pop(confirmation_id, None)
            self._response_events.pop(confirmation_id, None)
    
    def handle_response(self, confirmation_id: str, confirmed: bool) -> bool:
        """
        Handle confirmation response from mobile app.
        
        Called by WebSocket handler when confirmation message received.
        
        Args:
            confirmation_id: ID from confirmation_request
            confirmed: True if user confirmed, False if denied
        
        Returns:
            True if valid pending confirmation, False otherwise
        """
        print(f"\n[WS RECEIVE] confirmation response")
        print(f"[ID] {confirmation_id}")
        print(f"[CONFIRMED] {confirmed}")
        
        request = self._pending.get(confirmation_id)
        
        if request is None:
            print(f"[ERROR] No pending confirmation with ID {confirmation_id}")
            return False
        
        if request.is_expired:
            print(f"[ERROR] Confirmation {confirmation_id} has expired")
            return False
        
        # Record response
        request.confirmed = confirmed
        request.responded_at = datetime.now().timestamp()
        
        # Signal waiting coroutine
        event = self._response_events.get(confirmation_id)
        if event:
            event.set()
        
        return True
    
    def cancel_all(self):
        """Cancel all pending confirmations."""
        for confirmation_id, event in self._response_events.items():
            request = self._pending.get(confirmation_id)
            if request:
                request.confirmed = False
            event.set()
        
        self._pending.clear()
        self._response_events.clear()
    
    @property
    def pending_count(self) -> int:
        """Number of pending confirmations."""
        return len([r for r in self._pending.values() if r.is_pending])


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_confirmation_manager: Optional[ConfirmationManager] = None


def get_confirmation_manager() -> ConfirmationManager:
    """Get the global confirmation manager singleton."""
    global _confirmation_manager
    if _confirmation_manager is None:
        _confirmation_manager = ConfirmationManager()
    return _confirmation_manager


def init_confirmation_manager(
    websocket_callback: Optional[Callable[[dict], Any]] = None,
) -> ConfirmationManager:
    """Initialize and return the confirmation manager."""
    manager = get_confirmation_manager()
    manager.set_websocket_callback(websocket_callback)
    return manager


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ConfirmationManager",
    "ConfirmationRequest",
    "get_confirmation_manager",
    "init_confirmation_manager",
]
