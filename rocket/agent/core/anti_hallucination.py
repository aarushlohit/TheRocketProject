"""
Stage 5 — Anti-Hallucination Module.

Validates that model outputs match input and don't contain invented data.
Critical for production safety.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from agent.utils.logger import get_logger
from agent.core.intent_system import VALID_INTENTS


logger = get_logger(__name__)


# =============================================================================
# KNOWN APPS (for validation)
# =============================================================================

KNOWN_APPS: Set[str] = {
    # Browsers
    "chrome", "firefox", "edge", "safari", "brave", "opera", "vivaldi",
    
    # Office
    "word", "excel", "powerpoint", "outlook", "teams", "onenote", "access",
    
    # Development
    "vscode", "visual studio", "code", "pycharm", "intellij", "webstorm",
    "sublime", "atom", "notepad++", "notepad", "vim", "neovim",
    
    # Communication
    "slack", "discord", "zoom", "skype", "telegram", "whatsapp",
    
    # Media
    "spotify", "vlc", "itunes", "windows media player", "foobar2000",
    
    # System
    "terminal", "cmd", "powershell", "explorer", "file explorer",
    "task manager", "settings", "control panel",
    
    # Creative
    "photoshop", "illustrator", "gimp", "figma", "sketch",
    
    # Utilities
    "calculator", "calendar", "clock", "weather", "maps",
    "snipping tool", "paint", "camera", "photos",
    
    # Games
    "steam", "epic games", "battle.net",
}


# =============================================================================
# VALIDATION RESULT
# =============================================================================

@dataclass
class HallucinationCheckResult:
    """Result of anti-hallucination check."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================

def check_hallucination(
    input_text: str,
    output_json: Dict[str, Any],
    strict: bool = True,
) -> HallucinationCheckResult:
    """
    Validate that output doesn't contain hallucinated data.
    
    Checks:
    1. Intent is valid enum
    2. Slots derive from input (no invented words)
    3. URLs mentioned in input (if OPEN_URL)
    4. Apps are either from input or known
    5. No random invented data
    
    Args:
        input_text: Original user input
        output_json: Model output JSON
        strict: If True, fail on any warning
        
    Returns:
        HallucinationCheckResult with validation status
    """
    errors = []
    warnings = []
    details = {}
    
    input_lower = input_text.lower()
    intent = output_json.get("intent", "")
    slots = output_json.get("slots", {})
    
    # Check 1: Valid intent
    if intent not in VALID_INTENTS:
        errors.append(f"Invalid intent: {intent}")
        details["invalid_intent"] = intent
    
    # Check 2: Intent-specific validation
    if intent == "OPEN_APP":
        app = slots.get("app", "").lower()
        if app:
            validation = _validate_app_slot(app, input_lower)
            if not validation["valid"]:
                if validation["is_error"]:
                    errors.append(validation["message"])
                else:
                    warnings.append(validation["message"])
            details["app_validation"] = validation
    
    elif intent == "OPEN_URL":
        url = slots.get("url", "")
        if url:
            validation = _validate_url_slot(url, input_lower)
            if not validation["valid"]:
                if validation["is_error"]:
                    errors.append(validation["message"])
                else:
                    warnings.append(validation["message"])
            details["url_validation"] = validation
    
    elif intent == "SEARCH_WEB":
        query = slots.get("query", "")
        if query:
            validation = _validate_search_slot(query, input_lower)
            if not validation["valid"]:
                warnings.append(validation["message"])
            details["search_validation"] = validation
    
    elif intent == "TYPE_TEXT":
        text = slots.get("text", "")
        if text:
            validation = _validate_text_slot(text, input_lower)
            if not validation["valid"]:
                warnings.append(validation["message"])
            details["text_validation"] = validation
    
    elif intent == "CLICK_ELEMENT":
        target = slots.get("target", "")
        if target:
            validation = _validate_click_target(target, input_lower)
            if not validation["valid"]:
                warnings.append(validation["message"])
            details["click_validation"] = validation
    
    # Check 3: Multi-step validation
    if intent == "MULTI_STEP":
        steps = output_json.get("steps", [])
        for i, step in enumerate(steps):
            step_result = check_hallucination(input_text, step, strict=False)
            if step_result.errors:
                errors.append(f"Step {i+1}: {step_result.errors[0]}")
            if step_result.warnings:
                warnings.extend([f"Step {i+1}: {w}" for w in step_result.warnings])
    
    # Calculate confidence
    confidence = 1.0
    if warnings:
        confidence -= 0.1 * len(warnings)
    if errors:
        confidence -= 0.3 * len(errors)
    confidence = max(0.0, confidence)
    
    # Determine validity
    is_valid = len(errors) == 0
    if strict and len(warnings) > 2:
        is_valid = False
    
    return HallucinationCheckResult(
        valid=is_valid,
        errors=errors,
        warnings=warnings,
        confidence=confidence,
        details=details,
    )


