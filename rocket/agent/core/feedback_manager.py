"""Global Feedback Manager — Unified Screen Reader & Notification System.

This module provides a SINGLE entry point for ALL user notifications.
Every system component MUST use this for user communication.

Features:
- Accessibility-aware (voice/haptic/braille)
- Priority queue system
- No overlapping speech
- WebSocket integration
- Haptic pattern mapping
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import deque

from agent.core.user_profile import UserProfile, get_or_create_profile
from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# PRIORITY LEVELS
# =============================================================================

class Priority(Enum):
    """Notification priority levels."""
    LOW = 0       # Non-critical info
    NORMAL = 1    # Standard feedback
    HIGH = 2      # Important - override queue
    CRITICAL = 3  # Interrupt everything


# =============================================================================
# EVENT TYPES
# =============================================================================

class EventType(Enum):
    """System event types with default haptic patterns."""
    
    # System events
    SYSTEM_READY = "system_ready"
    SYSTEM_ERROR = "system_error"
    CONNECTION_OPEN = "connection_open"
    CONNECTION_CLOSE = "connection_close"
    
    # Input events
    INPUT_RECEIVED = "input_received"
    DRAWING_RECEIVED = "drawing_received"
    VOICE_RECEIVED = "voice_received"
    
    # Model events
    MODEL_PROCESSING = "model_processing"
    MODEL_SUCCESS = "model_success"
    MODEL_FAILURE = "model_failure"
    MODEL_FALLBACK = "model_fallback"
    
    # Safety events
    SAFETY_CHECK = "safety_check"
    SAFETY_PASSED = "safety_passed"
    SAFETY_BLOCKED = "safety_blocked"
    DANGER_DETECTED = "danger_detected"
    
    # Confirmation events
    CONFIRMATION_REQUIRED = "confirmation_required"
    CONFIRMATION_WAITING = "confirmation_waiting"
    CONFIRMATION_RECEIVED = "confirmation_received"
    CONFIRMATION_TIMEOUT = "confirmation_timeout"
    
    # Execution events
    EXECUTION_START = "execution_start"
    EXECUTION_PROGRESS = "execution_progress"
    EXECUTION_SUCCESS = "execution_success"
    EXECUTION_FAILURE = "execution_failure"
    EXECUTION_VERIFIED = "execution_verified"
    
    # Multi-step events
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    STEP_FAILED = "step_failed"
    ALL_STEPS_COMPLETE = "all_steps_complete"


# =============================================================================
# HAPTIC PATTERNS
# =============================================================================

HAPTIC_PATTERNS: Dict[str, List[int]] = {
    # System
    "system_ready": [100, 50, 100, 50, 200],     # da-da-daaa
    "system_error": [300, 100, 300, 100, 300],   # long error
    "connection_open": [100, 100, 100],          # triple tap
    "connection_close": [200, 100, 200],         # double long
    
    # Input
    "input_received": [50],                       # single tap
    "drawing_received": [50, 50, 50],            # quick triple
    
    # Model
    "model_processing": [50, 100] * 3,           # pulsing
    "model_success": [100, 50, 100],             # success
    "model_failure": [300, 100, 300],            # error
    "model_fallback": [100, 100, 200],           # warning
    
    # Safety
    "safety_passed": [50, 50],                   # quick double
    "safety_blocked": [200, 100, 200, 100, 200], # warning
    "danger_detected": [100, 50] * 5,            # rapid alarm
    
    # Confirmation
    "confirmation_required": [500],              # long hold
    "confirmation_waiting": [200, 500, 200],     # waiting
    "confirmation_timeout": [300, 100, 300],     # timeout
    
    # Execution
    "execution_start": [50, 50],                 # short start
    "execution_success": [100, 50, 100],         # double tap
    "execution_failure": [300, 100, 300, 100, 300],  # triple long
    "execution_verified": [100, 50, 100, 50, 200],   # verified
    
    # Multi-step
    "step_start": [50],                          # single
    "step_complete": [100],                      # medium
    "step_failed": [200, 100, 200],              # error
    "all_steps_complete": [100, 50, 100, 50, 200],  # celebration
}


# =============================================================================
# NOTIFICATION DATACLASS
# =============================================================================

@dataclass
class Notification:
    """A notification to send to user."""
    event_type: str
    message: str
    priority: Priority = Priority.NORMAL
    timestamp: float = field(default_factory=time.time)
    data: Optional[Dict[str, Any]] = None
    
    def to_websocket_message(self, modes: Dict[str, bool]) -> dict:
        """Convert to WebSocket message."""
        return {
            "type": "feedback",
            "event": self.event_type,
            "text": self.message,
            "mode": [k for k, v in modes.items() if v],
            "haptic_pattern": self.event_type,
            "haptic_data": HAPTIC_PATTERNS.get(self.event_type, [100]),
            "priority": self.priority.name.lower(),
            "timestamp": self.timestamp,
            "data": self.data,
        }


# =============================================================================
# FEEDBACK MANAGER (SINGLETON)
# =============================================================================

class FeedbackManager:
    """
    Global feedback manager for all system notifications.
    
    EVERY component MUST use this for user communication.
    
    Usage:
        manager = get_feedback_manager()
        await manager.notify(EventType.EXECUTION_START, "Opening Chrome")
    """
    
    _instance: Optional["FeedbackManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.profile: Optional[UserProfile] = None
        self.websocket_callback: Optional[Callable[[dict], Any]] = None
        
        # Queue system
        self._queue: deque[Notification] = deque()
        self._is_speaking = False
        self._current_notification: Optional[Notification] = None
        
        # Callbacks
        self._voice_callback: Optional[Callable[[str], Any]] = None
        self._haptic_callback: Optional[Callable[[List[int]], Any]] = None
        self._braille_callback: Optional[Callable[[str], Any]] = None
    
    def initialize(
        self,
        profile: Optional[UserProfile] = None,
        websocket_callback: Optional[Callable[[dict], Any]] = None,
    ):
        """Initialize with user profile and WebSocket callback."""
        self.profile = profile or get_or_create_profile()
        self.websocket_callback = websocket_callback
        
        print(f"\n[FEEDBACK MANAGER] Initialized")
        print(f"[PROFILE] voice={self.profile.prefers_voice}, haptic={self.profile.prefers_haptic}")
    
    def set_websocket_callback(self, callback: Callable[[dict], Any]):
        """Set WebSocket callback for sending messages."""
        self.websocket_callback = callback
    
    def set_profile(self, profile: UserProfile):
        """Update user profile."""
        self.profile = profile
    
    # -------------------------------------------------------------------------
    # CORE NOTIFICATION API
    # -------------------------------------------------------------------------
    
    async def notify(
        self,
        event_type: EventType | str,
        message: str,
        priority: Priority | str = Priority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """
        Send notification to user.
        
        THIS IS THE MAIN API — USE THIS EVERYWHERE.
        
        Args:
            event_type: Type of event (determines haptic pattern)
            message: Human-readable message
            priority: Notification priority
            data: Optional additional data
        
        Returns:
            WebSocket message that was sent
        """
        # Normalize event type
        if isinstance(event_type, EventType):
            event_str = event_type.value
        else:
            event_str = event_type
        
        # Normalize priority
        if isinstance(priority, str):
            priority = Priority[priority.upper()]
        
        # Create notification
        notification = Notification(
            event_type=event_str,
            message=message,
            priority=priority,
            data=data,
        )
        
        # Log
        print(f"\n[NOTIFY] [{priority.name}] {event_str}: {message}")
        
        # Handle based on priority
        if priority == Priority.CRITICAL:
            # Interrupt current and send immediately
            await self._send_immediate(notification)
        elif priority == Priority.HIGH:
            # Add to front of queue
            self._queue.appendleft(notification)
            await self._process_queue()
        else:
            # Add to queue
            self._queue.append(notification)
            await self._process_queue()
        
        # Build message
        modes = self._get_modes()
        ws_message = notification.to_websocket_message(modes)
        
        # Send via WebSocket
        if self.websocket_callback:
            try:
                await self._send_websocket(ws_message)
            except Exception as e:
                print(f"[WS SEND ERROR] {e}")
        
        return ws_message
    
    async def _send_immediate(self, notification: Notification):
        """Send notification immediately, interrupting queue."""
        self._is_speaking = False  # Interrupt
        self._current_notification = notification
        
        modes = self._get_modes()
        
        # Voice
        if modes.get("voice") and self._voice_callback:
            await self._voice_callback(notification.message)
        
        # Haptic
        if modes.get("haptic") and self._haptic_callback:
            pattern = HAPTIC_PATTERNS.get(notification.event_type, [100])
            await self._haptic_callback(pattern)
    
    async def _process_queue(self):
        """Process notification queue."""
        if self._is_speaking or not self._queue:
            return
        
        self._is_speaking = True
        
        while self._queue:
            notification = self._queue.popleft()
            self._current_notification = notification
            
            modes = self._get_modes()
            
            # Voice (simulated delay)
            if modes.get("voice"):
                # In real implementation, would wait for TTS completion
                await asyncio.sleep(0.1)
            
            # Haptic is instant
        
        self._is_speaking = False
    
    async def _send_websocket(self, message: dict):
        """Send message via WebSocket."""
        print(f"[WS SEND] {message.get('type')}: {message.get('text', '')[:50]}")
        
        if self.websocket_callback:
            if asyncio.iscoroutinefunction(self.websocket_callback):
                await self.websocket_callback(message)
            else:
                self.websocket_callback(message)
    
    def _get_modes(self) -> Dict[str, bool]:
        """Get active feedback modes from profile."""
        if not self.profile:
            return {"voice": True, "haptic": False, "braille": False, "visual": True}
        
        return {
            "voice": self.profile.prefers_voice and self.profile.can_hear,
            "haptic": self.profile.prefers_haptic,
            "braille": self.profile.prefers_braille,
            "visual": True,
        }
    
    # -------------------------------------------------------------------------
    # CONVENIENCE METHODS
    # -------------------------------------------------------------------------
    
    async def system_ready(self):
        """Notify system is ready."""
        await self.notify(EventType.SYSTEM_READY, "System ready")
    
    async def system_error(self, error: str):
        """Notify system error."""
        await self.notify(EventType.SYSTEM_ERROR, f"Error: {error}", Priority.CRITICAL)
    
    async def input_received(self, input_type: str = "drawing"):
        """Notify input received."""
        await self.notify(EventType.INPUT_RECEIVED, f"Received {input_type}")
    
    async def model_processing(self):
        """Notify model is processing."""
        await self.notify(EventType.MODEL_PROCESSING, "Processing your request")
    
    async def model_success(self, intent: str):
        """Notify model succeeded."""
        await self.notify(EventType.MODEL_SUCCESS, f"Understood: {intent}")
    
    async def model_failure(self, error: str):
        """Notify model failed."""
        await self.notify(EventType.MODEL_FAILURE, f"Could not process: {error}", Priority.HIGH)
    
    async def safety_blocked(self, reason: str):
        """Notify safety blocked."""
        await self.notify(EventType.SAFETY_BLOCKED, f"Blocked: {reason}", Priority.HIGH)
    
    async def danger_detected(self, pattern: str):
        """Notify danger detected."""
        await self.notify(EventType.DANGER_DETECTED, f"Dangerous command detected!", Priority.CRITICAL)
    
    async def confirmation_required(self, action: str, confirmation_id: str):
        """Notify confirmation required."""
        await self.notify(
            EventType.CONFIRMATION_REQUIRED,
            f"Confirm: {action}?",
            Priority.CRITICAL,
            data={"confirmation_id": confirmation_id},
        )
    
    async def execution_start(self, action: str):
        """Notify execution starting."""
        await self.notify(EventType.EXECUTION_START, f"Executing: {action}")
    
    async def execution_success(self, action: str):
        """Notify execution succeeded."""
        await self.notify(EventType.EXECUTION_SUCCESS, f"Done: {action}")
    
    async def execution_failure(self, action: str, error: str):
        """Notify execution failed."""
        await self.notify(EventType.EXECUTION_FAILURE, f"Failed: {action} - {error}", Priority.HIGH)
    
    async def execution_verified(self, action: str):
        """Notify execution verified."""
        await self.notify(EventType.EXECUTION_VERIFIED, f"Verified: {action}")
    
    async def step_start(self, step_num: int, total: int, action: str):
        """Notify step starting."""
        await self.notify(EventType.STEP_START, f"Step {step_num}/{total}: {action}")
    
    async def step_complete(self, step_num: int, total: int):
        """Notify step complete."""
        await self.notify(EventType.STEP_COMPLETE, f"Step {step_num}/{total} complete")
    
    async def all_steps_complete(self, total: int):
        """Notify all steps complete."""
        await self.notify(EventType.ALL_STEPS_COMPLETE, f"All {total} steps complete")


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_feedback_manager: Optional[FeedbackManager] = None


def get_feedback_manager() -> FeedbackManager:
    """Get the global feedback manager singleton."""
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = FeedbackManager()
    return _feedback_manager


def init_feedback_manager(
    profile: Optional[UserProfile] = None,
    websocket_callback: Optional[Callable[[dict], Any]] = None,
) -> FeedbackManager:
    """Initialize and return the feedback manager."""
    manager = get_feedback_manager()
    manager.initialize(profile, websocket_callback)
    return manager


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "FeedbackManager",
    "Priority",
    "EventType",
    "HAPTIC_PATTERNS",
    "get_feedback_manager",
    "init_feedback_manager",
]
