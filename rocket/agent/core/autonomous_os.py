"""
PRODUCTION-GRADE AUTONOMOUS AI OPERATING SYSTEM
Stage 6.0 - Deterministic, Safe, UI-Aware Execution System

Architecture:
    PERCEPTION → PRE-SAFETY → INTENT → PLAN → ROUTE → EXECUTE → VERIFY → MEMORY

Core Principles:
- OUTPUT MUST BE STRICT JSON
- NO TEXT, NO EXPLANATION, NO MARKDOWN
- NO GUESSING, NO HALLUCINATION
- USE ONLY ENUM INTENTS
- INVALID → RETURN UNKNOWN
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# INTENT ENUMS - SINGLE SOURCE OF TRUTH
# =============================================================================

class IntentEnum(str, Enum):
    """All supported intents as strict enum values."""
    
    # APP CONTROL (7)
    OPEN_APP = "OPEN_APP"
    CLOSE_APP = "CLOSE_APP"
    MINIMIZE_APP = "MINIMIZE_APP"
    MAXIMIZE_APP = "MAXIMIZE_APP"
    SWITCH_APP = "SWITCH_APP"
    FOCUS_WINDOW = "FOCUS_WINDOW"
    RESTART_APP = "RESTART_APP"
    
    # BROWSER CONTROL (11)
    OPEN_URL = "OPEN_URL"
    SEARCH_WEB = "SEARCH_WEB"
    NEW_TAB = "NEW_TAB"
    CLOSE_TAB = "CLOSE_TAB"
    SWITCH_TAB = "SWITCH_TAB"
    REFRESH_PAGE = "REFRESH_PAGE"
    SCROLL_UP = "SCROLL_UP"
    SCROLL_DOWN = "SCROLL_DOWN"
    GO_BACK = "GO_BACK"
    GO_FORWARD = "GO_FORWARD"
    BOOKMARK_PAGE = "BOOKMARK_PAGE"
    
    # INPUT CONTROL (9)
    TYPE_TEXT = "TYPE_TEXT"
    CLEAR_TEXT = "CLEAR_TEXT"
    SELECT_TEXT = "SELECT_TEXT"
    COPY = "COPY"
    PASTE = "PASTE"
    CUT = "CUT"
    PRESS_KEYS = "PRESS_KEYS"
    UNDO = "UNDO"
    REDO = "REDO"
    
    # SYSTEM CONTROL (10)
    LOCK_SCREEN = "LOCK_SCREEN"
    VOLUME_UP = "VOLUME_UP"
    VOLUME_DOWN = "VOLUME_DOWN"
    MUTE = "MUTE"
    UNMUTE = "UNMUTE"
    BRIGHTNESS_UP = "BRIGHTNESS_UP"
    BRIGHTNESS_DOWN = "BRIGHTNESS_DOWN"
    SHUTDOWN = "SHUTDOWN"
    RESTART_SYSTEM = "RESTART_SYSTEM"
    SLEEP = "SLEEP"
    
    # FILE CONTROL (9)
    OPEN_FILE = "OPEN_FILE"
    DELETE_FILE = "DELETE_FILE"
    CREATE_FILE = "CREATE_FILE"
    MOVE_FILE = "MOVE_FILE"
    RENAME_FILE = "RENAME_FILE"
    CREATE_FOLDER = "CREATE_FOLDER"
    DELETE_FOLDER = "DELETE_FOLDER"
    COPY_FILE = "COPY_FILE"
    PASTE_FILE = "PASTE_FILE"
    
    # UI CONTROL (7)
    CLICK_ELEMENT = "CLICK_ELEMENT"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    RIGHT_CLICK = "RIGHT_CLICK"
    HOVER_ELEMENT = "HOVER_ELEMENT"
    DRAG_AND_DROP = "DRAG_AND_DROP"
    SCROLL = "SCROLL"
    WAIT = "WAIT"
    
    # ADVANCED (4)
    MULTI_STEP = "MULTI_STEP"
    CONDITIONAL = "CONDITIONAL"
    RETRY = "RETRY"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    
    # SPECIAL
    UNKNOWN = "UNKNOWN"


# Intent sets by category
APP_CONTROL_INTENTS: Set[str] = {
    "OPEN_APP", "CLOSE_APP", "MINIMIZE_APP", "MAXIMIZE_APP",
    "SWITCH_APP", "FOCUS_WINDOW", "RESTART_APP"
}

BROWSER_CONTROL_INTENTS: Set[str] = {
    "OPEN_URL", "SEARCH_WEB", "NEW_TAB", "CLOSE_TAB", "SWITCH_TAB",
    "REFRESH_PAGE", "SCROLL_UP", "SCROLL_DOWN", "GO_BACK", "GO_FORWARD",
    "BOOKMARK_PAGE"
}

INPUT_CONTROL_INTENTS: Set[str] = {
    "TYPE_TEXT", "CLEAR_TEXT", "SELECT_TEXT", "COPY", "PASTE",
    "CUT", "PRESS_KEYS", "UNDO", "REDO"
}

SYSTEM_CONTROL_INTENTS: Set[str] = {
    "LOCK_SCREEN", "VOLUME_UP", "VOLUME_DOWN", "MUTE", "UNMUTE",
    "BRIGHTNESS_UP", "BRIGHTNESS_DOWN", "SHUTDOWN", "RESTART_SYSTEM", "SLEEP"
}

FILE_CONTROL_INTENTS: Set[str] = {
    "OPEN_FILE", "DELETE_FILE", "CREATE_FILE", "MOVE_FILE", "RENAME_FILE",
    "CREATE_FOLDER", "DELETE_FOLDER", "COPY_FILE", "PASTE_FILE"
}

UI_CONTROL_INTENTS: Set[str] = {
    "CLICK_ELEMENT", "DOUBLE_CLICK", "RIGHT_CLICK", "HOVER_ELEMENT",
    "DRAG_AND_DROP", "SCROLL", "WAIT"
}

ADVANCED_INTENTS: Set[str] = {
    "MULTI_STEP", "CONDITIONAL", "RETRY", "CONFIRMATION_REQUIRED", "UNKNOWN"
}

ALL_VALID_INTENTS: Set[str] = (
    APP_CONTROL_INTENTS | BROWSER_CONTROL_INTENTS | INPUT_CONTROL_INTENTS |
    SYSTEM_CONTROL_INTENTS | FILE_CONTROL_INTENTS | UI_CONTROL_INTENTS |
    ADVANCED_INTENTS
)


# =============================================================================
# PRE-SAFETY LAYER - MANDATORY BEFORE INTENT CLASSIFICATION
# =============================================================================

DANGEROUS_KEYWORDS: Set[str] = {
    "delete", "remove", "rm", "format", "erase", "wipe",
    "shutdown", "restart system", "reboot", "destroy",
}

SYSTEM_PATH_PATTERNS: List[str] = [
    r"c:\\",
    r"c:/",
    r"/etc/",
    r"/usr/",
    r"/bin/",
    r"/sbin/",
    r"/system/",
    r"/root/",
    r"c:\\windows",
    r"c:\\program files",
    r"c:\\programdata",
    r"system32",
]


def detect_dangerous_operation(input_text: str) -> Tuple[bool, str]:
    """
    PRE-SAFETY: Detect dangerous operations BEFORE intent classification.
    
    Returns:
        (is_dangerous, reason)
    """
    if not input_text:
        return False, ""
    
    text_lower = input_text.lower().strip()
    
    # Check for dangerous keywords
    for keyword in DANGEROUS_KEYWORDS:
        if keyword in text_lower:
            return True, f"dangerous_keyword:{keyword}"
    
    # Check for system paths
    for pattern in SYSTEM_PATH_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True, f"system_path_detected"
    
    return False, ""


def pre_intent_safety_check(input_text: str) -> Optional[Dict[str, Any]]:
    """
    MANDATORY PRE-SAFETY LAYER.
    
    Must run BEFORE intent classification.
    If dangerous operation detected, return CONFIRMATION_REQUIRED immediately.
    """
    is_dangerous, reason = detect_dangerous_operation(input_text)
    
    if is_dangerous:
        return {
            "intent": "CONFIRMATION_REQUIRED",
            "reason": "dangerous_operation",
            "details": reason,
            "original_input": input_text,
            "confidence": 1.0
        }
    
    return None


# =============================================================================
# UI MAPPING ENGINE - KEYBOARD-FIRST AUTOMATION
# =============================================================================

UI_KEYBOARD_MAPPINGS: Dict[str, str] = {
    # Browser navigation
    "search_bar": "Ctrl+L",
    "address_bar": "Ctrl+L",
    "new_tab": "Ctrl+T",
    "close_tab": "Ctrl+W",
    "refresh": "F5",
    "back": "Alt+Left",
    "forward": "Alt+Right",
    "bookmark": "Ctrl+D",
    "find": "Ctrl+F",
    "history": "Ctrl+H",
    "downloads": "Ctrl+J",
    "dev_tools": "F12",
    "full_screen": "F11",
    
    # Text editing
    "select_all": "Ctrl+A",
    "copy": "Ctrl+C",
    "paste": "Ctrl+V",
    "cut": "Ctrl+X",
    "undo": "Ctrl+Z",
    "redo": "Ctrl+Y",
    "save": "Ctrl+S",
    "print": "Ctrl+P",
    
    # Window control
    "minimize": "Win+Down",
    "maximize": "Win+Up",
    "close": "Alt+F4",
    "switch_window": "Alt+Tab",
    "task_view": "Win+Tab",
    "lock": "Win+L",
    
    # System
    "start_menu": "Win",
    "run": "Win+R",
    "settings": "Win+I",
    "file_explorer": "Win+E",
    "screenshot": "Win+Shift+S",
    "clipboard_history": "Win+V",
}


def get_keyboard_shortcut(semantic_target: str) -> Optional[str]:
    """Get keyboard shortcut for a semantic UI target."""
    normalized = semantic_target.lower().strip().replace(" ", "_")
    return UI_KEYBOARD_MAPPINGS.get(normalized)


# =============================================================================
# ZEROCLAW FALLBACK - STRICT RULES
# =============================================================================

ZEROCLAW_UI_KEYWORDS: Set[str] = {
    "click", "tap", "press", "button", "icon", "menu", "dropdown",
    "checkbox", "radio", "slider", "toggle", "link", "image"
}

ZEROCLAW_BLOCKED_INTENTS: Set[str] = FILE_CONTROL_INTENTS | SYSTEM_CONTROL_INTENTS


def should_use_zeroclaw(intent_data: Dict[str, Any], input_text: str) -> bool:
    """
    Determine if ZeroClaw should be used.
    
    ZeroClaw ONLY if:
    - Intent is UNKNOWN
    - Contains UI keywords
    - NOT file/system operations
    """
    intent = intent_data.get("intent", "UNKNOWN")
    
    # Never use ZeroClaw for file/system operations
    if intent in ZEROCLAW_BLOCKED_INTENTS:
        return False
    
    # Only use if intent is UNKNOWN or UI-related
    if intent == "UNKNOWN":
        text_lower = input_text.lower()
        return any(keyword in text_lower for keyword in ZEROCLAW_UI_KEYWORDS)
    
    return False


async def call_zeroclaw(task: str) -> Dict[str, Any]:
    """
    Call ZeroClaw API for UI automation.
    
    API: POST https://openclaw.pollinations.ai/
    """
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openclaw.pollinations.ai/",
                json={"task": task},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "status": "error",
                        "error": f"ZeroClaw returned {response.status}"
                    }
    except Exception as e:
        logger.error(f"[ZEROCLAW] Error: {e}")
        return {"status": "error", "error": str(e)}


# =============================================================================
# CONTEXT MEMORY - SESSION AWARENESS
# =============================================================================

@dataclass
class SessionContext:
    """Track current session state for intelligent execution."""
    
    current_app: Optional[str] = None
    last_action: Optional[str] = None
    last_intent: Optional[str] = None
    browser_active: bool = False
    pending_confirmation: Optional[Dict[str, Any]] = None
    action_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def update(self, intent: str, app: Optional[str] = None) -> None:
        """Update context after action."""
        self.last_intent = intent
        self.last_action = intent
        
        if app:
            self.current_app = app
            # Check if browser
            browsers = ["chrome", "firefox", "edge", "safari", "brave", "opera"]
            self.browser_active = any(b in app.lower() for b in browsers)
        
        self.action_history.append({
            "intent": intent,
            "app": app,
            "timestamp": time.time()
        })
        
        # Limit history
        if len(self.action_history) > 50:
            self.action_history = self.action_history[-50:]
    
    def should_reuse_browser(self) -> bool:
        """Check if we should reuse currently open browser."""
        return self.browser_active and self.current_app is not None
    
    def clear_confirmation(self) -> None:
        """Clear pending confirmation."""
        self.pending_confirmation = None


# Global session context
_session_context: Optional[SessionContext] = None


def get_session_context() -> SessionContext:
    """Get or create session context."""
    global _session_context
    if _session_context is None:
        _session_context = SessionContext()
    return _session_context


def reset_session_context() -> None:
    """Reset session context."""
    global _session_context
    _session_context = SessionContext()


# =============================================================================
# ACCESSIBILITY SYSTEM
# =============================================================================

class AccessibilityMode(Enum):
    """User accessibility modes."""
    NORMAL = "normal"
    VOICE = "voice"      # For blind users
    HAPTIC = "haptic"    # For deaf users
    BRAILLE = "braille"  # For blind users with braille display


@dataclass
class UserAccessibility:
    """User accessibility profile."""
    
    blind: bool = False
    deaf: bool = False
    uses_braille: bool = False
    preferred_mode: AccessibilityMode = AccessibilityMode.NORMAL
    
    def get_confirmation_mode(self) -> str:
        """Get confirmation mode based on user abilities."""
        if self.blind and not self.deaf:
            return "voice"
        elif self.deaf:
            return "haptic"
        elif self.uses_braille:
            return "braille"
        return "ui_prompt"


# Default user accessibility
_user_accessibility = UserAccessibility()


def get_user_accessibility() -> UserAccessibility:
    """Get user accessibility settings."""
    return _user_accessibility


def set_user_accessibility(
    blind: bool = False,
    deaf: bool = False,
    uses_braille: bool = False
) -> None:
    """Set user accessibility settings."""
    global _user_accessibility
    _user_accessibility = UserAccessibility(
        blind=blind,
        deaf=deaf,
        uses_braille=uses_braille
    )


# =============================================================================
# CONFIRMATION SYSTEM
# =============================================================================

TRIPLE_TAP_TIMEOUT = 2.0  # seconds
_tap_timestamps: List[float] = []


def register_tap() -> bool:
    """
    Register a tap for triple-tap confirmation.
    Returns True if triple tap detected.
    """
    global _tap_timestamps
    
    now = time.time()
    
    # Remove old taps
    _tap_timestamps = [t for t in _tap_timestamps if now - t < TRIPLE_TAP_TIMEOUT]
    
    # Add new tap
    _tap_timestamps.append(now)
    
    # Check for triple tap
    if len(_tap_timestamps) >= 3:
        _tap_timestamps.clear()
        return True
    
    return False


def build_confirmation_response(
    original_intent: str,
    original_slots: Dict[str, Any],
    reason: str = "dangerous_operation"
) -> Dict[str, Any]:
    """Build a confirmation required response."""
    accessibility = get_user_accessibility()
    
    return {
        "intent": "CONFIRMATION_REQUIRED",
        "slots": {
            "requires_confirmation": True,
            "reason": reason,
            "original_intent": original_intent,
            "original_slots": original_slots,
            "confirmation_mode": accessibility.get_confirmation_mode()
        },
        "reason": reason,
        "original_intent": original_intent,
        "confidence": 1.0,
        "accessibility": {
            "mode": accessibility.get_confirmation_mode(),
            "blind": accessibility.blind,
            "deaf": accessibility.deaf
        }
    }


# =============================================================================
# TYPE_TEXT SAFETY OVERRIDE
# =============================================================================

def check_type_text_safety_override(intent_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    TYPE_TEXT SAFETY OVERRIDE.
    
    If TYPE_TEXT contains system path → override to DELETE_FILE confirmation.
    """
    if intent_data.get("intent") != "TYPE_TEXT":
        return None
    
    slots = intent_data.get("slots", {})
    text = slots.get("text", "")
    
    if not text:
        return None
    
    # Check for system paths in text
    text_lower = text.lower()
    for pattern in SYSTEM_PATH_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return build_confirmation_response(
                original_intent="DELETE_FILE",
                original_slots={"path": text},
                reason="dangerous_operation"
            )
    
    return None