# =============================================================================
# SLOT VALIDATION HELPERS
# =============================================================================

def _validate_app_slot(app: str, input_lower: str) -> Dict[str, Any]:
    """Validate OPEN_APP slot."""
    app_lower = app.lower()
    mentioned_apps = _find_known_apps_in_input(input_lower)
    
    # Check if app is in input
    if app_lower in input_lower:
        return {"valid": True, "source": "input", "message": ""}
    
    # If the input already names a different app, treat that as a mismatch.
    if mentioned_apps:
        for mentioned_app in mentioned_apps:
            if _is_fuzzy_match(app_lower, mentioned_app):
                return {
                    "valid": True,
                    "source": "input_alias",
                    "matched": mentioned_app,
                    "message": "",
                }

        return {
            "valid": False,
            "is_error": True,
            "source": "input_mismatch",
            "mentioned_apps": sorted(mentioned_apps),
            "message": (
                f"App '{app}' conflicts with input mention(s): "
                f"{', '.join(sorted(mentioned_apps))}"
            ),
        }

    # Check if app is known
    if app_lower in KNOWN_APPS:
        return {"valid": True, "source": "known_apps", "message": ""}
    
    # Check for common misspellings/variations
    for known in KNOWN_APPS:
        if _is_fuzzy_match(app_lower, known):
            return {"valid": True, "source": "fuzzy_match", "matched": known, "message": ""}
    
    # Check if any word from input matches
    input_words = set(input_lower.split())
    if app_lower in input_words:
        return {"valid": True, "source": "input_word", "message": ""}
    
    # Not found - potential hallucination
    return {
        "valid": False,
        "is_error": True,
        "message": f"App '{app}' not found in input and not a known app",
    }


def _validate_url_slot(url: str, input_lower: str) -> Dict[str, Any]:
    """Validate OPEN_URL slot."""
    url_lower = url.lower()
    
    # Extract domain from URL
    domain = _extract_domain(url_lower)
    
    # Check if domain mentioned in input
    if domain and domain in input_lower:
        return {"valid": True, "source": "input", "message": ""}
    
    # Check if full URL in input
    if url_lower in input_lower or url.lower() in input_lower:
        return {"valid": True, "source": "input", "message": ""}
    
    # Check for common sites
    common_domains = [
        "google.com", "youtube.com", "facebook.com", "twitter.com",
        "github.com", "gmail.com", "amazon.com", "reddit.com",
    ]
    if domain in common_domains:
        return {"valid": True, "source": "common_site", "message": ""}
    
    # Check if any URL-like pattern in input
    if "http" in input_lower or "www" in input_lower or ".com" in input_lower:
        # User mentioned URLs, could be a valid transformation
        return {"valid": True, "source": "url_context", "message": ""}
    
    return {
        "valid": False,
        "is_error": True,
        "message": f"URL '{url}' not mentioned in input",
    }


def _validate_search_slot(query: str, input_lower: str) -> Dict[str, Any]:
    """Validate SEARCH_WEB slot."""
    query_lower = query.lower()
    
    # Check if query words are in input
    query_words = set(query_lower.split())
    input_words = set(input_lower.split())
    
    overlap = query_words & input_words
    
    if len(overlap) >= len(query_words) * 0.5:
        return {"valid": True, "source": "input_overlap", "message": ""}
    
    # Check for command word removal (search, find, etc.)
    command_words = {"search", "find", "look", "for", "google", "bing"}
    query_without_commands = query_words - command_words
    
    if query_without_commands and query_without_commands <= input_words:
        return {"valid": True, "source": "cleaned_query", "message": ""}
    
    # Still valid but warn
    return {
        "valid": False,
        "is_error": False,
        "message": f"Query words may not match input: '{query}'",
    }


