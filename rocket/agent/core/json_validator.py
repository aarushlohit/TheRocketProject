"""
Stage 4 — JSON Validation Layer.

Strict validation of intent JSON before execution:
- Intent existence check
- Required slots validation
- App name validation
- Query validation
- Confidence threshold check

RULE: Invalid JSON = NO execution
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Minimum confidence to execute
MIN_CONFIDENCE_THRESHOLD = 0.7

# Supported intents
VALID_INTENTS = {
    "OPEN_APP",
    "OPEN_URL",
    "SEARCH_WEB",
    "TYPE_TEXT",
    "PRESS_KEYS",
    "MULTI_STEP",
    "SCREENSHOT",
    "CLOSE_APP",
    "MINIMIZE",
    "MAXIMIZE",
    "SCROLL",
    "CLICK",
    "UNKNOWN",
}

# Required slots per intent
REQUIRED_SLOTS: Dict[str, List[str]] = {
    "OPEN_APP": ["app"],
    "OPEN_URL": ["url"],
    "SEARCH_WEB": ["query"],
    "TYPE_TEXT": ["text"],
    "PRESS_KEYS": ["keys"],
    "MULTI_STEP": ["steps"],
}

# Known app patterns (basic validation)
KNOWN_APP_PATTERNS = [
    # Browsers
    r"chrome|firefox|edge|safari|brave|opera|vivaldi|browser",
    # Editors
    r"code|vscode|notepad|sublime|atom|vim|emacs",
    # System
    r"calculator|calc|terminal|cmd|powershell|explorer|finder",
    # Media
    r"spotify|vlc|youtube|music|video",
    # Communication
    r"discord|slack|teams|zoom|skype",
    # Office
    r"word|excel|powerpoint|outlook|office",
    # Games
    r"steam|epic|games",
    # Generic
    r"\w+",  # Allow any word as last resort
]


# =============================================================================
# VALIDATION RESULT
# =============================================================================

@dataclass
class ValidationResult:
    """Result of JSON validation."""
    
    valid: bool
    intent_data: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "confidence": self.confidence,
        }


# =============================================================================
# JSON VALIDATOR CLASS
# =============================================================================

class JSONValidator:
    """
    Strict JSON validation for intent data.
    
    Rules:
    1. Intent MUST exist and be valid
    2. Required slots MUST exist for each intent
    3. Slot values MUST NOT be empty
    4. Confidence MUST exceed threshold
    5. MULTI_STEP steps MUST be valid
    """
    
    def __init__(
        self,
        min_confidence: float = MIN_CONFIDENCE_THRESHOLD,
    ):
        self.min_confidence = min_confidence
        self.valid_intents = VALID_INTENTS
        self.required_slots = REQUIRED_SLOTS
    
    def validate(self, intent_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate intent JSON structure.
        
        Args:
            intent_data: Raw intent JSON from model
            
        Returns:
            ValidationResult with valid flag and any errors
        """
        errors: List[str] = []
        warnings: List[str] = []
        
        print(f"\n{'='*60}")
        print(f"[JSON VALIDATOR] Validating intent data")
        print(f"{'='*60}")
        
        if not intent_data:
            return ValidationResult(
                valid=False,
                intent_data={},
                errors=["Empty intent data"],
                warnings=[],
                confidence=0.0,
            )
        
        # Check for error status from model
        if intent_data.get("status") == "error":
            return ValidationResult(
                valid=False,
                intent_data=intent_data,
                errors=[f"Model error: {intent_data.get('message', 'Unknown')}"],
                warnings=[],
                confidence=0.0,
            )
        
        # =================================================================
        # CHECK 1: Intent exists
        # =================================================================
        intent = intent_data.get("intent")
        
        if not intent:
            errors.append("Missing 'intent' field")
            print(f"[VALIDATION ERROR] Missing 'intent' field")
        elif intent not in self.valid_intents:
            errors.append(f"Invalid intent: {intent}")
            print(f"[VALIDATION ERROR] Invalid intent: {intent}")
        else:
            print(f"[VALIDATION PASS] Intent: {intent}")
        
        # =================================================================
        # CHECK 2: Confidence threshold
        # =================================================================
        confidence = intent_data.get("confidence", 0.0)
        
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            confidence = 0.0
            warnings.append("Invalid confidence value, defaulting to 0.0")
        
        if confidence < self.min_confidence:
            warnings.append(f"Low confidence: {confidence:.2f} < {self.min_confidence}")
            print(f"[VALIDATION WARN] Low confidence: {confidence:.2f}")
        else:
            print(f"[VALIDATION PASS] Confidence: {confidence:.2f}")
        
        # =================================================================
        # CHECK 3: Required slots
        # =================================================================
        slots = intent_data.get("slots", {})
        
        if intent in self.required_slots:
            for slot_name in self.required_slots[intent]:
                # Handle MULTI_STEP special case
                if intent == "MULTI_STEP" and slot_name == "steps":
                    steps = intent_data.get("steps", slots.get("steps", []))
                    if not steps:
                        errors.append("MULTI_STEP requires 'steps' array")
                        print(f"[VALIDATION ERROR] MULTI_STEP missing 'steps'")
                    else:
                        # Validate each step
                        step_errors = self._validate_steps(steps)
                        errors.extend(step_errors)
                        print(f"[VALIDATION PASS] MULTI_STEP has {len(steps)} steps")
                else:
                    slot_value = slots.get(slot_name)
                    if not slot_value:
                        errors.append(f"{intent} requires '{slot_name}' slot")
                        print(f"[VALIDATION ERROR] Missing slot: {slot_name}")
                    else:
                        print(f"[VALIDATION PASS] Slot '{slot_name}': {slot_value}")
        
        # =================================================================
        # CHECK 4: Slot value validation
        # =================================================================
        if intent == "OPEN_APP":
            app = slots.get("app", "")
            if app:
                # Check app name is not a command word
                if self._is_command_word(app):
                    errors.append(f"Invalid app name (command word): {app}")
                    print(f"[VALIDATION ERROR] App name is command word: {app}")
                else:
                    print(f"[VALIDATION PASS] App name valid: {app}")
        
        if intent == "SEARCH_WEB":
            query = slots.get("query", "")
            if query:
                # Check query is not empty after stripping
                if not query.strip():
                    errors.append("Search query is empty")
                    print(f"[VALIDATION ERROR] Empty search query")
                # Warn if query starts with command word
                elif self._starts_with_command(query):
                    warnings.append(f"Query may contain command word: {query}")
                    print(f"[VALIDATION WARN] Query starts with command: {query}")
                else:
                    print(f"[VALIDATION PASS] Search query: {query[:50]}...")
        
        if intent == "OPEN_URL":
            url = slots.get("url", "")
            if url:
                if not self._is_valid_url(url):
                    warnings.append(f"URL may be invalid: {url}")
                    print(f"[VALIDATION WARN] URL format: {url}")
                else:
                    print(f"[VALIDATION PASS] URL: {url}")
        
        # =================================================================
        # FINAL RESULT
        # =================================================================
        is_valid = len(errors) == 0
        
        print(f"\n[VALIDATION RESULT] Valid: {is_valid}")
        if errors:
            print(f"[ERRORS] {errors}")
        if warnings:
            print(f"[WARNINGS] {warnings}")
        
        logger.info(f"[JSON VALIDATOR] Valid={is_valid}, Errors={len(errors)}, Warnings={len(warnings)}")
        
        return ValidationResult(
            valid=is_valid,
            intent_data=intent_data,
            errors=errors,
            warnings=warnings,
            confidence=confidence,
        )
    
    def _validate_steps(self, steps: List[Dict[str, Any]]) -> List[str]:
        """Validate MULTI_STEP steps."""
        errors = []
        
        if not isinstance(steps, list):
            errors.append("'steps' must be an array")
            return errors
        
        if len(steps) == 0:
            errors.append("'steps' array is empty")
            return errors
        
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"Step {i} is not an object")
                continue
            
            step_intent = step.get("intent")
            if not step_intent:
                errors.append(f"Step {i} missing 'intent'")
            elif step_intent not in self.valid_intents:
                errors.append(f"Step {i} has invalid intent: {step_intent}")
            
            step_slots = step.get("slots", {})
            if step_intent in self.required_slots and step_intent != "MULTI_STEP":
                for slot_name in self.required_slots[step_intent]:
                    if not step_slots.get(slot_name):
                        errors.append(f"Step {i} ({step_intent}) missing '{slot_name}'")
        
        return errors
    
    def _is_command_word(self, text: str) -> bool:
        """Check if text is a command word."""
        command_words = {
            "open", "close", "search", "type", "press", "click",
            "scroll", "minimize", "maximize", "launch", "start",
            "run", "execute", "find", "look", "get",
        }
        return text.lower().strip() in command_words
    
    def _starts_with_command(self, text: str) -> bool:
        """Check if text starts with a command word."""
        command_words = {"search", "find", "look", "google", "open"}
        first_word = text.lower().split()[0] if text else ""
        return first_word in command_words
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        url_pattern = r'^(https?://|www\.|\w+\.\w+)'
        return bool(re.match(url_pattern, url, re.IGNORECASE))


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_validator_instance: Optional[JSONValidator] = None


def get_json_validator() -> JSONValidator:
    """Get singleton JSONValidator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = JSONValidator()
    return _validator_instance


def validate_intent_json(intent_data: Dict[str, Any]) -> ValidationResult:
    """
    Convenience function to validate intent JSON.
    
    Args:
        intent_data: Intent JSON from model
        
    Returns:
        ValidationResult
    """
    return get_json_validator().validate(intent_data)
