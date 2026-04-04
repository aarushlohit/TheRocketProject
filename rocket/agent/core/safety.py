"""Stage 5.6 - Safety-first validation and confirmation system.

Safety priority order:
1. Pre-intent safety filter
2. Intent classification / normalization
3. Execution

This module centralizes danger detection, system-path interception, and
accessibility-aware confirmation payloads.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from agent.core.intent_system import DANGEROUS_INTENTS as INTENT_SYSTEM_DANGEROUS
from agent.core.user_profile import UserProfile, get_or_create_profile
from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# DANGEROUS PATTERNS
# =============================================================================

DANGEROUS_PATTERNS = [
    # Unix destructive commands
    "rm -rf",
    "rm -r",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",
    "chmod 777",
    "chmod -r 777",
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
    "bcdedit",
    # Script execution / injection
    "powershell -e",
    "powershell -enc",
    "cmd /c",
    "curl | bash",
    "wget | bash",
    "curl | sh",
    "wget | sh",
    "invoke-expression",
    "iex(",
    # Explicit destructive language
    "delete",
    "remove",
    "erase",
    "wipe",
]

DANGEROUS_KEY_COMBOS = [
    "alt+f4",
    "ctrl+alt+del",
    "win+l",
    "alt+shift+tab",
]

PRE_INTENT_DANGEROUS_KEYWORDS = [
    "delete",
    "remove",
    "rm ",
    "format",
    "erase",
    "wipe",
    "shutdown",
    "restart system",
    "reboot",
    "lock screen",
    "sleep",
]

FILE_OPERATION_KEYWORDS = [
    "open file",
    "delete",
    "remove",
    "move",
    "rename",
    "copy file",
    "paste file",
    "create file",
    "create folder",
    "delete folder",
]

SYSTEM_PATH_TOKENS = [
    "c:\\windows",
    "c:\\program files",
    "c:\\programdata",
    "c:\\users\\public",
    "system32",
    "/etc/",
    "/usr/",
    "/bin/",
    "/sbin/",
    "/system/",
    "/root/",
]


# =============================================================================
# CONFIDENCE THRESHOLD
# =============================================================================

CONFIDENCE_THRESHOLD = 0.7


# =============================================================================
# DANGEROUS INTENTS
# =============================================================================

DANGEROUS_INTENTS = set(INTENT_SYSTEM_DANGEROUS) | {
    "MOVE_FILE",
    "RENAME_FILE",
}


# =============================================================================
# ACCESSIBILITY HELPERS
# =============================================================================

def _resolve_profile(user_profile: Optional[UserProfile] = None) -> UserProfile:
    """Resolve user profile with a safe default."""

    return user_profile or get_or_create_profile()


def get_confirmation_accessibility(
    user_profile: Optional[UserProfile] = None,
) -> Dict[str, Any]:
    """Build accessibility metadata for confirmation flows."""

    profile = _resolve_profile(user_profile)
    modes = profile.get_all_feedback_modes()

    if profile.uses_braille:
        primary_mode = "braille"
    elif profile.blind and profile.can_hear:
        primary_mode = "voice"
    elif profile.deaf or not profile.can_hear:
        primary_mode = "haptic"
    else:
        primary_mode = profile.get_feedback_mode()

    return {
        "mode": primary_mode,
        "modes": modes,
        "blind": profile.blind,
        "deaf": profile.deaf,
        "uses_braille": profile.uses_braille,
    }


# =============================================================================
# PATH / TEXT DETECTION
# =============================================================================

def is_system_path(path: Optional[str]) -> bool:
    """Check whether a path targets a sensitive system location."""

    if not path:
        return False

    path_lower = str(path).strip().lower().replace("/", "\\")
    normalized_tokens = [token.replace("/", "\\") for token in SYSTEM_PATH_TOKENS]

    if any(token in path_lower for token in normalized_tokens):
        return True

    if re.search(r"\b[a-z]:\\windows\\", path_lower):
        return True

    return False


def contains_system_path(text: Optional[str]) -> bool:
    """Detect whether free-form text references a system path."""

    if not text:
        return False

    text_lower = text.lower()
    if any(token in text_lower for token in SYSTEM_PATH_TOKENS):
        return True

    return bool(
        re.search(r"\b[a-z]:\\(?:windows|program files|programdata|users\\public)", text_lower)
    )


def is_dangerous_text(text: Optional[str]) -> bool:
    """Check if text contains dangerous patterns."""

    if not text:
        return False

    text_lower = str(text).lower()

    if re.search(r"\b(curl|wget)\b.+\|\s*(bash|sh)\b", text_lower):
        logger.warning("[SAFETY] Dangerous download-and-execute pattern detected")
        return True

    if contains_system_path(text_lower) and any(
        keyword in text_lower for keyword in PRE_INTENT_DANGEROUS_KEYWORDS
    ):
        logger.warning("[SAFETY] Dangerous text references sensitive system path")
        return True

    for pattern in DANGEROUS_PATTERNS:
        if pattern in text_lower:
            logger.warning(f"[SAFETY] Dangerous pattern detected: {pattern}")
            return True

    return False


def is_dangerous_keys(keys: Optional[str]) -> bool:
    """Check if key combination is dangerous."""

    if not keys:
        return False

    keys_lower = str(keys).lower().replace(" ", "")
    for combo in DANGEROUS_KEY_COMBOS:
        if combo.replace(" ", "") in keys_lower:
            logger.warning(f"[SAFETY] Dangerous key combo detected: {combo}")
            return True

    return False


def infer_raw_intent(input_text: Optional[str]) -> Optional[str]:
    """Infer a dangerous high-level intent from raw input before classification."""

    if not input_text:
        return None

    text_lower = input_text.lower()

    if any(term in text_lower for term in ["shutdown", "power off"]):
        return "SHUTDOWN"
    if any(term in text_lower for term in ["restart system", "reboot"]):
        return "RESTART_SYSTEM"
    if "lock screen" in text_lower:
        return "LOCK_SCREEN"
    if "sleep" in text_lower:
        return "SLEEP"
    if any(term in text_lower for term in ["delete folder", "remove folder", "delete directory", "remove directory"]):
        return "DELETE_FOLDER"
    if any(term in text_lower for term in ["delete", "remove", "rm ", "format", "erase", "wipe"]):
        return "DELETE_FILE"

    if contains_system_path(text_lower) and any(term in text_lower for term in FILE_OPERATION_KEYWORDS):
        return "DELETE_FILE"

    return None


# =============================================================================
# CONFIRMATION PAYLOADS
# =============================================================================

def build_confirmation_response(
    intent: Dict[str, Any],
    *,
    reason: str = "dangerous_operation",
    user_profile: Optional[UserProfile] = None,
    original_intent: Optional[str] = None,
    original_slots: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a deterministic confirmation-required payload."""

    accessibility = get_confirmation_accessibility(user_profile)
    resolved_original_intent = original_intent or intent.get("intent", "UNKNOWN")
    resolved_original_slots = original_slots or intent.get("slots", {})
    extra = metadata or {}

    slots = {
        "requires_confirmation": True,
        "reason": reason,
        "original_intent": resolved_original_intent,
        "original_slots": resolved_original_slots,
        "confirmation_mode": accessibility["mode"],
        "confirmation_modes": accessibility["modes"],
        "accessibility": accessibility,
    }
    slots.update(extra)

    return {
        "intent": "CONFIRMATION_REQUIRED",
        "slots": slots,
        "reason": reason,
        "original_intent": resolved_original_intent,
        "confidence": 1.0,
        "confirmation_mode": accessibility["mode"],
        "confirmation_modes": accessibility["modes"],
        "accessibility": accessibility,
    }


