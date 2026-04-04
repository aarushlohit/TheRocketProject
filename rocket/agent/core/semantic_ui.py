"""
Stage 5 — Semantic UI Interaction System.

Enables human-like UI interaction using semantic targets instead of coordinates.
The Vision Agent identifies and interacts with UI elements by name/description.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# SEMANTIC TARGET CATEGORIES
# =============================================================================

@dataclass
class SemanticTarget:
    """A semantic UI target."""
    name: str
    category: str
    aliases: List[str]
    priority: int = 1  # Higher = more specific


# =============================================================================
# NAVIGATION ELEMENTS
# =============================================================================

NAVIGATION_TARGETS: List[SemanticTarget] = [
    SemanticTarget("search bar", "navigation", ["search field", "search box", "search input"], 2),
    SemanticTarget("address bar", "navigation", ["url bar", "location bar", "omnibox"], 2),
    SemanticTarget("back button", "navigation", ["go back", "previous page"], 2),
    SemanticTarget("forward button", "navigation", ["go forward", "next page"], 2),
    SemanticTarget("refresh button", "navigation", ["reload", "refresh page"], 2),
    SemanticTarget("home button", "navigation", ["go home", "homepage"], 2),
    SemanticTarget("menu", "navigation", ["hamburger menu", "three lines", "menu icon"], 2),
    SemanticTarget("navigation bar", "navigation", ["navbar", "nav bar", "top bar"], 1),
    SemanticTarget("sidebar", "navigation", ["side panel", "left panel", "right panel"], 1),
]


# =============================================================================
# RESULT ELEMENTS
# =============================================================================

RESULT_TARGETS: List[SemanticTarget] = [
    SemanticTarget("first result", "results", ["result 1", "top result", "first link"], 3),
    SemanticTarget("second result", "results", ["result 2", "second link"], 3),
    SemanticTarget("third result", "results", ["result 3", "third link"], 3),
    SemanticTarget("fourth result", "results", ["result 4"], 3),
    SemanticTarget("fifth result", "results", ["result 5"], 3),
    SemanticTarget("main content", "results", ["content area", "main area", "body"], 1),
    SemanticTarget("footer", "results", ["page footer", "bottom"], 1),
]


# =============================================================================
# ACTION ELEMENTS
# =============================================================================

ACTION_TARGETS: List[SemanticTarget] = [
    SemanticTarget("play button", "action", ["play", "start playback"], 3),
    SemanticTarget("pause button", "action", ["pause", "stop playback"], 3),
    SemanticTarget("stop button", "action", ["stop"], 3),
    SemanticTarget("submit button", "action", ["submit", "send", "go"], 2),
    SemanticTarget("cancel button", "action", ["cancel", "close", "dismiss"], 2),
    SemanticTarget("login button", "action", ["sign in", "log in"], 2),
    SemanticTarget("signup button", "action", ["sign up", "register", "create account"], 2),
    SemanticTarget("logout button", "action", ["sign out", "log out"], 2),
    SemanticTarget("download button", "action", ["download", "save"], 2),
    SemanticTarget("upload button", "action", ["upload", "attach"], 2),
    SemanticTarget("next button", "action", ["next", "continue", "forward"], 2),
    SemanticTarget("previous button", "action", ["prev", "back", "previous"], 2),
    SemanticTarget("close button", "action", ["x button", "dismiss", "close"], 2),
]


# =============================================================================
# FORM ELEMENTS
# =============================================================================

FORM_TARGETS: List[SemanticTarget] = [
    SemanticTarget("text field", "form", ["input field", "text input", "text box"], 2),
    SemanticTarget("password field", "form", ["password input", "password box"], 2),
    SemanticTarget("email field", "form", ["email input", "email box"], 2),
    SemanticTarget("dropdown", "form", ["select", "dropdown menu", "combo box"], 2),
    SemanticTarget("checkbox", "form", ["check box", "tick box"], 2),
    SemanticTarget("radio button", "form", ["radio", "option button"], 2),
    SemanticTarget("textarea", "form", ["text area", "multiline input", "comment box"], 2),
    SemanticTarget("date picker", "form", ["calendar", "date input"], 2),
]


# =============================================================================
# MEDIA ELEMENTS
# =============================================================================

MEDIA_TARGETS: List[SemanticTarget] = [
    SemanticTarget("video player", "media", ["video", "player"], 2),
    SemanticTarget("audio player", "media", ["audio", "music player"], 2),
    SemanticTarget("image", "media", ["picture", "photo", "thumbnail"], 1),
    SemanticTarget("fullscreen button", "media", ["maximize video", "full screen"], 2),
    SemanticTarget("volume slider", "media", ["volume control", "audio slider"], 2),
    SemanticTarget("progress bar", "media", ["seek bar", "timeline", "scrubber"], 2),
]


# =============================================================================
# TAB/WINDOW ELEMENTS
# =============================================================================

TAB_TARGETS: List[SemanticTarget] = [
    SemanticTarget("first tab", "tabs", ["tab 1", "leftmost tab"], 3),
    SemanticTarget("second tab", "tabs", ["tab 2"], 3),
    SemanticTarget("third tab", "tabs", ["tab 3"], 3),
    SemanticTarget("last tab", "tabs", ["rightmost tab", "final tab"], 3),
    SemanticTarget("new tab button", "tabs", ["add tab", "plus tab", "+"], 2),
    SemanticTarget("close tab button", "tabs", ["x tab", "close this tab"], 2),
]


# =============================================================================
# ALL SEMANTIC TARGETS
# =============================================================================

ALL_SEMANTIC_TARGETS: List[SemanticTarget] = (
    NAVIGATION_TARGETS +
    RESULT_TARGETS +
    ACTION_TARGETS +
    FORM_TARGETS +
    MEDIA_TARGETS +
    TAB_TARGETS
)

# Quick lookup set
VALID_TARGETS: Set[str] = {t.name for t in ALL_SEMANTIC_TARGETS}

# Alias mapping
TARGET_ALIASES: Dict[str, str] = {}
for target in ALL_SEMANTIC_TARGETS:
    for alias in target.aliases:
        TARGET_ALIASES[alias.lower()] = target.name


# =============================================================================
# TARGET RESOLUTION
# =============================================================================

def normalize_target(target: str) -> Optional[str]:
    """
    Normalize a target description to a valid semantic target.
    
    Args:
        target: User-provided target description
        
    Returns:
        Normalized semantic target name, or None if invalid
    """
    if not target:
        return None
    
    target_lower = target.lower().strip()
    
    # Direct match
    if target_lower in VALID_TARGETS:
        return target_lower
    
    # Check aliases
    if target_lower in TARGET_ALIASES:
        return TARGET_ALIASES[target_lower]
    
    # Fuzzy match - check if target contains a known target
    for known_target in VALID_TARGETS:
        if known_target in target_lower or target_lower in known_target:
            return known_target
    
    # Check if any alias is contained
    for alias, canonical in TARGET_ALIASES.items():
        if alias in target_lower or target_lower in alias:
            return canonical
    
    logger.warning(f"[SEMANTIC UI] Could not normalize target: {target}")
    return target_lower  # Return as-is for vision model to interpret


def is_valid_semantic_target(target: str) -> bool:
    """Check if target is a known semantic target."""
    if not target:
        return False
    
    normalized = normalize_target(target)
    return normalized in VALID_TARGETS


def get_target_info(target: str) -> Optional[SemanticTarget]:
    """Get full information about a semantic target."""
    normalized = normalize_target(target)
    if not normalized:
        return None
    
    for t in ALL_SEMANTIC_TARGETS:
        if t.name == normalized:
            return t
    
    return None


def get_targets_by_category(category: str) -> List[SemanticTarget]:
    """Get all targets in a category."""
    return [t for t in ALL_SEMANTIC_TARGETS if t.category == category]


# =============================================================================
# CLICK ACTION TYPES
# =============================================================================

class ClickAction:
    """Types of click actions."""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    HOVER = "hover"
    LONG_PRESS = "long_press"


VALID_CLICK_ACTIONS: Set[str] = {
    ClickAction.CLICK,
    ClickAction.DOUBLE_CLICK,
    ClickAction.RIGHT_CLICK,
    ClickAction.HOVER,
    ClickAction.LONG_PRESS,
}


def normalize_click_action(action: str) -> str:
    """Normalize click action to valid enum."""
    if not action:
        return ClickAction.CLICK
    
    action_lower = action.lower().strip()
    
    if action_lower in VALID_CLICK_ACTIONS:
        return action_lower
    
    # Aliases
    if action_lower in ["double", "double-click", "dblclick"]:
        return ClickAction.DOUBLE_CLICK
    if action_lower in ["right", "right-click", "context"]:
        return ClickAction.RIGHT_CLICK
    if action_lower in ["hover", "mouseover", "mouse over"]:
        return ClickAction.HOVER
    if action_lower in ["long", "long-press", "hold"]:
        return ClickAction.LONG_PRESS
    
    return ClickAction.CLICK


# =============================================================================
# SEMANTIC TARGET EXTRACTION
# =============================================================================

def extract_target_from_text(text: str) -> Optional[str]:
    """
    Extract a semantic target from natural language text.
    
    Examples:
        "click on the play button" → "play button"
        "click search bar" → "search bar"
        "tap the first result" → "first result"
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Try to find known targets in the text
    found_targets = []
    
    for target in ALL_SEMANTIC_TARGETS:
        # Check main name
        if target.name in text_lower:
            found_targets.append((target, target.priority, len(target.name)))
        
        # Check aliases
        for alias in target.aliases:
            if alias in text_lower:
                found_targets.append((target, target.priority, len(alias)))
    
    if not found_targets:
        # Fallback: extract noun phrase after "click", "tap", etc.
        patterns = [
            r"click\s+(?:on\s+)?(?:the\s+)?(.+)",
            r"tap\s+(?:on\s+)?(?:the\s+)?(.+)",
            r"press\s+(?:the\s+)?(.+?)(?:\s+button)?",
            r"select\s+(?:the\s+)?(.+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1).strip()
        
        return None
    
    # Sort by priority (higher first), then by length (longer match first)
    found_targets.sort(key=lambda x: (-x[1], -x[2]))
    
    return found_targets[0][0].name


# =============================================================================
# BUILD CLICK ELEMENT INTENT
# =============================================================================

def build_click_intent(
    target: str,
    action: str = ClickAction.CLICK,
    confidence: float = 0.9,
) -> Dict[str, Any]:
    """
    Build a CLICK_ELEMENT intent.
    
    Args:
        target: Semantic target to click
        action: Click action type
        confidence: Confidence score
        
    Returns:
        Intent dictionary
    """
    normalized_target = normalize_target(target) or target
    normalized_action = normalize_click_action(action)
    
    return {
        "intent": "CLICK_ELEMENT",
        "slots": {
            "target": normalized_target,
            "action": normalized_action,
        },
        "confidence": confidence,
    }


# =============================================================================
# SCROLL DIRECTION
# =============================================================================

class ScrollDirection:
    """Scroll directions."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


def parse_scroll_direction(text: str) -> str:
    """Parse scroll direction from text."""
    text_lower = text.lower()
    
    if "up" in text_lower:
        return ScrollDirection.UP
    if "down" in text_lower:
        return ScrollDirection.DOWN
    if "left" in text_lower:
        return ScrollDirection.LEFT
    if "right" in text_lower:
        return ScrollDirection.RIGHT
    
    return ScrollDirection.DOWN  # Default


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Data classes
    "SemanticTarget",
    
    # Target collections
    "NAVIGATION_TARGETS",
    "RESULT_TARGETS",
    "ACTION_TARGETS",
    "FORM_TARGETS",
    "MEDIA_TARGETS",
    "TAB_TARGETS",
    "ALL_SEMANTIC_TARGETS",
    "VALID_TARGETS",
    "TARGET_ALIASES",
    
    # Target functions
    "normalize_target",
    "is_valid_semantic_target",
    "get_target_info",
    "get_targets_by_category",
    "extract_target_from_text",
    
    # Click actions
    "ClickAction",
    "VALID_CLICK_ACTIONS",
    "normalize_click_action",
    "build_click_intent",
    
    # Scroll
    "ScrollDirection",
    "parse_scroll_direction",
]
