"""WebSocket Message Handlers — Mobile ↔ Backend Contract.

This module defines the WebSocket message format and handlers
for communication between mobile app and backend.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional


# =============================================================================
# MESSAGE TYPES
# =============================================================================

class MessageType(Enum):
    """Types of WebSocket messages."""
    
    # Mobile → Backend
    DRAWING = "drawing"           # Image data for processing
    ONBOARDING = "onboarding"     # Accessibility profile setup
    CONFIRMATION = "confirmation"  # User confirmation response
    VOICE_COMMAND = "voice"       # Voice command (future)
    
    # Backend → Mobile
    FEEDBACK = "feedback"         # Feedback to user
    RESULT = "result"             # Execution result
    ERROR = "error"               # Error message
    STATUS = "status"             # Status update


# =============================================================================
# MESSAGE SCHEMAS
# =============================================================================

# Mobile → Backend Messages

DRAWING_MESSAGE = {
    "type": "drawing",
    "image": "<base64_encoded_image>",
    "format": "png",  # png, jpeg
    "timestamp": "2026-04-03T12:00:00Z",
}

ONBOARDING_MESSAGE = {
    "type": "onboarding",
    "selections": [1, 2, 3],  # List of selected accessibility options
    # 1 = Blind but can hear
    # 2 = Blind and cannot hear
    # 3 = Blind and cannot speak
    # 4 = Blind and uses Braille
    # 5 = Motor impairment
}

CONFIRMATION_MESSAGE = {
    "type": "confirmation",
    "confirmation_id": "abc12345",
    "confirmed": True,  # or False
}

VOICE_MESSAGE = {
    "type": "voice",
    "text": "open chrome",
    "confidence": 0.95,
}


# Backend → Mobile Messages

FEEDBACK_MESSAGE = {
    "type": "feedback",
    "text": "Opening Chrome",
    "modes": {
        "voice": True,
        "haptic": True,
        "braille": False,
        "visual": True,
    },
    "haptic_pattern": "executing",
    "haptic_data": [50, 50, 50],
    "priority": "normal",
    "requires_response": False,
}

RESULT_MESSAGE = {
    "type": "result",
    "status": "success",  # success, failed, blocked, confirmation_required
    "message": "Opened Chrome",
    "intent": "OPEN_APP",
    "confidence": 0.95,
    "data": {},
}

ERROR_MESSAGE = {
    "type": "error",
    "code": "MODEL_UNAVAILABLE",
    "message": "Both models failed",
    "retryable": True,
}

STATUS_MESSAGE = {
    "type": "status",
    "state": "processing",  # idle, processing, waiting_confirmation
    "message": "Processing your request...",
}


# =============================================================================
# MESSAGE BUILDER
# =============================================================================

class MessageBuilder:
    """Builds WebSocket messages in correct format."""
    
    @staticmethod
    def feedback(
        text: str,
        voice: bool = True,
        haptic: bool = False,
        haptic_pattern: Optional[str] = None,
        priority: str = "normal",
        requires_response: bool = False,
    ) -> dict:
        """Build feedback message."""
        return {
            "type": "feedback",
            "text": text,
            "modes": {
                "voice": voice,
                "haptic": haptic,
                "braille": False,
                "visual": True,
            },
            "haptic_pattern": haptic_pattern,
            "priority": priority,
            "requires_response": requires_response,
        }
    
    @staticmethod
    def result(
        status: str,
        message: str,
        intent: str,
        confidence: float,
        data: Optional[dict] = None,
    ) -> dict:
        """Build result message."""
        return {
            "type": "result",
            "status": status,
            "message": message,
            "intent": intent,
            "confidence": confidence,
            "data": data or {},
        }
    
    @staticmethod
    def error(code: str, message: str, retryable: bool = True) -> dict:
        """Build error message."""
        return {
            "type": "error",
            "code": code,
            "message": message,
            "retryable": retryable,
        }
    
    @staticmethod
    def status(state: str, message: str) -> dict:
        """Build status message."""
        return {
            "type": "status",
            "state": state,
            "message": message,
        }
    
    @staticmethod
    def confirmation_request(text: str, confirmation_id: str) -> dict:
        """Build confirmation request message."""
        return {
            "type": "feedback",
            "text": text,
            "modes": {
                "voice": True,
                "haptic": True,
                "braille": False,
                "visual": True,
            },
            "haptic_pattern": "confirm",
            "priority": "critical",
            "requires_response": True,
            "confirmation_id": confirmation_id,
        }


# =============================================================================
# MESSAGE HANDLER
# =============================================================================

class MessageHandler:
    """
    Handles incoming WebSocket messages.
    
    Usage:
        handler = MessageHandler()
        handler.register("drawing", handle_drawing)
        handler.register("onboarding", handle_onboarding)
        
        response = await handler.handle(message)
    """
    
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
    
    def register(self, message_type: str, handler: Callable) -> None:
        """Register handler for message type."""
        self._handlers[message_type] = handler
    
    async def handle(self, message: dict) -> dict:
        """
        Handle incoming message.
        
        Args:
            message: Parsed WebSocket message
        
        Returns:
            Response message
        """
        message_type = message.get("type", "unknown")
        
        handler = self._handlers.get(message_type)
        if handler is None:
            return MessageBuilder.error(
                code="UNKNOWN_MESSAGE_TYPE",
                message=f"Unknown message type: {message_type}",
                retryable=False,
            )
        
        try:
            return await handler(message)
        except Exception as e:
            return MessageBuilder.error(
                code="HANDLER_ERROR",
                message=str(e),
                retryable=True,
            )


# =============================================================================
# MOBILE APP CONTRACT
# =============================================================================

MOBILE_CONTRACT = """
# Rocket Mobile ↔ Backend WebSocket Contract