# =============================================================================
# PRE-INTENT SAFETY
# =============================================================================

def pre_intent_safety_check(
    input_text: Optional[str],
    user_profile: Optional[UserProfile] = None,
) -> Optional[Dict[str, Any]]:
    """Run mandatory safety interception before intent classification."""

    if not input_text:
        return None

    raw_intent = infer_raw_intent(input_text)
    if raw_intent is None:
        return None

    return build_confirmation_response(
        {"intent": raw_intent, "slots": {}},
        reason="dangerous_operation",
        user_profile=user_profile,
        original_intent=raw_intent,
        metadata={"input_text": input_text},
    )


def override_type_text_misuse(
    intent: Dict[str, Any],
    user_profile: Optional[UserProfile] = None,
) -> Optional[Dict[str, Any]]:
    """Override dangerous TYPE_TEXT usage into a confirmation-required delete action."""

    if intent.get("intent") != "TYPE_TEXT":
        return None

    slots = intent.get("slots", {})
    text = slots.get("text", "")
    if not text:
        return None

    if is_dangerous_text(text) or contains_system_path(text):
        return build_confirmation_response(
            intent,
            reason="dangerous_operation",
            user_profile=user_profile,
            original_intent="DELETE_FILE",
            original_slots={"path": text},
            metadata={
                "safety_override_from": "TYPE_TEXT",
                "typed_text": text,
            },
        )

    return None