# =============================================================================
# INTENT CLASSIFICATION ENGINE
# =============================================================================

INTENT_PATTERNS: Dict[str, List[str]] = {
    # App control
    "OPEN_APP": [r"open\s+(\w+)", r"launch\s+(\w+)", r"start\s+(\w+)", r"run\s+(\w+)"],
    "CLOSE_APP": [r"close\s+(\w+)?", r"exit\s+(\w+)?", r"quit\s+(\w+)?"],
    "MINIMIZE_APP": [r"minimize", r"minimize\s+(\w+)"],
    "MAXIMIZE_APP": [r"maximize", r"maximize\s+(\w+)"],
    "SWITCH_APP": [r"switch\s+to\s+(\w+)", r"alt\s*tab"],
    "RESTART_APP": [r"restart\s+(\w+)"],
    
    # Browser
    "OPEN_URL": [r"go\s+to\s+(.+)", r"open\s+(https?://.+)", r"navigate\s+to\s+(.+)"],
    "SEARCH_WEB": [r"search\s+(.+)", r"google\s+(.+)", r"find\s+(.+)"],
    "NEW_TAB": [r"new\s+tab", r"open\s+tab"],
    "CLOSE_TAB": [r"close\s+tab"],
    "REFRESH_PAGE": [r"refresh", r"reload"],
    "GO_BACK": [r"go\s+back", r"back"],
    "GO_FORWARD": [r"go\s+forward", r"forward"],
    "SCROLL_UP": [r"scroll\s+up"],
    "SCROLL_DOWN": [r"scroll\s+down"],
    "BOOKMARK_PAGE": [r"bookmark"],
    
    # Input
    "TYPE_TEXT": [r"type\s+(.+)", r"write\s+(.+)", r"enter\s+(.+)"],
    "COPY": [r"copy"],
    "PASTE": [r"paste"],
    "CUT": [r"cut"],
    "UNDO": [r"undo"],
    "REDO": [r"redo"],
    "SELECT_TEXT": [r"select\s+all", r"select\s+(.+)"],
    "CLEAR_TEXT": [r"clear", r"clear\s+text"],
    "PRESS_KEYS": [r"press\s+(.+)", r"hotkey\s+(.+)"],
    
    # System
    "LOCK_SCREEN": [r"lock\s+screen", r"lock"],
    "SHUTDOWN": [r"shutdown", r"power\s+off", r"turn\s+off"],
    "RESTART_SYSTEM": [r"restart\s+system", r"reboot"],
    "SLEEP": [r"sleep", r"hibernate"],
    "VOLUME_UP": [r"volume\s+up", r"increase\s+volume"],
    "VOLUME_DOWN": [r"volume\s+down", r"decrease\s+volume"],
    "MUTE": [r"mute"],
    "UNMUTE": [r"unmute"],
    "BRIGHTNESS_UP": [r"brightness\s+up", r"brighter"],
    "BRIGHTNESS_DOWN": [r"brightness\s+down", r"dimmer"],
    
    # File
    "OPEN_FILE": [r"open\s+file\s+(.+)"],
    "DELETE_FILE": [r"delete\s+file\s+(.+)", r"remove\s+file\s+(.+)"],
    "CREATE_FILE": [r"create\s+file\s+(.+)", r"new\s+file\s+(.+)"],
    "MOVE_FILE": [r"move\s+(.+)\s+to\s+(.+)"],
    "RENAME_FILE": [r"rename\s+(.+)\s+to\s+(.+)"],
    "CREATE_FOLDER": [r"create\s+folder\s+(.+)", r"new\s+folder\s+(.+)"],
    "DELETE_FOLDER": [r"delete\s+folder\s+(.+)", r"remove\s+folder\s+(.+)"],
    "COPY_FILE": [r"copy\s+file\s+(.+)"],
    "PASTE_FILE": [r"paste\s+file"],
    
    # UI
    "CLICK_ELEMENT": [r"click\s+(.+)", r"tap\s+(.+)", r"press\s+(.+)\s+button"],
    "DOUBLE_CLICK": [r"double\s+click\s+(.+)"],
    "RIGHT_CLICK": [r"right\s+click\s+(.+)"],
    "HOVER_ELEMENT": [r"hover\s+(.+)"],
    "DRAG_AND_DROP": [r"drag\s+(.+)\s+to\s+(.+)"],
    "SCROLL": [r"scroll"],
    "WAIT": [r"wait\s*(\d+)?", r"pause\s*(\d+)?"],
}


