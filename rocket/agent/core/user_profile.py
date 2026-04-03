"""User Profile Schema — Accessibility-First Onboarding Contract.

This module defines the contract between mobile app and backend
for user accessibility profiles.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Optional


# =============================================================================
# ACCESSIBILITY OPTIONS (Mobile Onboarding)
# =============================================================================

class AccessibilityOption(Enum):
    """
    Onboarding options presented to user.
    
    Mobile app shows:
    1 → Blind but can hear
    2 → Blind and cannot hear  
    3 → Blind and cannot speak
    4 → Blind and uses Braille
    5 → Motor impairment (limited touch)
    """
    BLIND_CAN_HEAR = 1
    BLIND_CANNOT_HEAR = 2
    BLIND_CANNOT_SPEAK = 3
    BLIND_USES_BRAILLE = 4
    MOTOR_IMPAIRMENT = 5


# =============================================================================
# USER PROFILE DATACLASS
# =============================================================================

@dataclass
class UserProfile:
    """
    User accessibility profile.
    
    Sent from mobile app to backend after onboarding.
    """
    
    # Vision
    blind: bool = False
    low_vision: bool = False
    
    # Hearing
    can_hear: bool = True
    deaf: bool = False
    
    # Speech
    can_speak: bool = True
    
    # Input methods
    uses_braille: bool = False
    braille_dots: int = 8  # 8-dot or 16-dot
    
    # Motor
    motor_impairment: bool = False
    limited_touch: bool = False
    
    # Preferred feedback modes (derived)
    prefers_voice: bool = True
    prefers_haptic: bool = False
    prefers_braille: bool = False
    prefers_large_ui: bool = False
    
    # Metadata
    profile_version: str = "1.0"
    onboarding_complete: bool = False
    
    def __post_init__(self):
        """Derive feedback preferences from selections."""
        self._derive_preferences()
    
    def _derive_preferences(self):
        """Auto-derive feedback modes based on abilities."""
        # If blind and can hear → prefer voice
        if self.blind and self.can_hear:
            self.prefers_voice = True
        
        # If blind and deaf → must use haptic
        if self.blind and self.deaf:
            self.prefers_haptic = True
            self.prefers_voice = False
        
        # If cannot hear → haptic feedback
        if not self.can_hear or self.deaf:
            self.prefers_haptic = True
        
        # If uses braille → send braille output
        if self.uses_braille:
            self.prefers_braille = True
        
        # If low vision → large UI
        if self.low_vision:
            self.prefers_large_ui = True
    
    @classmethod
    def from_options(cls, options: List[int]) -> "UserProfile":
        """
        Create profile from onboarding selections.
        
        Args:
            options: List of selected option numbers (1-5)
        """
        profile = cls()
        
        for opt in options:
            if opt == AccessibilityOption.BLIND_CAN_HEAR.value:
                profile.blind = True
                profile.can_hear = True
            
            elif opt == AccessibilityOption.BLIND_CANNOT_HEAR.value:
                profile.blind = True
                profile.can_hear = False
                profile.deaf = True
            
            elif opt == AccessibilityOption.BLIND_CANNOT_SPEAK.value:
                profile.blind = True
                profile.can_speak = False
            
            elif opt == AccessibilityOption.BLIND_USES_BRAILLE.value:
                profile.blind = True
                profile.uses_braille = True
            
            elif opt == AccessibilityOption.MOTOR_IMPAIRMENT.value:
                profile.motor_impairment = True
                profile.limited_touch = True
        
        profile.onboarding_complete = True
        profile._derive_preferences()
        return profile
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Create from dictionary."""
        profile = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return profile
    
    def get_feedback_mode(self) -> str:
        """Get primary feedback mode."""
        if self.prefers_voice and self.can_hear:
            return "voice"
        elif self.prefers_haptic:
            return "haptic"
        elif self.prefers_braille:
            return "braille"
        else:
            return "visual"
    
    def get_all_feedback_modes(self) -> List[str]:
        """Get all applicable feedback modes."""
        modes = []
        if self.prefers_voice and self.can_hear:
            modes.append("voice")
        if self.prefers_haptic:
            modes.append("haptic")
        if self.prefers_braille:
            modes.append("braille")
        if not modes:
            modes.append("visual")
        return modes