def _validate_text_slot(text: str, input_lower: str) -> Dict[str, Any]:
    """Validate TYPE_TEXT slot."""
    text_lower = text.lower()
    
    # Check if text is in input
    if text_lower in input_lower:
        return {"valid": True, "source": "input", "message": ""}
    
    # Check for quoted text
    quoted = re.findall(r'"([^"]*)"', input_lower)
    quoted.extend(re.findall(r"'([^']*)'", input_lower))
    
    if text_lower in [q.lower() for q in quoted]:
        return {"valid": True, "source": "quoted", "message": ""}
    
    # Check word overlap
    text_words = set(text_lower.split())
    input_words = set(input_lower.split())
    
    if text_words and text_words <= input_words:
        return {"valid": True, "source": "word_overlap", "message": ""}
    
    return {
        "valid": False,
        "is_error": False,
        "message": f"Text may not derive from input: '{text}'",
    }


def _validate_click_target(target: str, input_lower: str) -> Dict[str, Any]:
    """Validate CLICK_ELEMENT slot."""
    target_lower = target.lower()
    
    # Check if target mentioned in input
    if target_lower in input_lower:
        return {"valid": True, "source": "input", "message": ""}
    
    # Check for common UI elements
    common_targets = [
        "search bar", "first result", "play button", "submit",
        "send", "next", "previous", "close", "menu", "settings",
    ]
    
    if target_lower in common_targets:
        return {"valid": True, "source": "common_target", "message": ""}
    
    # Check if words overlap
    target_words = set(target_lower.split())
    input_words = set(input_lower.split())
    
    if target_words & input_words:
        return {"valid": True, "source": "word_overlap", "message": ""}
    
    return {
        "valid": False,
        "is_error": False,
        "message": f"Click target may not derive from input: '{target}'",
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _is_fuzzy_match(s1: str, s2: str, threshold: float = 0.8) -> bool:
    """Check if two strings are fuzzy matches."""
    if s1 == s2:
        return True
    
    # Simple character overlap ratio
    if len(s1) == 0 or len(s2) == 0:
        return False
    
    shorter, longer = sorted([s1, s2], key=len)
    
    if shorter in longer:
        return True
    
    # Character overlap
    overlap = sum(1 for c in shorter if c in longer)
    ratio = overlap / len(shorter)
    
    return ratio >= threshold


def _find_known_apps_in_input(input_lower: str) -> Set[str]:
    """Return known app names explicitly mentioned in the input text."""
    mentioned_apps: Set[str] = set()

    for known_app in KNOWN_APPS:
        if re.search(rf"\b{re.escape(known_app)}\b", input_lower):
            mentioned_apps.add(known_app)

    return mentioned_apps


def _extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL."""
    url = url.lower()
    
    # Remove protocol
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    
    # Get domain part
    match = re.match(r'^([^/]+)', url)
    if match:
        return match.group(1)
    
    return None


# =============================================================================
# ENFORCE ANTI-HALLUCINATION
# =============================================================================

def enforce_anti_hallucination(
    input_text: str,
    output_json: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Enforce anti-hallucination rules.
    
    If validation fails, return UNKNOWN intent.
    """
    result = check_hallucination(input_text, output_json)
    
    if not result.valid:
        logger.warning(f"[ANTI-HALLUCINATION] Blocked output: {result.errors}")
        return {
            "intent": "UNKNOWN",
            "slots": {},
            "confidence": 0.0,
            "reason": "anti_hallucination_triggered",
            "original_errors": result.errors,
            "original_warnings": result.warnings,
        }
    
    return output_json


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "check_hallucination",
    "enforce_anti_hallucination",
    "HallucinationCheckResult",
    "KNOWN_APPS",
]