def classify_intent(input_text: str) -> Dict[str, Any]:
    """
    Classify input text into an intent.
    
    Returns STRICT JSON output.
    """
    if not input_text or not input_text.strip():
        return {
            "intent": "UNKNOWN",
            "slots": {},
            "confidence": 0.0
        }
    
    text = input_text.lower().strip()
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                slots = extract_slots(intent, match, text)
                return {
                    "intent": intent,
                    "slots": slots,
                    "confidence": 0.9
                }
    
    # No match found
    return {
        "intent": "UNKNOWN",
        "slots": {"raw_input": input_text},
        "confidence": 0.0
    }


def extract_slots(intent: str, match, text: str) -> Dict[str, Any]:
    """Extract slots from regex match."""
    groups = match.groups()
    slots: Dict[str, Any] = {}
    
    if intent == "OPEN_APP" and groups:
        slots["app"] = groups[0]
    elif intent == "CLOSE_APP" and groups and groups[0]:
        slots["app"] = groups[0]
    elif intent in ("SEARCH_WEB", "OPEN_URL") and groups:
        slots["query" if intent == "SEARCH_WEB" else "url"] = groups[0]
    elif intent == "TYPE_TEXT" and groups:
        slots["text"] = groups[0]
    elif intent == "PRESS_KEYS" and groups:
        slots["keys"] = groups[0]
    elif intent in ("DELETE_FILE", "OPEN_FILE", "CREATE_FILE") and groups:
        slots["path"] = groups[0]
    elif intent in ("DELETE_FOLDER", "CREATE_FOLDER") and groups:
        slots["path"] = groups[0]
    elif intent in ("MOVE_FILE", "RENAME_FILE", "DRAG_AND_DROP") and len(groups) >= 2:
        slots["source"] = groups[0]
        slots["destination"] = groups[1]
    elif intent in UI_CONTROL_INTENTS and groups:
        slots["target"] = groups[0]
    elif intent == "WAIT" and groups and groups[0]:
        slots["seconds"] = int(groups[0])
    elif intent in ("MINIMIZE_APP", "MAXIMIZE_APP", "SWITCH_APP", "RESTART_APP") and groups and groups[0]:
        slots["app"] = groups[0]
    
    return slots


