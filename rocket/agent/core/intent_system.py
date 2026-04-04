"""
Stage 5.6 - Full Intent System for the autonomous AI operating system.

This module is the single source of truth for supported intents, categories,
slot requirements, danger classification, and keyword-based suggestions.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set

from agent.utils.logger import get_logger


logger = get_logger(__name__)


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
# APP CONTROL INTENTS (7)
# =============================================================================

APP_CONTROL_INTENTS: Set[str] = {
    "OPEN_APP",
    "CLOSE_APP",
    "MINIMIZE_APP",
    "MAXIMIZE_APP",
    "SWITCH_APP",
    "FOCUS_WINDOW",
    "RESTART_APP",
}


# =============================================================================
# BROWSER CONTROL INTENTS (11)
# =============================================================================

BROWSER_CONTROL_INTENTS: Set[str] = {
    "OPEN_URL",
    "SEARCH_WEB",
    "NEW_TAB",
    "CLOSE_TAB",
    "SWITCH_TAB",
    "REFRESH_PAGE",
    "GO_BACK",
    "GO_FORWARD",
    "BOOKMARK_PAGE",
    "SCROLL_UP",
    "SCROLL_DOWN",
}


# =============================================================================
# INPUT CONTROL INTENTS (9)
# =============================================================================

INPUT_CONTROL_INTENTS: Set[str] = {
    "TYPE_TEXT",
    "CLEAR_TEXT",
    "SELECT_TEXT",
    "COPY",
    "PASTE",
    "CUT",
    "UNDO",
    "REDO",
    "PRESS_KEYS",
}


# =============================================================================
# SYSTEM CONTROL INTENTS (10)
# =============================================================================

SYSTEM_CONTROL_INTENTS: Set[str] = {
    "LOCK_SCREEN",
    "SHUTDOWN",
    "RESTART_SYSTEM",
    "SLEEP",
    "VOLUME_UP",
    "VOLUME_DOWN",
    "MUTE",
    "UNMUTE",
    "BRIGHTNESS_UP",
    "BRIGHTNESS_DOWN",
}


# =============================================================================
# FILE SYSTEM INTENTS (9)
# =============================================================================

FILE_SYSTEM_INTENTS: Set[str] = {
    "OPEN_FILE",
    "DELETE_FILE",
    "CREATE_FILE",
    "MOVE_FILE",
    "RENAME_FILE",
    "COPY_FILE",
    "PASTE_FILE",
    "CREATE_FOLDER",
    "DELETE_FOLDER",
}


# =============================================================================
# UI / VISION CONTROL INTENTS (7)
# =============================================================================

UI_VISION_INTENTS: Set[str] = {
    "CLICK_ELEMENT",
    "DOUBLE_CLICK",
    "RIGHT_CLICK",
    "HOVER_ELEMENT",
    "DRAG_AND_DROP",
    "SCROLL",
    "WAIT",
}


# =============================================================================
# ADVANCED INTENTS (8)
# =============================================================================

ADVANCED_INTENTS: Set[str] = {
    "MULTI_STEP",
    "CONDITIONAL",
    "LOOP",
    "WAIT_FOR_ELEMENT",
    "VERIFY_ELEMENT",
    "RETRY",
    "CONFIRMATION_REQUIRED",
    "UNKNOWN",
}


# =============================================================================
# LEGACY COMPATIBILITY INTENTS (4)
# =============================================================================

LEGACY_COMPAT_INTENTS: Set[str] = {
    "SCREENSHOT",
    "MINIMIZE",
    "MAXIMIZE",
    "CLICK",
}


# =============================================================================
# ALL VALID INTENTS
# =============================================================================

VALID_INTENTS: Set[str] = (
    APP_CONTROL_INTENTS
    | BROWSER_CONTROL_INTENTS
    | INPUT_CONTROL_INTENTS
    | SYSTEM_CONTROL_INTENTS
    | FILE_SYSTEM_INTENTS
    | UI_VISION_INTENTS
    | ADVANCED_INTENTS
    | LEGACY_COMPAT_INTENTS
)


def get_intent_category(intent: str) -> Optional[IntentCategory]:
    """Get the category for an intent."""

    if intent in APP_CONTROL_INTENTS or intent in {"MINIMIZE", "MAXIMIZE"}:
        return IntentCategory.APP_CONTROL
    if intent in BROWSER_CONTROL_INTENTS:
        return IntentCategory.BROWSER_CONTROL
    if intent in INPUT_CONTROL_INTENTS:
        return IntentCategory.INPUT_CONTROL
    if intent in SYSTEM_CONTROL_INTENTS or intent == "SCREENSHOT":
        return IntentCategory.SYSTEM_CONTROL
    if intent in FILE_SYSTEM_INTENTS:
        return IntentCategory.FILE_SYSTEM
    if intent in UI_VISION_INTENTS or intent == "CLICK":
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
    "CLOSE_APP": [],
    "MINIMIZE_APP": [],
    "MAXIMIZE_APP": [],
    "SWITCH_APP": ["app"],
    "FOCUS_WINDOW": ["window"],
    "RESTART_APP": ["app"],

    # Browser control
    "OPEN_URL": ["url"],
    "SEARCH_WEB": ["query"],
    "NEW_TAB": [],
    "CLOSE_TAB": [],
    "SWITCH_TAB": ["tab_index"],
    "REFRESH_PAGE": [],
    "GO_BACK": [],
    "GO_FORWARD": [],
    "BOOKMARK_PAGE": [],
    "SCROLL_UP": [],
    "SCROLL_DOWN": [],

    # Input control
    "TYPE_TEXT": ["text"],
    "CLEAR_TEXT": [],
    "SELECT_TEXT": [],
    "COPY": [],
    "PASTE": [],
    "CUT": [],
    "UNDO": [],
    "REDO": [],
    "PRESS_KEYS": ["keys"],

    # System control
    "LOCK_SCREEN": [],
    "SHUTDOWN": [],
    "RESTART_SYSTEM": [],
    "SLEEP": [],
    "VOLUME_UP": [],
    "VOLUME_DOWN": [],
    "MUTE": [],
    "UNMUTE": [],
    "BRIGHTNESS_UP": [],
    "BRIGHTNESS_DOWN": [],

    # File system
    "OPEN_FILE": ["path"],
    "DELETE_FILE": ["path"],
    "CREATE_FILE": ["path"],
    "MOVE_FILE": ["source", "destination"],
    "RENAME_FILE": ["path", "new_name"],
    "COPY_FILE": ["source"],
    "PASTE_FILE": ["destination"],
    "CREATE_FOLDER": ["path"],
    "DELETE_FOLDER": ["path"],

    # UI / vision
    "CLICK_ELEMENT": ["target"],
    "DOUBLE_CLICK": ["target"],
    "RIGHT_CLICK": ["target"],
    "HOVER_ELEMENT": ["target"],
    "DRAG_AND_DROP": ["source_target", "destination_target"],
    "SCROLL": [],
    "WAIT": [],

    # Advanced
    "MULTI_STEP": ["steps"],
    "CONDITIONAL": [],
    "LOOP": ["steps", "count"],
    "WAIT_FOR_ELEMENT": ["target"],
    "VERIFY_ELEMENT": ["target"],
    "RETRY": [],
    "CONFIRMATION_REQUIRED": [],
    "UNKNOWN": [],

    # Legacy
    "SCREENSHOT": [],
    "MINIMIZE": [],
    "MAXIMIZE": [],
    "CLICK": [],
}


# =============================================================================
# OPTIONAL SLOTS
# =============================================================================

OPTIONAL_SLOTS: Dict[str, List[str]] = {
    "OPEN_APP": ["arguments"],
    "CLOSE_APP": ["app"],
    "MINIMIZE_APP": ["app"],
    "MAXIMIZE_APP": ["app"],
    "FOCUS_WINDOW": ["app"],
    "RESTART_APP": ["arguments"],
    "SWITCH_TAB": [],
    "TYPE_TEXT": ["target"],
    "PRESS_KEYS": ["count"],
    "WAIT": ["seconds", "condition"],
    "CLICK_ELEMENT": ["action"],
    "DOUBLE_CLICK": ["button"],
    "RIGHT_CLICK": ["button"],
    "HOVER_ELEMENT": ["duration_ms"],
    "DRAG_AND_DROP": ["hold_ms"],
    "SCROLL": ["direction", "amount", "target"],
    "OPEN_FILE": ["application"],
    "CREATE_FILE": ["content"],
    "COPY_FILE": ["destination"],
    "PASTE_FILE": ["source"],
    "CREATE_FOLDER": ["parents"],
    "DELETE_FOLDER": ["recursive"],
    "VERIFY_ELEMENT": ["state"],
    "RETRY": ["step", "max_attempts"],
    "CONFIRMATION_REQUIRED": ["reason", "original_intent", "original_slots"],
}


# =============================================================================
# DANGEROUS INTENTS
# =============================================================================

DANGEROUS_INTENTS: Set[str] = {
    "DELETE_FILE",
    "DELETE_FOLDER",
    "LOCK_SCREEN",
    "SHUTDOWN",
    "RESTART_SYSTEM",
    "SLEEP",
    "CLOSE_APP",
    "RESTART_APP",
}


# =============================================================================
# SYSTEM-LEVEL INTENTS
# =============================================================================

SYSTEM_LEVEL_INTENTS: Set[str] = {
    "LOCK_SCREEN",
    "SHUTDOWN",
    "RESTART_SYSTEM",
    "SLEEP",
    "VOLUME_UP",
    "VOLUME_DOWN",
    "MUTE",
    "UNMUTE",
    "BRIGHTNESS_UP",
    "BRIGHTNESS_DOWN",
    "SCREENSHOT",
}


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
    """Validate that required slots are present."""

    required = REQUIRED_SLOTS.get(intent, [])
    missing = [slot for slot in required if slot not in slots or not slots[slot]]
    return len(missing) == 0, missing


def get_intent_info(intent: str) -> Dict[str, Any]:
    """Get full information about an intent."""

    if intent not in VALID_INTENTS:
        return {"valid": False, "error": "Unknown intent"}

    category = get_intent_category(intent)
    return {
        "valid": True,
        "intent": intent,
        "category": category.value if category else None,
        "required_slots": REQUIRED_SLOTS.get(intent, []),
        "optional_slots": OPTIONAL_SLOTS.get(intent, []),
        "is_dangerous": is_dangerous_intent(intent),
        "is_system_level": is_system_intent(intent),
    }


def suggest_intent(text: str) -> List[str]:
    """Suggest possible intents based on input text."""

    text_lower = text.lower()
    suggestions: List[str] = []

    # App control keywords
    if any(word in text_lower for word in ["open", "start", "launch", "run"]):
        suggestions.append("OPEN_APP")
    if any(word in text_lower for word in ["close", "exit", "quit"]):
        suggestions.append("CLOSE_APP")
    if "restart app" in text_lower or "reopen" in text_lower:
        suggestions.append("RESTART_APP")
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
    if "go back" in text_lower or "back page" in text_lower:
        suggestions.append("GO_BACK")
    if "go forward" in text_lower or "forward page" in text_lower:
        suggestions.append("GO_FORWARD")
    if "bookmark" in text_lower:
        suggestions.append("BOOKMARK_PAGE")

    # Input keywords
    if any(word in text_lower for word in ["type", "write", "enter text"]):
        suggestions.append("TYPE_TEXT")
    if any(word in text_lower for word in ["press", "key", "hotkey", "shortcut"]):
        suggestions.append("PRESS_KEYS")
    if "copy" in text_lower:
        suggestions.append("COPY")
    if "paste" in text_lower:
        suggestions.append("PASTE")
    if "undo" in text_lower:
        suggestions.append("UNDO")
    if "redo" in text_lower:
        suggestions.append("REDO")

    # System keywords
    if any(word in text_lower for word in ["lock", "lock screen"]):
        suggestions.append("LOCK_SCREEN")
    if any(word in text_lower for word in ["shutdown", "power off"]):
        suggestions.append("SHUTDOWN")
    if any(word in text_lower for word in ["restart system", "reboot"]):
        suggestions.append("RESTART_SYSTEM")
    if "sleep" in text_lower:
        suggestions.append("SLEEP")
    if "volume" in text_lower:
        if "up" in text_lower or "increase" in text_lower:
            suggestions.append("VOLUME_UP")
        elif "down" in text_lower or "decrease" in text_lower:
            suggestions.append("VOLUME_DOWN")
    if "mute" in text_lower and "unmute" not in text_lower:
        suggestions.append("MUTE")
    if "unmute" in text_lower:
        suggestions.append("UNMUTE")

    # File keywords
    if any(word in text_lower for word in ["delete", "remove"]) and "file" in text_lower:
        suggestions.append("DELETE_FILE")
    if any(word in text_lower for word in ["delete", "remove"]) and any(
        word in text_lower for word in ["folder", "directory"]
    ):
        suggestions.append("DELETE_FOLDER")
    if "create file" in text_lower or "new file" in text_lower:
        suggestions.append("CREATE_FILE")
    if "create folder" in text_lower or "new folder" in text_lower:
        suggestions.append("CREATE_FOLDER")
    if "copy file" in text_lower:
        suggestions.append("COPY_FILE")
    if "paste file" in text_lower:
        suggestions.append("PASTE_FILE")

    # UI keywords
    if any(word in text_lower for word in ["click", "tap", "press button"]):
        suggestions.append("CLICK_ELEMENT")
    if "double click" in text_lower:
        suggestions.append("DOUBLE_CLICK")
    if "right click" in text_lower:
        suggestions.append("RIGHT_CLICK")
    if "hover" in text_lower:
        suggestions.append("HOVER_ELEMENT")
    if "drag" in text_lower and "drop" in text_lower:
        suggestions.append("DRAG_AND_DROP")
    if "scroll" in text_lower:
        suggestions.append("SCROLL")
    if "wait" in text_lower:
        suggestions.append("WAIT")

    # Advanced keywords
    if any(word in text_lower for word in ["and then", "then", "after that", "next"]):
        suggestions.append("MULTI_STEP")
    if "retry" in text_lower:
        suggestions.append("RETRY")

    return suggestions


__all__ = [
    "IntentCategory",
    "APP_CONTROL_INTENTS",
    "BROWSER_CONTROL_INTENTS",
    "INPUT_CONTROL_INTENTS",
    "SYSTEM_CONTROL_INTENTS",
    "FILE_SYSTEM_INTENTS",
    "UI_VISION_INTENTS",
    "ADVANCED_INTENTS",
    "LEGACY_COMPAT_INTENTS",
    "VALID_INTENTS",
    "DANGEROUS_INTENTS",
    "SYSTEM_LEVEL_INTENTS",
    "REQUIRED_SLOTS",
    "OPTIONAL_SLOTS",
    "is_valid_intent",
    "is_dangerous_intent",
    "is_system_intent",
    "validate_slots",
    "get_intent_info",
    "get_intent_category",
    "suggest_intent",
]
