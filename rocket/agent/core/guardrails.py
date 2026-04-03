"""
Stage 3 — Execution Guardrails Module.

Pre-execution validation and safety checks:
- Max steps limit
- Loop detection
- Dangerous step flagging
- Resource protection
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from agent.core.safety import is_dangerous_text, is_dangerous_keys
from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# GUARDRAIL CONFIGURATION
# =============================================================================

# Maximum steps in a plan
MAX_PLAN_STEPS = 5

# Maximum retries per step
MAX_RETRIES_PER_STEP = 2

# Maximum total retries across plan
MAX_TOTAL_RETRIES = 6

# Dangerous intents that always require confirmation
DANGEROUS_INTENTS = {
    "TYPE_TEXT",
    "PRESS_KEYS",
}

# Intents that are always safe (no confirmation needed)
SAFE_INTENTS = {
    "OPEN_APP",
    "OPEN_URL",
    "SEARCH_WEB",
    "SCREENSHOT",
    "MINIMIZE",
    "MAXIMIZE",
}

# Intents that modify system state
MODIFYING_INTENTS = {
    "TYPE_TEXT",
    "PRESS_KEYS",
    "CLOSE_APP",
}


# =============================================================================
# GUARDRAIL RESULT
# =============================================================================

class GuardrailResult:
    """Result of guardrail validation."""
    
    def __init__(
        self,
        passed: bool,
        issues: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        requires_confirmation: bool = False,
        blocked_steps: Optional[List[int]] = None,
    ):
        self.passed = passed
        self.issues = issues or []
        self.warnings = warnings or []
        self.requires_confirmation = requires_confirmation
        self.blocked_steps = blocked_steps or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": self.issues,
            "warnings": self.warnings,
            "requires_confirmation": self.requires_confirmation,
            "blocked_steps": self.blocked_steps,
        }
    
    def __bool__(self) -> bool:
        return self.passed


# =============================================================================
# EXECUTION GUARDRAILS CLASS
# =============================================================================

class ExecutionGuardrails:
    """
    Pre-execution validation and safety checks.
    
    Rules:
    1. Max steps = 5
    2. No repeated loops (same intent repeated >3 times)
    3. Dangerous steps require confirmation
    4. Block invalid intent types
    """
    
    def __init__(
        self,
        max_steps: int = MAX_PLAN_STEPS,
        max_retries: int = MAX_RETRIES_PER_STEP,
    ):
        self.max_steps = max_steps
        self.max_retries = max_retries
        self.total_retries = 0
    
    def validate_plan(self, plan) -> GuardrailResult:
        """
        Validate an execution plan.
        
        Args:
            plan: ExecutionPlan to validate
            
        Returns:
            GuardrailResult
        """
        from agent.core.planner import ExecutionPlan
        
        issues = []
        warnings = []
        blocked_steps = []
        requires_confirmation = False
        
        print(f"\n========== [GUARDRAILS CHECK] ==========")
        print(f"[PLAN STEPS] {len(plan.steps)}")
        
        # Rule 1: Max steps check
        if len(plan.steps) > self.max_steps:
            issues.append(f"Plan exceeds maximum steps ({len(plan.steps)} > {self.max_steps})")
            print(f"[GUARDRAIL FAIL] Too many steps: {len(plan.steps)}")
        
        # Rule 2: Loop detection
        loop_issue = self._detect_loops(plan)
        if loop_issue:
            issues.append(loop_issue)
            print(f"[GUARDRAIL FAIL] {loop_issue}")
        
        # Rule 3: Check each step
        for i, step in enumerate(plan.steps):
            step_result = self._validate_step(step, i)
            
            if step_result.blocked_steps:
                blocked_steps.extend(step_result.blocked_steps)
            
            if step_result.requires_confirmation:
                requires_confirmation = True
            
            issues.extend(step_result.issues)
            warnings.extend(step_result.warnings)
        
        passed = len(issues) == 0
        
        print(f"[GUARDRAILS RESULT] {'PASSED' if passed else 'FAILED'}")
        if issues:
            print(f"[ISSUES] {issues}")
        if warnings:
            print(f"[WARNINGS] {warnings}")
        if requires_confirmation:
            print(f"[CONFIRMATION REQUIRED]")
        
        logger.info(f"[GUARDRAILS] passed={passed}, issues={len(issues)}, warnings={len(warnings)}")
        
        return GuardrailResult(
            passed=passed,
            issues=issues,
            warnings=warnings,
            requires_confirmation=requires_confirmation,
            blocked_steps=blocked_steps,
        )
    
    def _detect_loops(self, plan) -> Optional[str]:
        """
        Detect suspicious repeated patterns.
        
        Returns issue string if loop detected, None otherwise.
        """
        if len(plan.steps) < 3:
            return None
        
        # Count intent occurrences
        intent_counts: Dict[str, int] = {}
        for step in plan.steps:
            intent = step.intent
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        # Check for repeated intents (same intent > 3 times)
        for intent, count in intent_counts.items():
            if count > 3:
                return f"Suspicious loop detected: {intent} repeated {count} times"
        
        # Check for exact slot repetition
        seen_steps: Set[str] = set()
        for step in plan.steps:
            step_key = f"{step.intent}:{sorted(step.slots.items())}"
            if step_key in seen_steps:
                return f"Duplicate step detected: {step.intent}"
            seen_steps.add(step_key)
        
        return None
    
    def _validate_step(self, step, index: int) -> GuardrailResult:
        """Validate a single step."""
        issues = []
        warnings = []
        blocked = []
        requires_confirmation = False
        
        intent = step.intent
        slots = step.slots
        
        # Check for UNKNOWN intent
        if intent == "UNKNOWN":
            issues.append(f"Step {index}: Unknown intent")
            blocked.append(index)
        
        # Check for dangerous intents
        if intent in DANGEROUS_INTENTS:
            if intent == "TYPE_TEXT":
                text = slots.get("text", "")
                if is_dangerous_text(text):
                    issues.append(f"Step {index}: Dangerous text content detected")
                    blocked.append(index)
                    requires_confirmation = True
                elif text:
                    warnings.append(f"Step {index}: TYPE_TEXT will type '{text[:30]}...'")
            
            elif intent == "PRESS_KEYS":
                keys = slots.get("keys", "")
                if is_dangerous_keys(keys):
                    issues.append(f"Step {index}: Dangerous key combination detected")
                    blocked.append(index)
                    requires_confirmation = True
        
        # Check for missing required slots
        slot_issue = self._check_required_slots(intent, slots, index)
        if slot_issue:
            issues.append(slot_issue)
        
        # Confidence check
        if step.confidence < 0.5:
            warnings.append(f"Step {index}: Low confidence ({step.confidence:.0%})")
        
        return GuardrailResult(
            passed=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            requires_confirmation=requires_confirmation,
            blocked_steps=blocked,
        )
    
    def _check_required_slots(self, intent: str, slots: dict, index: int) -> Optional[str]:
        """Check that required slots are present."""
        required_slots = {
            "OPEN_APP": ["app"],
            "OPEN_URL": ["url"],
            "SEARCH_WEB": ["query"],
            "TYPE_TEXT": ["text"],
            "PRESS_KEYS": ["keys"],
        }
        
        required = required_slots.get(intent, [])
        for slot in required:
            if not slots.get(slot):
                return f"Step {index}: Missing required slot '{slot}' for {intent}"
        
        return None
    
    def check_retry_limit(self, current_retries: int) -> Tuple[bool, str]:
        """
        Check if retry limit has been reached.
        
        Returns: (can_retry, message)
        """
        if current_retries >= self.max_retries:
            return False, f"Max retries reached ({self.max_retries})"
        
        self.total_retries += 1
        
        if self.total_retries >= MAX_TOTAL_RETRIES:
            return False, f"Total retry limit reached ({MAX_TOTAL_RETRIES})"
        
        return True, "Retry allowed"
    
    def reset_retry_count(self):
        """Reset total retry counter (for new plan)."""
        self.total_retries = 0
    
    def is_safe_intent(self, intent: str) -> bool:
        """Check if intent is inherently safe."""
        return intent in SAFE_INTENTS
    
    def requires_confirmation(self, intent: str, slots: dict) -> bool:
        """
        Determine if intent requires user confirmation.
        
        Confirmation required for:
        - TYPE_TEXT with dangerous content
        - PRESS_KEYS with dangerous combinations
        - CLOSE_APP always (safety measure)
        """
        if intent == "TYPE_TEXT":
            text = slots.get("text", "")
            return is_dangerous_text(text)
        
        if intent == "PRESS_KEYS":
            keys = slots.get("keys", "")
            return is_dangerous_keys(keys)
        
        # CLOSE_APP always requires confirmation
        if intent == "CLOSE_APP":
            return True
        
        return False


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_guardrails_instance: Optional[ExecutionGuardrails] = None


def get_guardrails() -> ExecutionGuardrails:
    """Get singleton ExecutionGuardrails instance."""
    global _guardrails_instance
    if _guardrails_instance is None:
        _guardrails_instance = ExecutionGuardrails()
    return _guardrails_instance


def validate_plan(plan) -> GuardrailResult:
    """Convenience function to validate a plan."""
    return get_guardrails().validate_plan(plan)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "GuardrailResult",
    "ExecutionGuardrails",
    "get_guardrails",
    "validate_plan",
    "MAX_PLAN_STEPS",
    "MAX_RETRIES_PER_STEP",
    "DANGEROUS_INTENTS",
    "SAFE_INTENTS",
]
