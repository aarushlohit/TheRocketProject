"""
Stage 3 — Execution Planner Module.

Converts intent JSON into normalized execution plans:
- Single step wrapping
- Multi-step expansion
- Vague intent expansion
- Step validation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# SUPPORTED INTENTS
# =============================================================================

SUPPORTED_INTENTS = {
    "OPEN_APP",
    "OPEN_URL",
    "SEARCH_WEB",
    "TYPE_TEXT",
    "PRESS_KEYS",
    "SCREENSHOT",
    "CLOSE_APP",
    "MINIMIZE",
    "MAXIMIZE",
    "SCROLL",
    "CLICK",
}

# Intent expansion patterns
INTENT_EXPANSIONS: Dict[str, List[Dict[str, Any]]] = {
    # "open chrome and search youtube" type patterns
    "open_and_search": [
        {"intent": "OPEN_APP", "slots": {"app": "{browser}"}},
        {"intent": "SEARCH_WEB", "slots": {"query": "{query}"}},
    ],
    
    # "open notepad and type" patterns
    "open_and_type": [
        {"intent": "OPEN_APP", "slots": {"app": "{app}"}},
        {"intent": "TYPE_TEXT", "slots": {"text": "{text}"}},
    ],
    
    # "search youtube for videos" → open browser + search
    "search_for": [
        {"intent": "OPEN_APP", "slots": {"app": "chrome"}},
        {"intent": "SEARCH_WEB", "slots": {"query": "{query}"}},
    ],
}


# =============================================================================
# EXECUTION PLAN DATACLASS
# =============================================================================

class ExecutionStep:
    """Represents a single execution step."""
    
    def __init__(
        self,
        intent: str,
        slots: Dict[str, Any],
        confidence: float = 1.0,
        index: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.intent = intent
        self.slots = slots
        self.confidence = confidence
        self.index = index
        self.metadata = metadata or {}
        self.status = "pending"  # pending, executing, success, failed, skipped
        self.error: Optional[str] = None
        self.retries = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "intent": self.intent,
            "slots": self.slots,
            "confidence": self.confidence,
            "index": self.index,
            "status": self.status,
            "retries": self.retries,
            "error": self.error,
            "metadata": self.metadata,
        }
    
    def __repr__(self) -> str:
        return f"ExecutionStep({self.intent}, slots={self.slots}, status={self.status})"


class ExecutionPlan:
    """Represents a full execution plan."""
    
    def __init__(self, steps: Optional[List[ExecutionStep]] = None):
        self.steps = steps or []
        self.status = "created"  # created, executing, completed, failed, partial
        self.current_step_index = 0
        self.failed_step: Optional[int] = None
        self.metadata: Dict[str, Any] = {}
    
    def add_step(self, step: ExecutionStep):
        """Add a step to the plan."""
        step.index = len(self.steps)
        self.steps.append(step)
    
    def get_current_step(self) -> Optional[ExecutionStep]:
        """Get the current step to execute."""
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def advance(self):
        """Advance to the next step."""
        self.current_step_index += 1
    
    def mark_step_success(self):
        """Mark current step as successful."""
        if self.current_step_index < len(self.steps):
            self.steps[self.current_step_index].status = "success"
    
    def mark_step_failed(self, error: str):
        """Mark current step as failed."""
        if self.current_step_index < len(self.steps):
            step = self.steps[self.current_step_index]
            step.status = "failed"
            step.error = error
            self.failed_step = self.current_step_index
    
    def is_complete(self) -> bool:
        """Check if plan is complete."""
        return self.current_step_index >= len(self.steps)
    
    def get_progress(self) -> Tuple[int, int]:
        """Get progress as (current, total)."""
        return (self.current_step_index, len(self.steps))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status,
            "current_step": self.current_step_index,
            "total_steps": len(self.steps),
            "failed_step": self.failed_step,
            "steps": [s.to_dict() for s in self.steps],
            "metadata": self.metadata,
        }
    
    def __len__(self) -> int:
        return len(self.steps)
    
    def __repr__(self) -> str:
        return f"ExecutionPlan(steps={len(self.steps)}, status={self.status})"


# =============================================================================
# EXECUTION PLANNER CLASS
# =============================================================================

class ExecutionPlanner:
    """
    Converts intents to execution plans.
    
    Features:
    - Single intent wrapping
    - Multi-step plan parsing
    - Vague intent expansion
    - Step validation
    """
    
    def __init__(self):
        self.supported_intents = SUPPORTED_INTENTS
        self.expansions = INTENT_EXPANSIONS
    
    def plan(self, intent_data: Dict[str, Any]) -> ExecutionPlan:
        """
        STAGE 4 ENHANCED: Create execution plan from intent data.
        
        Smart Planner Rules:
        1. MULTI_STEP intent → execute steps sequentially
        2. SEARCH_WEB with app context → split into MULTI_STEP (open browser + search)
        3. Compound text patterns → auto-expand to MULTI_STEP
        4. Single intent → wrap in plan
        
        Args:
            intent_data: Intent JSON from model or refiner
            
        Returns:
            ExecutionPlan with steps
        """
        print(f"\n{'='*60}")
        print(f"[STAGE 4 SMART PLANNER]")
        print(f"{'='*60}")
        
        intent_type = intent_data.get("intent", "UNKNOWN")
        slots = intent_data.get("slots", {})
        confidence = intent_data.get("confidence", 1.0)
        
        print(f"[INTENT] {intent_type}")
        print(f"[SLOTS] {slots}")
        
        # =================================================================
        # Case 1: Direct MULTI_STEP intent from model
        # =================================================================
        if intent_type == "MULTI_STEP":
            # Check both top-level "steps" and slots["steps"]
            steps = intent_data.get("steps", slots.get("steps", []))
            plan = self._plan_multi_step_from_array(steps, confidence)
            print(f"[PLAN CREATED] {len(plan)} steps (MULTI_STEP from model)")
            return plan
        
        # =================================================================
        # Case 2: Stage 4 Smart Expansion - SEARCH_WEB with browser context
        # If the user searches and we can infer a browser, add open browser first
        # =================================================================
        if intent_type == "SEARCH_WEB":
            plan = self._smart_expand_search(slots, confidence, intent_data)
            if plan:
                print(f"[PLAN CREATED] {len(plan)} steps (smart search expansion)")
                return plan
        
        # =================================================================
        # Case 3: Check for compound intents in normalized text
        # =================================================================
        normalized_text = intent_data.get("normalized_text", "")
        if self._is_compound_intent(normalized_text):
            plan = self._expand_compound_intent(normalized_text, intent_data)
            if plan:
                print(f"[PLAN CREATED] {len(plan)} steps (compound expanded)")
                return plan
        
        # =================================================================
        # Case 4: Single intent → wrap in plan
        # =================================================================
        plan = self._plan_single_intent(intent_type, slots, confidence, intent_data)
        print(f"[PLAN CREATED] {len(plan)} step(s) (single)")
        
        logger.info(f"[PLANNER] Created plan with {len(plan)} steps")
        return plan
    
    def _smart_expand_search(
        self,
        slots: Dict[str, Any],
        confidence: float,
        original_data: Dict[str, Any],
    ) -> Optional[ExecutionPlan]:
        """
        Stage 4: Smart search expansion.
        
        If SEARCH_WEB contains app context (e.g., "search youtube on chrome"),
        split into MULTI_STEP: OPEN_APP + SEARCH_WEB
        """
        query = slots.get("query", "")
        
        # Check if query contains browser reference
        browsers = ["chrome", "firefox", "edge", "safari", "brave", "browser"]
        query_lower = query.lower()
        
        for browser in browsers:
            if f"on {browser}" in query_lower or f"in {browser}" in query_lower:
                # Extract clean query (remove browser reference)
                clean_query = query_lower.replace(f"on {browser}", "").replace(f"in {browser}", "").strip()
                
                plan = ExecutionPlan()
                
                # Step 1: Open browser
                plan.add_step(ExecutionStep(
                    intent="OPEN_APP",
                    slots={"app": browser},
                    confidence=confidence,
                ))
                
                # Step 2: Search
                plan.add_step(ExecutionStep(
                    intent="SEARCH_WEB",
                    slots={"query": clean_query},
                    confidence=confidence,
                ))
                
                plan.metadata["source"] = "smart_search_expansion"
                plan.metadata["pattern"] = "search_on_browser"
                print(f"[SMART EXPAND] SEARCH_WEB → OPEN_APP({browser}) + SEARCH({clean_query})")
                
                return plan
        
        return None
    
    def _plan_single_intent(
        self,
        intent_type: str,
        slots: Dict[str, Any],
        confidence: float,
        original_data: Dict[str, Any],
    ) -> ExecutionPlan:
        """Create plan for single intent."""
        plan = ExecutionPlan()
        
        # Validate intent
        if intent_type not in self.supported_intents and intent_type != "UNKNOWN":
            print(f"[WARNING] Unsupported intent: {intent_type}")
        
        step = ExecutionStep(
            intent=intent_type,
            slots=slots,
            confidence=confidence,
            metadata={"original": original_data},
        )
        
        plan.add_step(step)
        plan.metadata["source"] = "single_intent"
        
        return plan
    
    def _plan_multi_step_from_array(
        self,
        steps: List[Dict[str, Any]],
        default_confidence: float,
    ) -> ExecutionPlan:
        """Create plan from MULTI_STEP steps array."""
        plan = ExecutionPlan()
        
        if not steps:
            print(f"[WARNING] MULTI_STEP has empty steps array")
            return plan
        
        for i, step_data in enumerate(steps):
            step_intent = step_data.get("intent", "UNKNOWN")
            step_slots = step_data.get("slots", {})
            step_confidence = step_data.get("confidence", default_confidence)
            
            step = ExecutionStep(
                intent=step_intent,
                slots=step_slots,
                confidence=step_confidence,
                index=i,
            )
            
            print(f"[STEP {i}] {step_intent}: {step_slots}")
            plan.add_step(step)
        
        plan.metadata["source"] = "multi_step"
        
        return plan
    
    def _plan_multi_step(
        self,
        slots: Dict[str, Any],
        confidence: float,
    ) -> ExecutionPlan:
        """Legacy: Create plan for MULTI_STEP intent (slots-based)."""
        steps_data = slots.get("steps", [])
        return self._plan_multi_step_from_array(steps_data, confidence)
    
    def _is_compound_intent(self, text: str) -> bool:
        """Check if text contains compound intent."""
        if not text:
            return False
        
        text_lower = text.lower()
        compound_markers = [" and ", " then ", " after that ", ", "]
        
        return any(marker in text_lower for marker in compound_markers)
    
    def _expand_compound_intent(
        self,
        text: str,
        intent_data: Dict[str, Any],
    ) -> Optional[ExecutionPlan]:
        """
        Expand compound intent text into multi-step plan.
        
        Examples:
        - "open chrome and search youtube" → [OPEN_APP chrome, SEARCH_WEB youtube]
        - "launch notepad and type hello" → [OPEN_APP notepad, TYPE_TEXT hello]
        """
        text_lower = text.lower()
        
        # Pattern: "open X and search Y"
        import re
        
        open_search_pattern = r"open\s+(\w+)\s+and\s+search\s+(.+)"
        match = re.search(open_search_pattern, text_lower)
        if match:
            app = match.group(1)
            query = match.group(2)
            
            plan = ExecutionPlan()
            plan.add_step(ExecutionStep(
                intent="OPEN_APP",
                slots={"app": app},
                confidence=intent_data.get("confidence", 0.9),
            ))
            plan.add_step(ExecutionStep(
                intent="SEARCH_WEB",
                slots={"query": query},
                confidence=intent_data.get("confidence", 0.9),
            ))
            plan.metadata["source"] = "compound_expansion"
            plan.metadata["pattern"] = "open_and_search"
            return plan
        
        # Pattern: "open X and type Y"
        open_type_pattern = r"open\s+(\w+)\s+and\s+type\s+(.+)"
        match = re.search(open_type_pattern, text_lower)
        if match:
            app = match.group(1)
            text = match.group(2)
            
            plan = ExecutionPlan()
            plan.add_step(ExecutionStep(
                intent="OPEN_APP",
                slots={"app": app},
                confidence=intent_data.get("confidence", 0.9),
            ))
            plan.add_step(ExecutionStep(
                intent="TYPE_TEXT",
                slots={"text": text},
                confidence=intent_data.get("confidence", 0.9),
            ))
            plan.metadata["source"] = "compound_expansion"
            plan.metadata["pattern"] = "open_and_type"
            return plan
        
        # Pattern: "search X on Y" / "search X in Y"
        search_on_pattern = r"search\s+(.+?)\s+(?:on|in)\s+(\w+)"
        match = re.search(search_on_pattern, text_lower)
        if match:
            query = match.group(1)
            platform = match.group(2)
            
            plan = ExecutionPlan()
            
            # If platform is a browser, open it first
            browsers = ["chrome", "firefox", "edge", "safari", "browser"]
            if platform in browsers:
                plan.add_step(ExecutionStep(
                    intent="OPEN_APP",
                    slots={"app": platform},
                    confidence=intent_data.get("confidence", 0.9),
                ))
            
            plan.add_step(ExecutionStep(
                intent="SEARCH_WEB",
                slots={"query": f"{query} {platform}" if platform not in browsers else query},
                confidence=intent_data.get("confidence", 0.9),
            ))
            plan.metadata["source"] = "compound_expansion"
            plan.metadata["pattern"] = "search_on"
            return plan
        
        return None
    
    def validate_step(self, step: ExecutionStep) -> Tuple[bool, str]:
        """
        Validate a single execution step.
        
        Returns: (is_valid, reason)
        """
        # Check intent is supported
        if step.intent not in self.supported_intents and step.intent != "UNKNOWN":
            return False, f"Unsupported intent: {step.intent}"
        
        # Intent-specific validation
        if step.intent == "OPEN_APP":
            if not step.slots.get("app"):
                return False, "OPEN_APP requires 'app' slot"
        
        elif step.intent == "OPEN_URL":
            if not step.slots.get("url"):
                return False, "OPEN_URL requires 'url' slot"
        
        elif step.intent == "SEARCH_WEB":
            if not step.slots.get("query"):
                return False, "SEARCH_WEB requires 'query' slot"
        
        elif step.intent == "TYPE_TEXT":
            if not step.slots.get("text"):
                return False, "TYPE_TEXT requires 'text' slot"
        
        return True, "valid"
    
    def validate_plan(self, plan: ExecutionPlan) -> Tuple[bool, List[str]]:
        """
        Validate entire execution plan.
        
        Returns: (is_valid, list of issues)
        """
        issues = []
        
        for step in plan.steps:
            is_valid, reason = self.validate_step(step)
            if not is_valid:
                issues.append(f"Step {step.index}: {reason}")
        
        return len(issues) == 0, issues


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_planner_instance: Optional[ExecutionPlanner] = None


def get_execution_planner() -> ExecutionPlanner:
    """Get singleton ExecutionPlanner instance."""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = ExecutionPlanner()
    return _planner_instance


def plan_execution(intent_data: Dict[str, Any]) -> ExecutionPlan:
    """
    Convenience function to create execution plan.
    
    Args:
        intent_data: Intent JSON
        
    Returns:
        ExecutionPlan
    """
    return get_execution_planner().plan(intent_data)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ExecutionStep",
    "ExecutionPlan",
    "ExecutionPlanner",
    "get_execution_planner",
    "plan_execution",
    "SUPPORTED_INTENTS",
]