# =============================================================================
# MULTI-STEP DETECTION
# =============================================================================

MULTI_STEP_INDICATORS: List[str] = [
    "and then", "then", "after that", "next", "and",
    "followed by", "afterward", "subsequently"
]


def detect_multi_step(input_text: str) -> bool:
    """Detect if input requires multiple steps."""
    text_lower = input_text.lower()
    return any(indicator in text_lower for indicator in MULTI_STEP_INDICATORS)


def parse_multi_step(input_text: str) -> List[str]:
    """Parse multi-step input into individual steps."""
    text = input_text.lower()
    
    # Split by indicators
    for indicator in MULTI_STEP_INDICATORS:
        text = text.replace(indicator, "|")
    
    steps = [s.strip() for s in text.split("|") if s.strip()]
    return steps


def classify_multi_step(input_text: str) -> Dict[str, Any]:
    """
    Classify multi-step input.
    
    RULE: If multiple actions → MUST return MULTI_STEP with ordered steps.
    """
    if not detect_multi_step(input_text):
        return classify_intent(input_text)
    
    step_texts = parse_multi_step(input_text)
    
    if len(step_texts) <= 1:
        return classify_intent(input_text)
    
    steps = []
    for step_text in step_texts:
        step_result = classify_intent(step_text)
        if step_result["intent"] != "UNKNOWN":
            steps.append({
                "intent": step_result["intent"],
                "slots": step_result["slots"]
            })
    
    if not steps:
        return {
            "intent": "UNKNOWN",
            "slots": {"raw_input": input_text},
            "confidence": 0.0
        }
    
    return {
        "intent": "MULTI_STEP",
        "steps": steps,
        "confidence": 0.85
    }