# =============================================================================
# CONFIRMATION / VALIDATION
# =============================================================================

def validate_confidence(parsed_json: dict) -> tuple[bool, str]:
    """Reject low-confidence outputs."""

    confidence = parsed_json.get("confidence", 0.0)

    print("\n========== [CONFIDENCE CHECK] ==========")
    print(f"[CONFIDENCE] {confidence}")
    print(f"[THRESHOLD] {CONFIDENCE_THRESHOLD}")

    if confidence < CONFIDENCE_THRESHOLD:
        logger.warning(f"[SAFETY] Low confidence rejected: {confidence}")
        print("[RESULT] REJECTED - confidence too low")
        return False, "low_confidence"

    print("[RESULT] PASSED")
    return True, "confidence_ok"


def validate_intent(intent: dict) -> tuple[bool, str]:
    """Validate intent for safety."""

    intent_type = intent.get("intent", "")
    slots = intent.get("slots", {})

    print("\n========== [SAFETY CHECK] ==========")
    print(f"[INTENT] {intent_type}")
    print(f"[SLOTS] {slots}")

    if intent_type == "CONFIRMATION_REQUIRED":
        print("[RESULT] SAFE - already intercepted by safety layer")
        return True, "requires_confirmation"

    if intent_type in {"OPEN_APP", "OPEN_URL", "SEARCH_WEB"}:
        print(f"[RESULT] SAFE - {intent_type} allowed")
        logger.info(f"[SAFETY] {intent_type}: allowed")
        return True, "safe"

    if intent_type == "TYPE_TEXT":
        text = slots.get("text", "")
        if is_dangerous_text(text):
            print("[RESULT] BLOCKED - dangerous text pattern")
            return False, "dangerous_text"
        print("[RESULT] SAFE - TYPE_TEXT content ok")
        return True, "safe"

    if intent_type == "PRESS_KEYS":
        keys = slots.get("keys", "")
        if is_dangerous_keys(keys):
            print("[RESULT] BLOCKED - dangerous key combo")
            return False, "dangerous_keys"
        print("[RESULT] SAFE - PRESS_KEYS content ok")
        return True, "safe"

    print("[RESULT] SAFE - default allow")
    return True, "safe"


def requires_confirmation(intent: dict) -> bool:
    """Determine if an intent requires explicit user confirmation."""

    intent_type = intent.get("intent", "")
    slots = intent.get("slots", {})

    if intent_type == "CONFIRMATION_REQUIRED":
        return True

    if intent_type in DANGEROUS_INTENTS:
        return True

    if intent_type in {
        "OPEN_FILE",
        "CREATE_FILE",
        "MOVE_FILE",
        "RENAME_FILE",
        "COPY_FILE",
        "PASTE_FILE",
        "CREATE_FOLDER",
        "DELETE_FOLDER",
    }:
        path = slots.get("path") or slots.get("source") or slots.get("destination")
        if is_system_path(path):
            return True

    if intent_type == "TYPE_TEXT":
        return is_dangerous_text(slots.get("text", ""))

    if intent_type == "PRESS_KEYS":
        return is_dangerous_keys(slots.get("keys", ""))

    return False


def full_validation(parsed_json: dict) -> tuple[bool, str, dict]:
    """Full validation pipeline."""

    print("\n========== [FULL VALIDATION] ==========")

    conf_ok, conf_reason = validate_confidence(parsed_json)
    if not conf_ok:
        return False, conf_reason, {
            "confidence": parsed_json.get("confidence", 0.0),
            "threshold": CONFIDENCE_THRESHOLD,
        }

    safety_ok, safety_reason = validate_intent(parsed_json)
    if not safety_ok:
        return False, safety_reason, {
            "intent": parsed_json.get("intent"),
            "blocked_reason": safety_reason,
        }

    print("\n[VALIDATION RESULT] PASSED")
    return True, "valid", {}


__all__ = [
    "CONFIDENCE_THRESHOLD",
    "DANGEROUS_INTENTS",
    "DANGEROUS_KEY_COMBOS",
    "DANGEROUS_PATTERNS",
    "build_confirmation_response",
    "contains_system_path",
    "full_validation",
    "get_confirmation_accessibility",
    "infer_raw_intent",
    "is_dangerous_keys",
    "is_dangerous_text",
    "is_system_path",
    "override_type_text_misuse",
    "pre_intent_safety_check",
    "requires_confirmation",
    "validate_confidence",
    "validate_intent",
]