## Connection
- URL: ws://<host>:8765
- Protocol: JSON over WebSocket

## Mobile → Backend Messages

### 1. Drawing (Image to Process)
```json
{
    "type": "drawing",
    "image": "<base64_encoded_png>",
    "format": "png",
    "timestamp": "2026-04-03T12:00:00Z"
}
```

### 2. Onboarding (First Launch Only)
```json
{
    "type": "onboarding",
    "selections": [1, 2]
}
```
Options:
- 1 = Blind but can hear
- 2 = Blind and cannot hear
- 3 = Blind and cannot speak
- 4 = Blind and uses Braille
- 5 = Motor impairment

### 3. Confirmation Response
```json
{
    "type": "confirmation",
    "confirmation_id": "abc12345",
    "confirmed": true
}
```

## Backend → Mobile Messages

### 1. Feedback (User Communication)
```json
{
    "type": "feedback",
    "text": "Opening Chrome",
    "modes": {
        "voice": true,
        "haptic": true,
        "braille": false,
        "visual": true
    },
    "haptic_pattern": "executing",
    "haptic_data": [50, 50, 50],
    "priority": "normal",
    "requires_response": false
}
```

Mobile Implementation:
- If `voice: true` → Play TTS
- If `haptic: true` → Vibrate with pattern
- If `braille: true` → Send to braille display
- If `visual: true` → Show on screen
- If `requires_response: true` → Wait for user input

### 2. Result (Execution Complete)
```json
{
    "type": "result",
    "status": "success",
    "message": "Opened Chrome",
    "intent": "OPEN_APP",
    "confidence": 0.95,
    "data": {}
}
```
Status values: success, failed, blocked, confirmation_required

### 3. Error
```json
{
    "type": "error",
    "code": "MODEL_UNAVAILABLE",
    "message": "Both models failed",
    "retryable": true
}
```

### 4. Status Update
```json
{
    "type": "status",
    "state": "processing",
    "message": "Processing your request..."
}
```
State values: idle, processing, waiting_confirmation

## Haptic Patterns
- "success": [100, 50, 100] - Two quick pulses
- "error": [300, 100, 300, 100, 300] - Three long buzzes
- "warning": [200, 100, 200] - Two medium pulses
- "confirm": [500] - One long pulse (waiting)
- "executing": [50, 50, 50, 50, 50] - Rapid pulses
- "complete": [100, 50, 100, 50, 200] - Ascending
- "danger": [200, 100, 200, 100, 200, 100, 200] - Danger alert

## Priority Levels
- "low": Non-critical info
- "normal": Standard feedback
- "high": Important feedback
- "critical": Requires attention (confirmations)
"""


def get_mobile_contract() -> str:
    """Get the mobile app contract documentation."""
    return MOBILE_CONTRACT


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "MessageType",
    "MessageBuilder",
    "MessageHandler",
    "get_mobile_contract",
    "MOBILE_CONTRACT",
]