# =============================================================================
# ROUTING ENGINE
# =============================================================================

class ExecutionRoute(Enum):
    """Execution routing destinations."""
    LOCAL = "local"           # Local platform executor
    BACKEND = "backend"       # Backend file executor
    ZEROCLAW = "zeroclaw"     # Vision-based UI automation


def route_intent(intent_data: Dict[str, Any], input_text: str) -> ExecutionRoute:
    """
    Route intent to appropriate executor.
    
    Rules:
    - FILE intent → backend executor
    - UI semantic OR unknown UI → ZeroClaw (ONLY if safe)
    - ELSE → local executor
    """
    intent = intent_data.get("intent", "UNKNOWN")
    
    # File operations → backend
    if intent in FILE_CONTROL_INTENTS:
        return ExecutionRoute.BACKEND
    
    # Check for ZeroClaw fallback
    if should_use_zeroclaw(intent_data, input_text):
        return ExecutionRoute.ZEROCLAW
    
    # Default to local
    return ExecutionRoute.LOCAL


# =============================================================================
# EXECUTION RESULT
# =============================================================================

@dataclass
class ExecutionResult:
    """Standardized execution result."""
    
    status: str  # success | failed | blocked | confirmation_required
    intent: str
    message: str
    confidence: float
    verified: bool = False
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "status": self.status,
            "intent": self.intent,
            "message": self.message,
            "confidence": self.confidence,
            "verified": self.verified
        }
        if self.data:
            result["data"] = self.data
        if self.error_code:
            result["error_code"] = self.error_code
        return result
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# =============================================================================
# MAIN PIPELINE - AUTONOMOUS OS PROCESSOR
# =============================================================================

