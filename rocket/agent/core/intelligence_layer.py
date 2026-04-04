"""
Stage 5.5 — Intelligence Layer Module.

Enhanced reasoning and validation for autonomous execution:
- Intent validation with anti-hallucination
- Consensus logic for multiple interpretations
- Context priority engine
- Search normalization
- Multi-step detection
- Goal interpretation
- Self-correction strategy
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from agent.utils.logger import get_logger
from agent.core.intent_system import VALID_INTENTS, is_valid_intent
from agent.core.anti_hallucination import check_hallucination, KNOWN_APPS
from agent.core.safety import (
    build_confirmation_response,
    is_system_path,
    override_type_text_misuse,
    pre_intent_safety_check,
    requires_confirmation,
)
from agent.core.user_profile import UserProfile
from agent.core.goal_expander import (
    is_high_level_goal,
    expand_goal,
    normalize_search_query,
    contains_multiple_actions,
    split_compound_input,
)
from agent.core.semantic_ui import normalize_target, VALID_TARGETS


logger = get_logger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Confidence thresholds
MIN_CONFIDENCE_THRESHOLD = 0.6
HIGH_CONFIDENCE_THRESHOLD = 0.85

# Multi-step detection keywords
MULTI_STEP_KEYWORDS = {"and", "then", "after", "next", "also", "before"}

# Search command prefixes to remove
SEARCH_PREFIXES = [
    "search for", "search", "find", "look for", "look up",
    "google", "bing", "search for me", "can you find",
]


# =============================================================================
# INTELLIGENCE RESULT
# =============================================================================

@dataclass
class IntelligenceResult:
    """Result from the intelligence layer processing."""
    intent_data: Dict[str, Any]
    is_valid: bool
    confidence: float
    validation_passed: bool
    consensus_score: float = 1.0
    context_applied: bool = False
    normalized: bool = False
    expanded: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# 1. INTENT VALIDATION (CRITICAL)
# =============================================================================

def validate_intent_against_input(
    input_text: str,
    intent_data: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """
    Validate that intent matches input text.
    
    Checks:
    - Intent is valid enum
    - Slots derive from input
    - No hallucinated entities
    """
    errors = []
    intent = intent_data.get("intent", "")
    slots = intent_data.get("slots", {})
    
    # Check 1: Valid intent enum
    if not is_valid_intent(intent):
        errors.append(f"Invalid intent: {intent}")
        return False, errors
    
    # Check 2: Use anti-hallucination
    hallucination_check = check_hallucination(input_text, intent_data)
    if not hallucination_check.valid:
        errors.extend(hallucination_check.errors)
        return False, errors
    
    return True, errors


# =============================================================================
# 2. CONSENSUS LOGIC
# =============================================================================

def apply_consensus(
    candidates: List[Dict[str, Any]],
    input_text: str,
) -> Dict[str, Any]:
    """
    Apply consensus logic to multiple interpretations.
    
    Rules:
    - Prefer majority agreement
    - Prefer semantic similarity to input
    - Prefer known applications
    - Reject outliers
    
    FIX 3: CONSENSUS BYPASS for OPEN_APP
    If ANY candidate is OPEN_APP with confidence > 0.7, select immediately.
    
    FIX 3b: DISABLE CONSENSUS TEMPORARILY
    For now, just select highest confidence candidate.
    """
    if not candidates:
        return {"intent": "UNKNOWN", "slots": {}, "confidence": 0.0}
    
    if len(candidates) == 1:
        return candidates[0]
    
    # FIX 3: CONSENSUS BYPASS - Check for high-confidence OPEN_APP first
    for candidate in candidates:
        if (candidate.get("intent") == "OPEN_APP" and 
            candidate.get("confidence", 0) > 0.7):
            print(f"[CONSENSUS BYPASS] OPEN_APP with confidence {candidate.get('confidence'):.2f} - selecting immediately")
            return candidate
    
    # FIX 3b: DISABLE CONSENSUS - Just select highest confidence
    print(f"[CONSENSUS DISABLED] Selecting highest confidence candidate")
    best = max(candidates, key=lambda c: c.get("confidence", 0))
    print(f"[CONSENSUS] Selected {best.get('intent')} with confidence {best.get('confidence'):.2f}")
    return best
    
    # OLD CONSENSUS LOGIC - DISABLED FOR NOW
    # # Group by intent type
    # intent_groups: Dict[str, List[Dict]] = {}
    # for candidate in candidates:
    #     intent = candidate.get("intent", "UNKNOWN")
    #     if intent not in intent_groups:
    #         intent_groups[intent] = []
    #     intent_groups[intent].append(candidate)
    # 
    # # Find majority
    # majority_intent = max(intent_groups.keys(), key=lambda k: len(intent_groups[k]))
    # majority_candidates = intent_groups[majority_intent]
    # 
    # # From majority, select highest confidence
    # best = max(majority_candidates, key=lambda c: c.get("confidence", 0))
    # 
    # # Validate against input
    # valid, _ = validate_intent_against_input(input_text, best)
    # if not valid:
    #     # Try next best
    #     for candidate in sorted(candidates, key=lambda c: -c.get("confidence", 0)):
    #         valid, _ = validate_intent_against_input(input_text, candidate)
    #         if valid:
    #             return candidate
    #     
    #     return {"intent": "UNKNOWN", "slots": {}, "confidence": 0.0}
    # 
    # return best


# =============================================================================
# 3. CONTEXT PRIORITY ENGINE
# =============================================================================

def apply_context_priority(
    intent_data: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Apply context-aware optimizations.
    
    Rules:
    - If browser open → prefer SEARCH_WEB over OPEN_APP + SEARCH
    - If app active → reuse instead of reopen
    - DO NOT reopen unnecessarily
    """
    if not context:
        return intent_data
    
    intent = intent_data.get("intent")
    slots = intent_data.get("slots", {})
    
    # If trying to open app that's already open
    if intent == "OPEN_APP":
        app = slots.get("app", "").lower()
        last_app = (context.get("last_app") or "").lower()
        
        if app and app == last_app:
            # Skip - app already open
            return {
                "intent": "FOCUS_WINDOW",
                "slots": {"window": app},
                "confidence": intent_data.get("confidence", 0.9),
                "_context_optimized": True,
            }
    
    # If MULTI_STEP with OPEN_APP browser + SEARCH_WEB and browser is open
    if intent == "MULTI_STEP":
        steps = intent_data.get("steps", [])
        if len(steps) >= 2:
            first = steps[0]
            second = steps[1]
            
            if first.get("intent") == "OPEN_APP" and second.get("intent") == "SEARCH_WEB":
                browser = first.get("slots", {}).get("app", "").lower()
                last_browser = (context.get("last_browser") or "").lower()
                
                if browser and browser == last_browser:
                    # Skip OPEN_APP, just SEARCH_WEB
                    return {
                        "intent": "SEARCH_WEB",
                        "slots": second.get("slots", {}),
                        "confidence": intent_data.get("confidence", 0.9),
                        "_context_optimized": True,
                    }
    
    return intent_data


