"""Stage 1.5 — Action-based safety validation (NOT app-based).

CORE PRINCIPLE: Do NOT restrict user freedom.
- OPEN_APP is ALWAYS allowed
- Safety checks ONLY for dangerous behaviors (TYPE_TEXT, PRESS_KEYS)
"""

from __future__ import annotations

from typing import Any
from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# DANGEROUS PATTERNS — Block these in TYPE_TEXT / PRESS_KEYS
# =============================================================================
DANGEROUS_PATTERNS = [
    # Unix destructive commands
    "rm -rf",
    "rm -r",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",  # fork bomb
    
    # Windows destructive commands
    "format",
    "del /s",
    "del /f",
    "rd /s",
    "rmdir /s",
    "shutdown",
    "taskkill /f",
    
    # Registry / system
    "reg delete",
    "regedit",
    
    # Network / security
    "netsh advfirewall",
    "bcdedit",
]

DANGEROUS_KEY_COMBOS = [
    "alt+f4",       # Close window (could close unsaved work)
    "ctrl+alt+del", # System interrupt
    "win+l",        # Lock screen
    "alt+shift+tab",
]


# =============================================================================
# CONFIDENCE THRESHOLD
# =============================================================================
CONFIDENCE_THRESHOLD = 0.7


def is_dangerous_text(text: str) -> bool:
    """Check if text contains dangerous patterns."""
    if not text:
        return False
    
    text_lower = text.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in text_lower:
            logger.warning(f"[SAFETY] Dangerous pattern detected: {pattern}")
            return True
    return False


def is_dangerous_keys(keys: str) -> bool:
    """Check if key combination is dangerous."""
    if not keys:
        return False
    
    keys_lower = keys.lower().replace(" ", "")
    for combo in DANGEROUS_KEY_COMBOS:
        if combo.replace(" ", "") in keys_lower:
            logger.warning(f"[SAFETY] Dangerous key combo detected: {combo}")
            return True
    return False


def validate_confidence(parsed_json: dict) -> tuple[bool, str]:
    """Reject low-confidence outputs."""
    confidence = parsed_json.get("confidence", 0.0)
    
    print(f"\n========== [CONFIDENCE CHECK] ==========")
    print(f"[CONFIDENCE] {confidence}")
    print(f"[THRESHOLD] {CONFIDENCE_THRESHOLD}")
    
    if confidence < CONFIDENCE_THRESHOLD:
        logger.warning(f"[SAFETY] Low confidence rejected: {confidence}")
        print(f"[RESULT] REJECTED - confidence too low")
        return False, "low_confidence"
    
    print(f"[RESULT] PASSED")
    return True, "confidence_ok"


def validate_intent(intent: dict) -> tuple[bool, str]:
    """
    Validate intent for safety.
    
    CORE RULE: OPEN_APP is ALWAYS allowed.
    Only check TYPE_TEXT and PRESS_KEYS for dangerous content.
    """
    intent_type = intent.get("intent", "")
    slots = intent.get("slots", {})
    
    print(f"\n========== [SAFETY CHECK] ==========")
    print(f"[INTENT] {intent_type}")
    print(f"[SLOTS] {slots}")
    
    # OPEN_APP is ALWAYS allowed — DO NOT restrict user freedom
    if intent_type == "OPEN_APP":
        print(f"[RESULT] SAFE - OPEN_APP always allowed")
        logger.info("[SAFETY] OPEN_APP: always allowed")
        return True, "safe"
    
    # OPEN_URL is ALWAYS allowed
    if intent_type == "OPEN_URL":
        print(f"[RESULT] SAFE - OPEN_URL always allowed")
        logger.info("[SAFETY] OPEN_URL: always allowed")
        return True, "safe"
    
    # SEARCH_WEB is ALWAYS allowed
    if intent_type == "SEARCH_WEB":
        print(f"[RESULT] SAFE - SEARCH_WEB always allowed")
        logger.info("[SAFETY] SEARCH_WEB: always allowed")
        return True, "safe"
    
    # TYPE_TEXT — Check for dangerous patterns
    if intent_type == "TYPE_TEXT":
        text = slots.get("text", "")
        if is_dangerous_text(text):
            print(f"[RESULT] BLOCKED - dangerous text pattern")
            return False, "dangerous_text"
        print(f"[RESULT] SAFE - TYPE_TEXT content ok")
        return True, "safe"
    
    # PRESS_KEYS — Check for dangerous combos
    if intent_type == "PRESS_KEYS":
        keys = slots.get("keys", "")
        if is_dangerous_keys(keys):
            print(f"[RESULT] BLOCKED - dangerous key combo")
            return False, "dangerous_keys"
        print(f"[RESULT] SAFE - PRESS_KEYS content ok")
        return True, "safe"
    
    # SCREENSHOT, CLOSE_APP, etc. — allowed by default
    print(f"[RESULT] SAFE - default allow")
    return True, "safe"


def requires_confirmation(intent: dict) -> bool:
    """
    Determine if an intent requires user confirmation.
    
    Confirmation required for:
    - TYPE_TEXT with any content (safety measure)
    - PRESS_KEYS with any content
    - Dangerous patterns (will be blocked anyway, but confirm first)
    """
    intent_type = intent.get("intent", "")
    slots = intent.get("slots", {})
    
    # OPEN_APP never requires confirmation
    if intent_type == "OPEN_APP":
        return False
    
    # OPEN_URL never requires confirmation
    if intent_type == "OPEN_URL":
        return False
    
    # SEARCH_WEB never requires confirmation
    if intent_type == "SEARCH_WEB":
        return False
    
    # TYPE_TEXT with dangerous content requires confirmation
    if intent_type == "TYPE_TEXT":
        text = slots.get("text", "")
        return is_dangerous_text(text)
    
    # PRESS_KEYS with dangerous combos requires confirmation
    if intent_type == "PRESS_KEYS":
        keys = slots.get("keys", "")
        return is_dangerous_keys(keys)
    
    return False


def full_validation(parsed_json: dict) -> tuple[bool, str, dict]:
    """
    Full validation pipeline:
    1. Confidence check
    2. Safety check
    
    Returns: (is_valid, reason, details)
    """
    print(f"\n========== [FULL VALIDATION] ==========")
    
    # Step 1: Confidence check
    conf_ok, conf_reason = validate_confidence(parsed_json)
    if not conf_ok:
        return False, conf_reason, {
            "confidence": parsed_json.get("confidence", 0.0),
            "threshold": CONFIDENCE_THRESHOLD,
        }
    
    # Step 2: Safety check
    safety_ok, safety_reason = validate_intent(parsed_json)
    if not safety_ok:
        return False, safety_reason, {
            "intent": parsed_json.get("intent"),
            "blocked_reason": safety_reason,
        }
    
    print(f"\n[VALIDATION RESULT] PASSED ✓")
    return True, "valid", {}