class AutonomousOSProcessor:
    """
    Production-Grade Autonomous AI Operating System.
    
    Pipeline:
        PERCEPTION → PRE-SAFETY → INTENT → PLAN → ROUTE → EXECUTE → VERIFY → MEMORY
    
    HARD RULES:
    - OUTPUT MUST BE STRICT JSON
    - NO TEXT, NO EXPLANATION, NO MARKDOWN
    - NO GUESSING, NO HALLUCINATION
    - USE ONLY ENUM INTENTS
    - INVALID → RETURN UNKNOWN
    """
    
    def __init__(self):
        self.context = get_session_context()
        self.max_retries = 1
    
    def process(self, input_text: str) -> Dict[str, Any]:
        """
        Main processing pipeline.
        
        Returns STRICT JSON only.
        """
        # STEP 1: PERCEPTION
        if not input_text or not input_text.strip():
            return {"intent": "UNKNOWN", "confidence": 0.0}
        
        # STEP 2: PRE-SAFETY CHECK (MANDATORY)
        safety_result = pre_intent_safety_check(input_text)
        if safety_result:
            # Build an executable confirmation payload so confirm_action can run safely.
            classified = classify_multi_step(input_text)
            original_intent = classified.get("intent", "UNKNOWN")
            original_slots = classified.get("slots", {})

            if original_intent in {"UNKNOWN", "CONFIRMATION_REQUIRED"}:
                original_intent = "UNKNOWN"
                original_slots = {}

            confirmation = build_confirmation_response(
                original_intent=original_intent,
                original_slots=original_slots if isinstance(original_slots, dict) else {},
                reason=safety_result.get("reason", "dangerous_operation"),
            )
            self.context.pending_confirmation = confirmation
            return confirmation
        
        # STEP 3: INTENT CLASSIFICATION
        intent_data = classify_multi_step(input_text)
        
        # STEP 4: TYPE_TEXT SAFETY OVERRIDE
        override = check_type_text_safety_override(intent_data)
        if override:
            self.context.pending_confirmation = override
            return override
        
        # STEP 5: VALIDATE INTENT
        intent = intent_data.get("intent", "UNKNOWN")
        if intent not in ALL_VALID_INTENTS:
            return {"intent": "UNKNOWN", "confidence": 0.0}
        
        # STEP 6: ROUTE
        route = route_intent(intent_data, input_text)
        intent_data["_route"] = route.value
        
        # STEP 7: ENRICH WITH CONTEXT
        if self.context.browser_active and intent in BROWSER_CONTROL_INTENTS:
            intent_data["_context"] = {
                "browser_active": True,
                "current_app": self.context.current_app
            }
        
        return intent_data
    
    async def execute(self, intent_data: Dict[str, Any]) -> ExecutionResult:
        """
        Execute an intent.
        
        Returns ExecutionResult.
        """
        intent = intent_data.get("intent", "UNKNOWN")
        
        # Handle confirmation required
        if intent == "CONFIRMATION_REQUIRED":
            return ExecutionResult(
                status="confirmation_required",
                intent=intent,
                message="Action requires confirmation",
                confidence=1.0,
                data=intent_data.get("slots", {})
            )
        
        # Handle multi-step
        if intent == "MULTI_STEP":
            return await self._execute_multi_step(intent_data)
        
        # Handle unknown
        if intent == "UNKNOWN":
            return ExecutionResult(
                status="failed",
                intent=intent,
                message="Unknown intent",
                confidence=0.0
            )
        
        # Route and execute
        route = ExecutionRoute(intent_data.get("_route", "local"))
        
        try:
            if route == ExecutionRoute.ZEROCLAW:
                result = await self._execute_zeroclaw(intent_data)
            elif route == ExecutionRoute.BACKEND:
                result = await self._execute_backend(intent_data)
            else:
                result = await self._execute_local(intent_data)
            
            # Update context on success
            if result.status == "success":
                app = intent_data.get("slots", {}).get("app")
                self.context.update(intent, app)
            
            return result
            
        except Exception as e:
            logger.error(f"[EXECUTION ERROR] {e}")
            return ExecutionResult(
                status="failed",
                intent=intent,
                message=str(e),
                confidence=0.0,
                error_code="execution_error"
            )
    
    async def _execute_multi_step(self, intent_data: Dict[str, Any]) -> ExecutionResult:
        """Execute multi-step intent."""
        steps = intent_data.get("steps", [])
        results = []
        
        for i, step in enumerate(steps):
            step["_route"] = route_intent(step, "").value
            result = await self.execute(step)
            results.append(result.to_dict())
            
            # STOP on failure
            if result.status != "success":
                return ExecutionResult(
                    status="failed",
                    intent="MULTI_STEP",
                    message=f"Step {i+1} failed: {result.message}",
                    confidence=intent_data.get("confidence", 0.0),
                    data={"completed_steps": i, "results": results}
                )
        
        return ExecutionResult(
            status="success",
            intent="MULTI_STEP",
            message=f"Completed {len(steps)} steps",
            confidence=intent_data.get("confidence", 0.0),
            verified=True,
            data={"steps_completed": len(steps), "results": results}
        )
    
    async def _execute_local(self, intent_data: Dict[str, Any]) -> ExecutionResult:
        """Execute via local platform adapter."""
        from agent.platform.windows import WindowsAdapter
        
        adapter = WindowsAdapter()
        intent = intent_data.get("intent", "")
        slots = intent_data.get("slots", {})
        
        try:
            if intent == "OPEN_APP":
                result = await adapter.open_app(slots.get("app", ""))
            elif intent == "OPEN_URL":
                result = await adapter.open_url(slots.get("url", ""))
            elif intent == "SEARCH_WEB":
                result = await adapter.search_web(slots.get("query", ""))
            elif intent == "TYPE_TEXT":
                result = await adapter.type_text(slots.get("text", ""))
            elif intent == "PRESS_KEYS":
                result = await adapter.press_keys(slots.get("keys", ""))
            elif intent == "CLOSE_APP":
                result = await adapter.close_app(slots.get("app"))
            elif intent == "MINIMIZE_APP":
                result = await adapter.minimize(slots.get("app"))
            elif intent == "MAXIMIZE_APP":
                result = await adapter.maximize(slots.get("app"))
            elif intent == "SCROLL_UP":
                result = await adapter.scroll("up", 3)
            elif intent == "SCROLL_DOWN":
                result = await adapter.scroll("down", 3)
            elif intent in ("NEW_TAB", "CLOSE_TAB", "REFRESH_PAGE", "GO_BACK", "GO_FORWARD"):
                # Browser shortcuts
                shortcut = get_keyboard_shortcut(intent.lower().replace("_", " "))
                if shortcut:
                    result = await adapter.press_keys(shortcut)
                else:
                    result = {"status": "error", "reason": "no_shortcut"}
            elif intent in ("COPY", "PASTE", "CUT", "UNDO", "REDO", "SELECT_TEXT"):
                shortcut = get_keyboard_shortcut(intent.lower())
                if shortcut:
                    result = await adapter.press_keys(shortcut)
                else:
                    result = {"status": "error", "reason": "no_shortcut"}
            else:
                result = {"status": "error", "reason": "unhandled_intent"}
            
            status = result.get("status", "error")
            return ExecutionResult(
                status="success" if status == "success" else "failed",
                intent=intent,
                message=f"{intent} executed",
                confidence=intent_data.get("confidence", 0.0),
                verified=True,
                data=result
            )
            
        except Exception as e:
            return ExecutionResult(
                status="failed",
                intent=intent,
                message=str(e),
                confidence=0.0,
                error_code="execution_error"
            )
    
    async def _execute_backend(self, intent_data: Dict[str, Any]) -> ExecutionResult:
        """Execute via backend file executor."""
        intent = intent_data.get("intent", "")
        slots = intent_data.get("slots", {})
        
        # File operations would go through backend
        # For now, return confirmation required for safety
        return ExecutionResult(
            status="confirmation_required",
            intent=intent,
            message="File operation requires confirmation",
            confidence=1.0,
            data=slots
        )
    
    async def _execute_zeroclaw(self, intent_data: Dict[str, Any]) -> ExecutionResult:
        """Execute via ZeroClaw vision API."""
        slots = intent_data.get("slots", {})
        target = slots.get("target", slots.get("raw_input", ""))
        
        result = await call_zeroclaw(f"Click on {target}")
        
        if result.get("status") == "error":
            return ExecutionResult(
                status="failed",
                intent="CLICK_ELEMENT",
                message=result.get("error", "ZeroClaw failed"),
                confidence=0.0
            )
        
        return ExecutionResult(
            status="success",
            intent="CLICK_ELEMENT",
            message="ZeroClaw executed action",
            confidence=0.8,
            verified=True,
            data=result
        )
    
    def confirm_dangerous_action(self) -> Optional[Dict[str, Any]]:
        """
        Confirm a pending dangerous action.
        
        Returns the original intent if confirmed, None if no pending.
        """
        if not self.context.pending_confirmation:
            return None
        
        confirmed = self.context.pending_confirmation
        original_intent = confirmed.get("original_intent") or confirmed.get("slots", {}).get("original_intent")
        original_slots = confirmed.get("original_slots") or confirmed.get("slots", {}).get("original_slots", {})

        if not original_intent or original_intent == "UNKNOWN":
            return None
        
        self.context.clear_confirmation()
        
        return {
            "intent": original_intent,
            "slots": original_slots,
            "confidence": 1.0,
            "confirmed": True
        }
    
    def handle_triple_tap(self) -> Optional[Dict[str, Any]]:
        """
        Handle triple tap for confirmation.
        
        Returns confirmed intent if triple tap completes confirmation.
        """
        if not self.context.pending_confirmation:
            # Ignore triple tap if no pending confirmation
            return None
        
        if register_tap():
            return self.confirm_dangerous_action()
        
        return None


