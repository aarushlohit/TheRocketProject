"""
Stage 5 — Full Intent System for Autonomous AI Operating System.

Supports 38 intent types across 7 categories for complete OS control.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# INTENT ENUMERATION
# =============================================================================

class IntentCategory(Enum):
    """Intent categories for organization."""
    APP_CONTROL = "app_control"
    BROWSER_CONTROL = "browser_control"
    INPUT_CONTROL = "input_control"
    SYSTEM_CONTROL = "system_control"
    FILE_SYSTEM = "file_system"
    UI_VISION = "ui_vision"
    ADVANCED = "advanced"


# =============================================================================
# APP CONTROL INTENTS (6)
# =============================================================================

APP_CONTROL_INTENTS: Set[str] = {
    "OPEN_APP",       # Open application by name
    "CLOSE_APP",      # Close active/named application
    "MINIMIZE_APP",   # Minimize window to taskbar
    "MAXIMIZE_APP",   # Maximize window
    "SWITCH_APP",     # Switch to running application
    "FOCUS_WINDOW",   # Focus specific window
}


# =============================================================================
# BROWSER CONTROL INTENTS (8)
# =============================================================================

BROWSER_CONTROL_INTENTS: Set[str] = {
    "OPEN_URL",       # Open URL directly
    "SEARCH_WEB",     # Search in browser
    "NEW_TAB",        # Open new tab
    "CLOSE_TAB",      # Close current tab
    "SWITCH_TAB",     # Switch to tab N
    "REFRESH_PAGE",   # Refresh current page
    "SCROLL_UP",      # Scroll page up
    "SCROLL_DOWN",    # Scroll page down
}


# =============================================================================
# INPUT CONTROL INTENTS (7)
# =============================================================================

INPUT_CONTROL_INTENTS: Set[str] = {
    "TYPE_TEXT",      # Type text
    "CLEAR_TEXT",     # Clear text field
    "SELECT_TEXT",    # Select text
    "COPY",           # Copy selection
    "PASTE",          # Paste clipboard
    "CUT",            # Cut selection
    "PRESS_KEYS",     # Press key combination
}


# =============================================================================
# SYSTEM CONTROL INTENTS (6)
# =============================================================================

SYSTEM_CONTROL_INTENTS: Set[str] = {
    "LOCK_SCREEN",       # Lock workstation
    "VOLUME_UP",         # Increase volume
    "VOLUME_DOWN",       # Decrease volume
    "MUTE",              # Toggle mute
    "BRIGHTNESS_UP",     # Increase brightness
    "BRIGHTNESS_DOWN",   # Decrease brightness
}


# =============================================================================
# FILE SYSTEM INTENTS (5)
# =============================================================================

FILE_SYSTEM_INTENTS: Set[str] = {
    "OPEN_FILE",      # Open file
    "DELETE_FILE",    # Delete file (dangerous)
    "CREATE_FILE",    # Create new file
    "MOVE_FILE",      # Move file
    "RENAME_FILE",    # Rename file
}


# =============================================================================
# UI/VISION CONTROL INTENTS (3)
# =============================================================================

UI_VISION_INTENTS: Set[str] = {
    "CLICK_ELEMENT",   # Click semantic target
    "SCROLL",          # Scroll to element
    "WAIT",            # Wait for condition
}


# =============================================================================
# ADVANCED INTENTS (3)
# =============================================================================

ADVANCED_INTENTS: Set[str] = {
    "MULTI_STEP",      # Sequential actions
    "CONDITIONAL",     # If-then logic
    "UNKNOWN",         # Cannot determine intent
}


# =============================================================================
# ALL VALID INTENTS
# =============================================================================

VALID_INTENTS: Set[str] = (
    APP_CONTROL_INTENTS |
    BROWSER_CONTROL_INTENTS |
    INPUT_CONTROL_INTENTS |
    SYSTEM_CONTROL_INTENTS |
    FILE_SYSTEM_INTENTS |
    UI_VISION_INTENTS |
    ADVANCED_INTENTS
)


# =============================================================================
# INTENT → CATEGORY MAPPING
# =============================================================================

def get_intent_category(intent: str) -> Optional[IntentCategory]:
    """Get the category for an intent."""
    if intent in APP_CONTROL_INTENTS:
        return IntentCategory.APP_CONTROL
    if intent in BROWSER_CONTROL_INTENTS:
        return IntentCategory.BROWSER_CONTROL
    if intent in INPUT_CONTROL_INTENTS:
        return IntentCategory.INPUT_CONTROL
    if intent in SYSTEM_CONTROL_INTENTS:
        return IntentCategory.SYSTEM_CONTROL
    if intent in FILE_SYSTEM_INTENTS:
        return IntentCategory.FILE_SYSTEM
    if intent in UI_VISION_INTENTS:
        return IntentCategory.UI_VISION
    if intent in ADVANCED_INTENTS:
        return IntentCategory.ADVANCED
    return None


# =============================================================================
# SLOT REQUIREMENTS
# =============================================================================

REQUIRED_SLOTS: Dict[str, List[str]] = {
    # App control
    "OPEN_APP": ["app"],
    "CLOSE_APP": [],  # Can close active app
    "MINIMIZE_APP": [],
    "MAXIMIZE_APP": [],
    "SWITCH_APP": ["app"],
    "FOCUS_WINDOW": ["window"],
    
    # Browser control
    "OPEN_URL": ["url"],
    "SEARCH_WEB": ["query"],
    "NEW_TAB": [],
    "CLOSE_TAB": [],
    "SWITCH_TAB": ["tab_index"],
    "REFRESH_PAGE": [],
    "SCROLL_UP": [],
    "SCROLL_DOWN": [],
    
    # Input control
    "TYPE_TEXT": ["text"],
    "CLEAR_TEXT": [],
    "SELECT_TEXT": [],
    "COPY": [],
    "PASTE": [],
    "CUT": [],
    "PRESS_KEYS": ["keys"],
    
    # System control
    "LOCK_SCREEN": [],
    "VOLUME_UP": [],
    "VOLUME_DOWN": [],
    "MUTE": [],
    "BRIGHTNESS_UP": [],
    "BRIGHTNESS_DOWN": [],
    
    # File system
    "OPEN_FILE": ["path"],
    "DELETE_FILE": ["path"],
    "CREATE_FILE": ["path"],
    "MOVE_FILE": ["source", "destination"],
    "RENAME_FILE": ["path", "new_name"],
    
    # UI/Vision
    "CLICK_ELEMENT": ["target"],
    "SCROLL": [],
    "WAIT": [],
    
    # Advanced
    "MULTI_STEP": ["steps"],
    "CONDITIONAL": ["condition", "then", "else"],
    "UNKNOWN": [],
}


# =============================================================================
# OPTIONAL SLOTS
# =============================================================================

OPTIONAL_SLOTS: Dict[str, List[str]] = {
    "OPEN_APP": ["arguments"],
    "CLOSE_APP": ["app"],
    "SWITCH_TAB": [],
    "TYPE_TEXT": ["target"],
    "PRESS_KEYS": ["count"],
    "WAIT": ["seconds", "condition"],
    "CLICK_ELEMENT": ["action"],  # click, double_click, right_click
    "SCROLL": ["direction", "amount"],
    "OPEN_FILE": ["application"],
    "CREATE_FILE": ["content"],
}


# =============================================================================
# DANGEROUS INTENTS (Require confirmation)
# =============================================================================

DANGEROUS_INTENTS: Set[str] = {
    "DELETE_FILE",
    "LOCK_SCREEN",
    "CLOSE_APP",  # Only if app has unsaved work
}


# =============================================================================
# SYSTEM-LEVEL INTENTS
# =============================================================================

SYSTEM_LEVEL_INTENTS: Set[str] = {
    "LOCK_SCREEN",
    "VOLUME_UP",
    "VOLUME_DOWN",
    "MUTE",
    "BRIGHTNESS_UP",
    "BRIGHTNESS_DOWN",
}


# =============================================================================
# INTENT VALIDATION
# =============================================================================

def is_valid_intent(intent: str) -> bool:
    """Check if intent is a valid enum value."""
    return intent in VALID_INTENTS


def is_dangerous_intent(intent: str) -> bool:
    """Check if intent is potentially dangerous."""
    return intent in DANGEROUS_INTENTS


def is_system_intent(intent: str) -> bool:
    """Check if intent is a system-level action."""
    return intent in SYSTEM_LEVEL_INTENTS


def validate_slots(intent: str, slots: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate that required slots are present.
    
    Returns: (is_valid, missing_slots)
    """
    required = REQUIRED_SLOTS.get(intent, [])
    missing = [slot for slot in required if slot not in slots or not slots[slot]]
    return len(missing) == 0, missing


