"""Stage 1.5 — Adaptive User Accessibility & Confirmation System.

Dynamically adapts confirmation methods based on user's disability profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
import json
from pathlib import Path

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# USER PROFILE TYPES
# =============================================================================

class VisionLevel(Enum):
    NORMAL = "normal"
    LOW_VISION = "low_vision"
    BLIND = "blind"


class HearingLevel(Enum):
    NORMAL = "normal"
    HARD_OF_HEARING = "hard_of_hearing"
    DEAF = "deaf"


class InteractionMode(Enum):
    TOUCH = "touch"
    VOICE = "voice"
    HAPTIC = "haptic"
    BRAILLE = "braille"


@dataclass
class UserProfile:
    """User accessibility profile."""
    vision: VisionLevel = VisionLevel.NORMAL
    hearing: HearingLevel = HearingLevel.NORMAL
    interaction: list[InteractionMode] = field(default_factory=lambda: [InteractionMode.TOUCH])
    
    def to_dict(self) -> dict:
        return {
            "vision": self.vision.value,
            "hearing": self.hearing.value,
            "interaction": [m.value for m in self.interaction],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        return cls(
            vision=VisionLevel(data.get("vision", "normal")),
            hearing=HearingLevel(data.get("hearing", "normal")),
            interaction=[InteractionMode(m) for m in data.get("interaction", ["touch"])],
        )


# =============================================================================
# HAPTIC PATTERNS — Vibration language for accessibility
# =============================================================================

HAPTIC_PATTERNS = {
    "alert": [200, 100, 200],           # ⚡⚡ danger warning
    "confirm_prompt": [500],            # ⚡ waiting for input
    "success": [100, 50, 100],          # ✓ executed successfully
    "error": [300, 100, 300, 100, 300], # ✗ error occurred
    "cancel": [100],                    # action cancelled
}


# =============================================================================
# CONFIRMATION RESPONSE TYPES
# =============================================================================

@dataclass
class ConfirmationRequest:
    """Request for user confirmation."""
    message: str
    intent_type: str
    slots: dict
    danger_level: str  # "low", "medium", "high"
    

@dataclass
class ConfirmationResponse:
    """User's response to confirmation request."""
    confirmed: bool
    method: str  # "touch", "voice", "haptic", "timeout"
    response_time_ms: int = 0


# =============================================================================
# ADAPTIVE CONFIRMATION ENGINE
# =============================================================================

class AdaptiveConfirmationEngine:
    """
    Adaptive confirmation system that adjusts communication based on user profile.
    
    Cases:
    - Blind + Can Hear → TTS (Text-to-Speech)
    - Blind + Deaf → Haptic patterns
    - Low Vision → Large UI + high contrast + vibration
    - Braille User → Braille display (future)
    - Normal → Standard UI dialog
    """
    
    def __init__(self, user_profile: UserProfile):
        self.profile = user_profile
        self._tts_engine = None
    
    def _get_tts_engine(self):
        """Lazy load TTS engine."""
        if self._tts_engine is None:
            try:
                import pyttsx3
                self._tts_engine = pyttsx3.init()
                self._tts_engine.setProperty('rate', 150)
            except Exception as e:
                logger.error(f"Failed to initialize TTS: {e}")
                self._tts_engine = None
        return self._tts_engine
    
    def get_confirmation_method(self) -> str:
        """Determine the best confirmation method for this user."""
        vision = self.profile.vision
        hearing = self.profile.hearing
        interactions = self.profile.interaction
        
        # Case 1: Blind + Can Hear → TTS
        if vision == VisionLevel.BLIND and hearing != HearingLevel.DEAF:
            return "tts"
        
        # Case 2: Blind + Deaf → Haptic
        if vision == VisionLevel.BLIND and hearing == HearingLevel.DEAF:
            return "haptic"
        
        # Case 3: Low Vision → Large UI with vibration assist
        if vision == VisionLevel.LOW_VISION:
            return "large_ui_haptic"
        
        # Case 4: Braille preference
        if InteractionMode.BRAILLE in interactions:
            return "braille"
        
        # Case 5: Voice preference
        if InteractionMode.VOICE in interactions:
            return "voice"
        
        # Default: Standard UI
        return "standard_ui"
    
    def build_confirmation_message(self, request: ConfirmationRequest) -> dict:
        """
        Build confirmation message adapted to user profile.
        
        Returns dict with:
        - message: The text message
        - tts_message: Message for TTS (may differ)
        - haptic_pattern: Vibration pattern to use
        - ui_config: UI display configuration
        """
        base_message = request.message
        
        # Build TTS-friendly message
        if request.intent_type == "TYPE_TEXT":
            tts_message = f"Warning. You are about to type: {request.slots.get('text', '')}. Do you want to proceed?"
        elif request.intent_type == "PRESS_KEYS":
            tts_message = f"Warning. You are about to press keys: {request.slots.get('keys', '')}. Do you want to proceed?"
        else:
            tts_message = f"Do you want to execute: {request.intent_type}?"
        
        # Select haptic pattern based on danger level
        if request.danger_level == "high":
            haptic = HAPTIC_PATTERNS["alert"]
        else:
            haptic = HAPTIC_PATTERNS["confirm_prompt"]
        
        # UI config for low vision
        ui_config = {
            "font_size": 24 if self.profile.vision == VisionLevel.LOW_VISION else 16,
            "high_contrast": self.profile.vision in [VisionLevel.LOW_VISION, VisionLevel.BLIND],
            "button_size": "large" if self.profile.vision == VisionLevel.LOW_VISION else "normal",
        }
        
        return {
            "message": base_message,
            "tts_message": tts_message,
            "haptic_pattern": haptic,
            "ui_config": ui_config,
            "method": self.get_confirmation_method(),
        }
    
    def speak(self, message: str) -> bool:
        """Speak message using TTS."""
        engine = self._get_tts_engine()
        if engine:
            try:
                engine.say(message)
                engine.runAndWait()
                return True
            except Exception as e:
                logger.error(f"TTS failed: {e}")
        return False
    
    async def request_confirmation(
        self,
        request: ConfirmationRequest,
        response_callback: Optional[Callable] = None,
    ) -> ConfirmationResponse:
        """
        Request confirmation from user using adaptive method.
        
        This method prepares the confirmation request and returns the
        message data to be sent to the mobile app. The actual confirmation
        happens on the mobile side.
        """
        method = self.get_confirmation_method()
        confirmation_data = self.build_confirmation_message(request)
        
        print(f"\n========== [CONFIRMATION REQUEST] ==========")
        print(f"[METHOD] {method}")
        print(f"[MESSAGE] {request.message}")
        print(f"[INTENT] {request.intent_type}")
        print(f"[DANGER] {request.danger_level}")
        
        logger.info(f"[ACCESSIBILITY] Confirmation requested via {method}")
        
        # For TTS method, speak on server side if user is connected
        if method == "tts":
            self.speak(confirmation_data["tts_message"])
        
        # Return the confirmation data to be sent to mobile
        # The actual response will come back via WebSocket
        return confirmation_data