# =============================================================================
# PROFILE PERSISTENCE
# =============================================================================

DEFAULT_PROFILE_PATH = Path.home() / ".rocket" / "user_profile.json"


def save_profile(profile: UserProfile, path: Optional[Path] = None) -> Path:
    """Save user profile to disk."""
    path = path or DEFAULT_PROFILE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w") as f:
        json.dump(profile.to_dict(), f, indent=2)
    
    print(f"[PROFILE] Saved to {path}")
    return path


def load_profile(path: Optional[Path] = None) -> Optional[UserProfile]:
    """Load user profile from disk."""
    path = path or DEFAULT_PROFILE_PATH
    
    if not path.exists():
        print(f"[PROFILE] No profile found at {path}")
        return None
    
    with open(path, "r") as f:
        data = json.load(f)
    
    profile = UserProfile.from_dict(data)
    print(f"[PROFILE] Loaded from {path}")
    return profile


def get_or_create_profile() -> UserProfile:
    """Get existing profile or create default."""
    profile = load_profile()
    if profile is None:
        profile = UserProfile()
        print("[PROFILE] Created default profile (onboarding not complete)")
    return profile


# =============================================================================
# ONBOARDING API CONTRACT (Mobile ↔ Backend)
# =============================================================================

ONBOARDING_REQUEST_SCHEMA = {
    "type": "onboarding",
    "selections": [1, 2, 3],  # List of selected options
}

ONBOARDING_RESPONSE_SCHEMA = {
    "status": "success",
    "profile": {
        "blind": True,
        "can_hear": False,
        "can_speak": True,
        "uses_braille": False,
        "motor_impairment": False,
        "prefers_voice": False,
        "prefers_haptic": True,
        "feedback_modes": ["haptic"],
    },
    "message": "Profile saved successfully",
}


def process_onboarding_request(request) -> dict:
    """
    Process onboarding request from mobile app.
    
    Args:
        request: Either a list of selections [1, 2, ...] or
                 dict {"type": "onboarding", "selections": [1, 2, ...]}
    
    Returns:
        Response with created profile
    """
    print("\n========== [ONBOARDING] ==========")
    
    # Handle both list and dict input
    if isinstance(request, list):
        selections = request
    elif isinstance(request, dict):
        selections = request.get("selections", [])
    else:
        return {
            "status": "error",
            "message": f"Invalid onboarding request type: {type(request)}",
        }
    
    print(f"[SELECTIONS] {selections}")
    
    # Validate selections
    if not selections:
        return {
            "status": "error",
            "message": "No selections provided",
        }
    
    # Create profile from selections
    try:
        profile = UserProfile.from_options(selections)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create profile: {e}",
        }
    
    # Save to disk
    save_profile(profile)
    
    # Return response
    response = {
        "status": "success",
        "profile": profile,  # Return the UserProfile object
        "data": {
            "blind": profile.blind,
            "can_hear": profile.can_hear,
            "can_speak": profile.can_speak,
            "deaf": profile.deaf,
            "uses_braille": profile.uses_braille,
            "motor_impairment": profile.motor_impairment,
            "prefers_voice": profile.prefers_voice,
            "prefers_haptic": profile.prefers_haptic,
            "prefers_braille": profile.prefers_braille,
            "feedback_modes": profile.get_all_feedback_modes(),
        },
        "message": "Profile saved successfully",
    }
    
    print(f"[PROFILE CREATED] {profile.get_feedback_mode()} mode")
    return response


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "UserProfile",
    "AccessibilityOption",
    "save_profile",
    "load_profile",
    "get_or_create_profile",
    "process_onboarding_request",
]