# =============================================================================
# 4. SEARCH NORMALIZATION
# =============================================================================

def normalize_search(intent_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize search queries by removing command words.
    
    "search github" → query: "github"
    "find python tutorials" → query: "python tutorials"
    """
    intent = intent_data.get("intent")
    
    if intent != "SEARCH_WEB":
        return intent_data
    
    slots = intent_data.get("slots", {})
    query = slots.get("query", "")
    
    if query:
        normalized = normalize_search_query(query)
        if normalized != query:
            new_slots = dict(slots)
            new_slots["query"] = normalized
            return {
                **intent_data,
                "slots": new_slots,
                "_normalized": True,
            }
    
    return intent_data


# =============================================================================
# 5. MULTI-STEP DETECTION
# =============================================================================

def detect_multi_step(input_text: str) -> bool:
    """
    Detect if input requires multi-step execution.
    
    Triggers:
    - Contains "and", "then", etc.
    - Multiple verbs
    - Sequential goals
    """
    if not input_text:
        return False
    
    text_lower = input_text.lower()
    
    # Check for multi-step keywords
    for keyword in MULTI_STEP_KEYWORDS:
        # Use word boundary to avoid false positives
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, text_lower):
            return True
    
    # Check for multiple action verbs
    action_verbs = ["open", "search", "type", "click", "close", "go to", "find"]
    verb_count = sum(1 for verb in action_verbs if verb in text_lower)
    
    if verb_count >= 2:
        return True
    
    return False


def ensure_multi_step(
    input_text: str,
    intent_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Ensure multi-step inputs return MULTI_STEP intent.
    """
    if intent_data.get("intent") == "MULTI_STEP":
        return intent_data
    
    if not detect_multi_step(input_text):
        return intent_data
    
    # Split and create steps
    parts = split_compound_input(input_text)
    
    if len(parts) <= 1:
        return intent_data
    
    # This is a multi-step that wasn't detected - wrap single intent
    return {
        "intent": "MULTI_STEP",
        "steps": [intent_data],
        "confidence": intent_data.get("confidence", 0.8),
        "_forced_multi_step": True,
    }


# =============================================================================
# 6. GOAL INTERPRETER
# =============================================================================

def interpret_goal(
    input_text: str,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Interpret high-level goals into executable steps.
    
    "watch youtube cat videos" →
    1. OPEN_APP browser
    2. SEARCH_WEB "youtube cat videos"
    3. CLICK_ELEMENT "first result"
    """
    if not is_high_level_goal(input_text):
        return None
    
    result = expand_goal(input_text, context)
    
    if not result.is_goal or not result.steps:
        return None
    
    if len(result.steps) == 1:
        return {
            **result.steps[0],
            "confidence": result.confidence,
            "_goal_interpreted": True,
        }
    
    return {
        "intent": "MULTI_STEP",
        "steps": result.steps,
        "confidence": result.confidence,
        "_goal_interpreted": True,
    }


# =============================================================================
# 7. UI SEMANTIC CONTROL
# =============================================================================

def enforce_semantic_ui(intent_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforce semantic UI targeting (no coordinates).
    
    Validates CLICK_ELEMENT targets are semantic.
    """
    intent = intent_data.get("intent")
    
    if intent == "CLICK_ELEMENT":
        slots = intent_data.get("slots", {})
        target = slots.get("target", "")
        
        # Normalize target
        normalized = normalize_target(target)
        if normalized and normalized != target:
            new_slots = dict(slots)
            new_slots["target"] = normalized
            return {
                **intent_data,
                "slots": new_slots,
                "_semantic_normalized": True,
            }
    
    # Also check MULTI_STEP
    if intent == "MULTI_STEP":
        steps = intent_data.get("steps", [])
        new_steps = [enforce_semantic_ui(step) for step in steps]
        return {
            **intent_data,
            "steps": new_steps,
        }
    
    return intent_data


# =============================================================================
# 8. SELF-CORRECTION STRATEGY
# =============================================================================

def apply_self_correction(
    intent_data: Dict[str, Any],
    input_text: str,
) -> Dict[str, Any]:
    """
    Apply self-correction for unreliable actions.
    
    Rules:
    - Unknown apps → fallback to browser search
    - Low confidence → prefer simpler action
    - Unreliable targets → use search instead
    """
    intent = intent_data.get("intent")
    slots = intent_data.get("slots", {})
    confidence = intent_data.get("confidence", 0.5)
    
    # Low confidence fallback
    if confidence < MIN_CONFIDENCE_THRESHOLD:
        # Try browser search as fallback
        return {
            "intent": "SEARCH_WEB",
            "slots": {"query": input_text},
            "confidence": 0.7,
            "_self_corrected": True,
            "_reason": "low_confidence_fallback",
        }
    
    # Unknown app fallback
    if intent == "OPEN_APP":
        app = slots.get("app", "").lower()
        if app and app not in KNOWN_APPS:
            # Search for the app instead
            return {
                "intent": "SEARCH_WEB",
                "slots": {"query": f"open {app}"},
                "confidence": 0.75,
                "_self_corrected": True,
                "_reason": "unknown_app_fallback",
            }
    
    return intent_data


# =============================================================================
# 9. SAFETY FILTER
# =============================================================================

def apply_safety_filter(
    intent_data: Dict[str, Any],
    user_profile: Optional[UserProfile] = None,
) -> Dict[str, Any]:
    """
    Apply Stage 5.6 safety interception after intent shaping.

    The mandatory pre-intent safety layer should already run on raw input.
    This function is the final deterministic guard before execution.
    """
    if intent_data.get("intent") == "CONFIRMATION_REQUIRED":
        return intent_data

    intent = intent_data.get("intent")
    slots = intent_data.get("slots", {})

    override = override_type_text_misuse(intent_data, user_profile)
    if override is not None:
        return override

    if intent == "MULTI_STEP":
        steps = intent_data.get("steps", [])
        for step in steps:
            filtered = apply_safety_filter(step, user_profile)
            if filtered.get("intent") == "CONFIRMATION_REQUIRED":
                return build_confirmation_response(
                    intent_data,
                    reason="dangerous_operation",
                    user_profile=user_profile,
                    original_intent="MULTI_STEP",
                    original_slots={"steps": steps},
                    metadata={"triggering_step": filtered},
                )

    if requires_confirmation(intent_data):
        path = slots.get("path") or slots.get("source") or slots.get("destination")
        reason = "system_path_operation" if is_system_path(path) else "dangerous_operation"
        return build_confirmation_response(
            intent_data,
            reason=reason,
            user_profile=user_profile,
        )

    return intent_data


# =============================================================================
# 10. FAILURE HANDLING
# =============================================================================

def handle_failure(
    reason: str,
    input_text: str = "",
    details: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Handle failures gracefully.
    
    Returns UNKNOWN with reason for debugging.
    """
    return {
        "intent": "UNKNOWN",
        "slots": {},
        "confidence": 0.0,
        "_failure_reason": reason,
        "_input": input_text[:100] if input_text else "",
        "_details": details or {},
    }


# =============================================================================
# MAIN INTELLIGENCE PIPELINE
# =============================================================================

def process_with_intelligence(
    input_text: str,
    raw_intent: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    candidates: Optional[List[Dict[str, Any]]] = None,
    user_profile: Optional[UserProfile] = None,
) -> IntelligenceResult:
    """
    Process intent through the Stage 5.6 intelligence layer.
    
    Pipeline:
    1. Intent validation
    2. Consensus logic (if multiple candidates)
    3. Context priority
    4. Search normalization
    5. Multi-step detection
    6. Goal interpretation
    7. UI semantic control
    8. Self-correction
    9. Safety filter
    10. Final validation
    """
    errors = []
    warnings = []
    metadata = {}

    # 0. Mandatory pre-intent safety layer
    safety_intercept = pre_intent_safety_check(input_text, user_profile)
    if safety_intercept is not None:
        metadata["pre_intent_safety"] = True
        metadata["confirmation_required"] = True
        warnings.append("Pre-intent safety interception applied")
        return IntelligenceResult(
            intent_data=safety_intercept,
            is_valid=True,
            confidence=1.0,
            validation_passed=True,
            warnings=warnings,
            metadata=metadata,
        )
    
    # Start with raw intent or consensus
    if candidates and len(candidates) > 1:
        intent_data = apply_consensus(candidates, input_text)
        metadata["consensus_applied"] = True
    else:
        intent_data = raw_intent.copy()
    
    # 1. Initial validation
    valid, validation_errors = validate_intent_against_input(input_text, intent_data)
    if not valid:
        # Try goal interpretation as fallback
        goal_result = interpret_goal(input_text, context)
        if goal_result:
            intent_data = goal_result
            metadata["goal_interpreted"] = True
        else:
            errors.extend(validation_errors)
            return IntelligenceResult(
                intent_data=handle_failure("validation_failed", input_text),
                is_valid=False,
                confidence=0.0,
                validation_passed=False,
                errors=errors,
            )
    
    # 2. Context priority
    intent_data = apply_context_priority(intent_data, context)
    if intent_data.get("_context_optimized"):
        metadata["context_optimized"] = True
    
    # 3. Search normalization
    intent_data = normalize_search(intent_data)
    if intent_data.get("_normalized"):
        metadata["search_normalized"] = True
    
    # 4. Multi-step detection
    intent_data = ensure_multi_step(input_text, intent_data)
    if intent_data.get("_forced_multi_step"):
        metadata["forced_multi_step"] = True
    
    # 5. UI semantic control
    intent_data = enforce_semantic_ui(intent_data)
    if intent_data.get("_semantic_normalized"):
        metadata["semantic_normalized"] = True
    
    # 6. Self-correction
    intent_data = apply_self_correction(intent_data, input_text)
    if intent_data.get("_self_corrected"):
        metadata["self_corrected"] = True
        warnings.append(f"Self-corrected: {intent_data.get('_reason')}")
    
    # 7. Safety filter
    intent_data = apply_safety_filter(intent_data, user_profile)
    if intent_data.get("intent") == "CONFIRMATION_REQUIRED":
        metadata["confirmation_required"] = True
    
    # 8. Final confidence check
    confidence = intent_data.get("confidence", 0.0)
    
    return IntelligenceResult(
        intent_data=intent_data,
        is_valid=True,
        confidence=confidence,
        validation_passed=True,
        context_applied=metadata.get("context_optimized", False),
        normalized=metadata.get("search_normalized", False),
        expanded=metadata.get("goal_interpreted", False),
        warnings=warnings,
        metadata=metadata,
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Main function
    "process_with_intelligence",
    
    # Individual processors
    "validate_intent_against_input",
    "apply_consensus",
    "apply_context_priority",
    "normalize_search",
    "detect_multi_step",
    "ensure_multi_step",
    "interpret_goal",
    "enforce_semantic_ui",
    "apply_self_correction",
    "apply_safety_filter",
    "handle_failure",
    
    # Result class
    "IntelligenceResult",
    
    # Constants
    "MIN_CONFIDENCE_THRESHOLD",
    "HIGH_CONFIDENCE_THRESHOLD",
]