# =============================================================================
# USER PROFILE PERSISTENCE
# =============================================================================

def load_user_profile(profile_path: Path) -> UserProfile:
    """Load user profile from disk."""
    if profile_path.exists():
        try:
            with open(profile_path, "r") as f:
                data = json.load(f)
            return UserProfile.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load user profile: {e}")
    return UserProfile()


def save_user_profile(profile: UserProfile, profile_path: Path) -> bool:
    """Save user profile to disk."""
    try:
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        with open(profile_path, "w") as f:
            json.dump(profile.to_dict(), f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save user profile: {e}")
        return False


# =============================================================================
# CONFIRMATION FLOW
# =============================================================================

def should_require_confirmation(intent: dict, profile: UserProfile) -> bool:
    """
    Determine if confirmation is required for this intent.
    
    NEVER require confirmation for:
    - OPEN_APP
    - OPEN_URL
    - SEARCH_WEB
    
    MAY require confirmation for:
    - TYPE_TEXT (if contains sensitive patterns)
    - PRESS_KEYS (if contains system keys)
    """
    intent_type = intent.get("intent", "")
    slots = intent.get("slots", {})
    
    # Safe intents — never require confirmation
    if intent_type in ["OPEN_APP", "OPEN_URL", "SEARCH_WEB", "SCREENSHOT"]:
        return False
    
    # TYPE_TEXT — check content
    if intent_type == "TYPE_TEXT":
        from agent.core.safety import is_dangerous_text
        text = slots.get("text", "")
        return is_dangerous_text(text)
    
    # PRESS_KEYS — check for dangerous combos
    if intent_type == "PRESS_KEYS":
        from agent.core.safety import is_dangerous_keys
        keys = slots.get("keys", "")
        return is_dangerous_keys(keys)
    
    return False


def get_danger_level(intent: dict) -> str:
    """Determine danger level of an intent."""
    intent_type = intent.get("intent", "")
    slots = intent.get("slots", {})
    
    if intent_type == "TYPE_TEXT":
        text = slots.get("text", "").lower()
        if any(p in text for p in ["rm -rf", "format", "del /s", "shutdown"]):
            return "high"
        return "medium"
    
    if intent_type == "PRESS_KEYS":
        keys = slots.get("keys", "").lower()
        if "ctrl+alt+del" in keys:
            return "high"
        if "alt+f4" in keys:
            return "medium"
        return "low"
    
    return "low"
