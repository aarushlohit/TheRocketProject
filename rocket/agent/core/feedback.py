"""Accessibility Feedback Hooks — Multi-Modal Output System.

This module provides hooks for sending feedback to users
based on their accessibility profile.

DESIGN PRINCIPLE:
- These are HOOKS, not hardware implementations
- Mobile app implements actual TTS, haptic, braille
- Backend sends messages via WebSocket
- Mobile interprets based on feedback_type
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from agent.core.user_profile import UserProfile, get_or_create_profile


# =============================================================================
# FEEDBACK TYPES
# =============================================================================

class FeedbackType(Enum):
    """Types of feedback that can be sent."""
    VOICE = "voice"          # Text-to-speech
    HAPTIC = "haptic"        # Vibration patterns
    BRAILLE = "braille"      # Braille display data
    VISUAL = "visual"        # On-screen text/UI
    SOUND = "sound"          # Audio cues (non-voice)


# =============================================================================
# HAPTIC PATTERNS
# =============================================================================

class HapticPattern(Enum):
    """
    Predefined haptic vibration patterns.
    
    Format: List of (vibrate_ms, pause_ms) tuples
    """
    # Status patterns
    SUCCESS = "success"           # Short happy pulse
    ERROR = "error"               # Long error buzz
    WARNING = "warning"           # Medium alert
    
    # Action patterns
    CONFIRM_PROMPT = "confirm"    # Asking for confirmation
    EXECUTING = "executing"       # Action in progress
    COMPLETE = "complete"         # Action finished
    
    # Navigation
    OPTION_HIGHLIGHT = "highlight"  # Highlighting an option
    SELECTION_MADE = "selected"     # Option selected


# Haptic pattern definitions (milliseconds)
HAPTIC_PATTERNS: Dict[str, List[int]] = {
    # [vibrate, pause, vibrate, pause, ...]
    "success": [100, 50, 100],                    # ● ● (two quick pulses)
    "error": [300, 100, 300, 100, 300],           # ●●● (three long buzzes)
    "warning": [200, 100, 200],                   # ●● (two medium pulses)
    "confirm": [500],                              # ● (one long pulse - waiting)
    "executing": [50, 50, 50, 50, 50],            # ●●●●● (rapid pulses)
    "complete": [100, 50, 100, 50, 200],          # ●●● (ascending)
    "highlight": [50],                             # ● (single tap)
    "selected": [100, 100, 100],                  # ●●● (confirm tap)
    "danger": [200, 100, 200, 100, 200, 100, 200],  # ●●●● (danger alert)
}


# =============================================================================
# SOUND CUES
# =============================================================================

class SoundCue(Enum):
    """Non-voice audio cues."""
    SUCCESS_CHIME = "success_chime"
    ERROR_TONE = "error_tone"
    NOTIFICATION = "notification"
    CONFIRM_ASK = "confirm_ask"


# =============================================================================
# FEEDBACK MESSAGE DATACLASS
# =============================================================================

@dataclass
class FeedbackMessage:
    """
    A feedback message to send to the user.
    
    Can contain multiple feedback types for multi-modal output.
    """
    
    # Primary content
    text: str
    
    # Feedback types to use
    voice: bool = False
    haptic: bool = False
    braille: bool = False
    visual: bool = True
    
    # Optional specific data
    haptic_pattern: Optional[str] = None
    sound_cue: Optional[str] = None
    braille_data: Optional[str] = None
    
    # Metadata
    priority: str = "normal"  # low, normal, high, critical
    requires_response: bool = False
    
    def to_websocket_message(self) -> dict:
        """Convert to WebSocket message format."""
        return {
            "type": "feedback",
            "text": self.text,
            "modes": {
                "voice": self.voice,
                "haptic": self.haptic,
                "braille": self.braille,
                "visual": self.visual,
            },
            "haptic_pattern": self.haptic_pattern,
            "haptic_data": HAPTIC_PATTERNS.get(self.haptic_pattern) if self.haptic_pattern else None,
            "sound_cue": self.sound_cue,
            "braille_data": self.braille_data,
            "priority": self.priority,
            "requires_response": self.requires_response,
        }


# =============================================================================
# FEEDBACK SENDER (Main Interface)
# =============================================================================

class FeedbackSender:
    """
    Sends feedback to user based on their accessibility profile.
    
    Usage:
        sender = FeedbackSender(user_profile)
        sender.send_success("App opened successfully")
        sender.send_error("Failed to open app")
        sender.ask_confirmation("Execute dangerous command?")
    """
    
    def __init__(
        self,
        profile: Optional[UserProfile] = None,
        websocket_callback: Optional[Callable[[dict], None]] = None,
    ):
        self.profile = profile or get_or_create_profile()
        self.websocket_callback = websocket_callback
        self._pending_confirmations: Dict[str, dict] = {}
    
    def _build_message(
        self,
        text: str,
        haptic_pattern: Optional[str] = None,
        priority: str = "normal",
        requires_response: bool = False,
    ) -> FeedbackMessage:
        """Build feedback message based on user profile."""
        return FeedbackMessage(
            text=text,
            voice=self.profile.prefers_voice and self.profile.can_hear,
            haptic=self.profile.prefers_haptic,
            braille=self.profile.prefers_braille,
            visual=True,  # Always include visual
            haptic_pattern=haptic_pattern,
            priority=priority,
            requires_response=requires_response,
        )
    
    def _send(self, message: FeedbackMessage) -> dict:
        """Send feedback message."""
        ws_message = message.to_websocket_message()
        
        print(f"\n========== [FEEDBACK] ==========")
        print(f"[TEXT] {message.text}")
        print(f"[MODES] voice={message.voice}, haptic={message.haptic}, braille={message.braille}")
        if message.haptic_pattern:
            print(f"[HAPTIC] {message.haptic_pattern}: {HAPTIC_PATTERNS.get(message.haptic_pattern)}")
        
        # Send via WebSocket if callback provided
        if self.websocket_callback:
            self.websocket_callback(ws_message)
        
        return ws_message
    
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    
    def send_success(self, text: str) -> dict:
        """Send success feedback."""
        msg = self._build_message(text, haptic_pattern="success")
        return self._send(msg)
    
    def send_error(self, text: str) -> dict:
        """Send error feedback."""
        msg = self._build_message(text, haptic_pattern="error", priority="high")
        return self._send(msg)
    
    def send_warning(self, text: str) -> dict:
        """Send warning feedback."""
        msg = self._build_message(text, haptic_pattern="warning", priority="normal")
        return self._send(msg)
    
    def send_info(self, text: str) -> dict:
        """Send informational feedback."""
        msg = self._build_message(text)
        return self._send(msg)
    
    def send_executing(self, text: str) -> dict:
        """Send 'action in progress' feedback."""
        msg = self._build_message(text, haptic_pattern="executing")
        return self._send(msg)
    
    def send_complete(self, text: str) -> dict:
        """Send 'action complete' feedback."""
        msg = self._build_message(text, haptic_pattern="complete")
        return self._send(msg)
    
    def ask_confirmation(self, text: str, action_id: str = None) -> dict:
        """
        Ask user for confirmation.
        
        Returns message with requires_response=True.
        Mobile app should send confirmation response.
        """
        msg = self._build_message(
            text,
            haptic_pattern="confirm",
            priority="critical",
            requires_response=True,
        )
        
        ws_message = msg.to_websocket_message()
        ws_message["confirmation_id"] = action_id
        
        print(f"\n========== [CONFIRMATION REQUEST] ==========")
        print(f"[TEXT] {text}")
        print(f"[ACTION_ID] {action_id}")
        
        if self.websocket_callback:
            self.websocket_callback(ws_message)
        
        return ws_message
    
    def send_danger_alert(self, text: str) -> dict:
        """Send critical danger alert."""
        msg = self._build_message(
            text,
            haptic_pattern="danger",
            priority="critical",
        )
        return self._send(msg)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def send_voice(message: str) -> dict:
    """Send voice feedback (TTS). Hook for mobile implementation."""
    print(f"[VOICE] {message}")
    return {
        "type": "feedback",
        "mode": "voice",
        "text": message,
    }


def send_haptic(pattern: str) -> dict:
    """Send haptic feedback. Hook for mobile implementation."""
    pattern_data = HAPTIC_PATTERNS.get(pattern, [100])
    print(f"[HAPTIC] {pattern}: {pattern_data}")
    return {
        "type": "feedback",
        "mode": "haptic",
        "pattern": pattern,
        "data": pattern_data,
    }


def send_braille(text: str) -> dict:
    """Send braille output. Hook for mobile implementation."""
    print(f"[BRAILLE] {text}")
    return {
        "type": "feedback",
        "mode": "braille",
        "text": text,
    }


def send_sound(cue: str) -> dict:
    """Send sound cue. Hook for mobile implementation."""
    print(f"[SOUND] {cue}")
    return {
        "type": "feedback",
        "mode": "sound",
        "cue": cue,
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "FeedbackType",
    "HapticPattern",
    "HAPTIC_PATTERNS",
    "FeedbackMessage",
    "FeedbackSender",
    "send_voice",
    "send_haptic",
    "send_braille",
    "send_sound",
]