def get_intent_info(intent: str) -> Dict[str, Any]:
    """Get full information about an intent."""
    if intent not in VALID_INTENTS:
        return {"valid": False, "error": "Unknown intent"}
    
    return {
        "valid": True,
        "intent": intent,
        "category": get_intent_category(intent).value if get_intent_category(intent) else None,
        "required_slots": REQUIRED_SLOTS.get(intent, []),
        "optional_slots": OPTIONAL_SLOTS.get(intent, []),
        "is_dangerous": is_dangerous_intent(intent),
        "is_system_level": is_system_intent(intent),
    }


# =============================================================================
# INTENT SUGGESTIONS
# =============================================================================

def suggest_intent(text: str) -> List[str]:
    """
    Suggest possible intents based on input text.
    
    This is a fallback for ambiguous inputs.
    """
    text_lower = text.lower()
    suggestions = []
    
    # App control keywords
    if any(word in text_lower for word in ["open", "start", "launch", "run"]):
        suggestions.append("OPEN_APP")
    if any(word in text_lower for word in ["close", "exit", "quit"]):
        suggestions.append("CLOSE_APP")
    if "minimize" in text_lower:
        suggestions.append("MINIMIZE_APP")
    if "maximize" in text_lower:
        suggestions.append("MAXIMIZE_APP")
    if any(word in text_lower for word in ["switch", "alt-tab"]):
        suggestions.append("SWITCH_APP")
    
    # Browser keywords
    if any(word in text_lower for word in ["search", "find", "google", "look for"]):
        suggestions.append("SEARCH_WEB")
    if "url" in text_lower or "http" in text_lower or "www" in text_lower:
        suggestions.append("OPEN_URL")
    if "new tab" in text_lower:
        suggestions.append("NEW_TAB")
    if "close tab" in text_lower:
        suggestions.append("CLOSE_TAB")
    if "refresh" in text_lower or "reload" in text_lower:
        suggestions.append("REFRESH_PAGE")
    
    # Input keywords
    if any(word in text_lower for word in ["type", "write", "enter text"]):
        suggestions.append("TYPE_TEXT")
    if any(word in text_lower for word in ["press", "key", "hotkey", "shortcut"]):
        suggestions.append("PRESS_KEYS")
    if "copy" in text_lower:
        suggestions.append("COPY")
    if "paste" in text_lower:
        suggestions.append("PASTE")
    
    # System keywords
    if any(word in text_lower for word in ["lock", "lock screen"]):
        suggestions.append("LOCK_SCREEN")
    if "volume" in text_lower:
        if "up" in text_lower or "increase" in text_lower:
            suggestions.append("VOLUME_UP")
        elif "down" in text_lower or "decrease" in text_lower:
            suggestions.append("VOLUME_DOWN")
    if "mute" in text_lower:
        suggestions.append("MUTE")
    
    # File keywords
    if any(word in text_lower for word in ["delete", "remove"]) and "file" in text_lower:
        suggestions.append("DELETE_FILE")
    if "create file" in text_lower or "new file" in text_lower:
        suggestions.append("CREATE_FILE")
    
    # UI keywords
    if any(word in text_lower for word in ["click", "tap", "press button"]):
        suggestions.append("CLICK_ELEMENT")
    if "scroll" in text_lower:
        suggestions.append("SCROLL")
    if "wait" in text_lower:
        suggestions.append("WAIT")
    
    # Multi-step detection
    if any(word in text_lower for word in ["and then", "then", "after that", "next"]):
        suggestions.append("MULTI_STEP")
    
    return suggestions


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Categories
    "IntentCategory",
    
    # Intent sets
    "APP_CONTROL_INTENTS",
    "BROWSER_CONTROL_INTENTS",
    "INPUT_CONTROL_INTENTS",
    "SYSTEM_CONTROL_INTENTS",
    "FILE_SYSTEM_INTENTS",
    "UI_VISION_INTENTS",
    "ADVANCED_INTENTS",
    "VALID_INTENTS",
    "DANGEROUS_INTENTS",
    "SYSTEM_LEVEL_INTENTS",
    
    # Slot requirements
    "REQUIRED_SLOTS",
    "OPTIONAL_SLOTS",
    
    # Validation functions
    "is_valid_intent",
    "is_dangerous_intent",
    "is_system_intent",
    "validate_slots",
    "get_intent_info",
    "get_intent_category",
    "suggest_intent",
]