# =============================================================================
# SINGLETON PROCESSOR
# =============================================================================

_processor_instance: Optional[AutonomousOSProcessor] = None


def get_processor() -> AutonomousOSProcessor:
    """Get singleton processor instance."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = AutonomousOSProcessor()
    return _processor_instance


def reset_processor() -> None:
    """Reset processor instance."""
    global _processor_instance
    _processor_instance = None
    reset_session_context()


# =============================================================================
# PUBLIC API - STRICT JSON OUTPUT
# =============================================================================

def process_input(input_text: str) -> str:
    """
    Process user input and return STRICT JSON.
    
    NO TEXT. NO EXPLANATION. NO MARKDOWN.
    """
    processor = get_processor()
    result = processor.process(input_text)
    return json.dumps(result)


async def execute_intent(intent_json: str) -> str:
    """
    Execute intent from JSON and return STRICT JSON result.
    
    NO TEXT. NO EXPLANATION. NO MARKDOWN.
    """
    processor = get_processor()
    intent_data = json.loads(intent_json)
    result = await processor.execute(intent_data)
    return result.to_json()


def confirm_action() -> str:
    """
    Confirm pending dangerous action.
    
    Returns STRICT JSON.
    """
    processor = get_processor()
    result = processor.confirm_dangerous_action()
    if result:
        return json.dumps(result)
    return json.dumps({"status": "no_pending_confirmation"})


def handle_tap() -> str:
    """
    Handle tap input for triple-tap confirmation.
    
    Returns STRICT JSON.
    """
    processor = get_processor()
    result = processor.handle_triple_tap()
    if result:
        return json.dumps(result)
    return json.dumps({"status": "tap_registered"})


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "IntentEnum",
    "ExecutionRoute",
    "AccessibilityMode",
    
    # Intent sets
    "APP_CONTROL_INTENTS",
    "BROWSER_CONTROL_INTENTS",
    "INPUT_CONTROL_INTENTS",
    "SYSTEM_CONTROL_INTENTS",
    "FILE_CONTROL_INTENTS",
    "UI_CONTROL_INTENTS",
    "ADVANCED_INTENTS",
    "ALL_VALID_INTENTS",
    
    # Safety
    "pre_intent_safety_check",
    "detect_dangerous_operation",
    "check_type_text_safety_override",
    
    # Classification
    "classify_intent",
    "classify_multi_step",
    "route_intent",
    
    # UI Mapping
    "UI_KEYBOARD_MAPPINGS",
    "get_keyboard_shortcut",
    
    # ZeroClaw
    "should_use_zeroclaw",
    "call_zeroclaw",
    
    # Context
    "SessionContext",
    "get_session_context",
    "reset_session_context",
    
    # Accessibility
    "UserAccessibility",
    "get_user_accessibility",
    "set_user_accessibility",
    
    # Confirmation
    "build_confirmation_response",
    "register_tap",
    
    # Processor
    "AutonomousOSProcessor",
    "ExecutionResult",
    "get_processor",
    "reset_processor",
    
    # Public API
    "process_input",
    "execute_intent",
    "confirm_action",
    "handle_tap",
]
