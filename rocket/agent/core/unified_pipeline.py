"""
Stage 6.0 - Unified Pipeline Orchestrator.

Single entry point for the Autonomous AI Operating System.
Orchestrates the complete pipeline:

    PERCEPTION → PRE-SAFETY → INTENT → PLAN → ROUTE → EXECUTE → VERIFY → MEMORY

NO TEXT. NO EXPLANATION. STRICT JSON ONLY.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from agent.core.autonomous_os import (
    AutonomousOSProcessor,
    ExecutionResult,
    SessionContext,
    get_processor,
    get_session_context,
    pre_intent_safety_check,
    classify_multi_step,
    route_intent,
    ExecutionRoute,
    ALL_VALID_INTENTS,
    FILE_CONTROL_INTENTS,
    SYSTEM_CONTROL_INTENTS,
    build_confirmation_response,
    get_user_accessibility,
)
from agent.core.verification_layer import (
    ExecutionVerifier,
    VerificationResult,
    get_verifier,
)
from agent.core.context_memory import get_context_memory
from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# PIPELINE STAGES
# =============================================================================

class PipelineStage:
    """Pipeline stage names."""
    PERCEPTION = "perception"
    PRE_SAFETY = "pre_safety"
    INTENT = "intent"
    PLAN = "plan"
    ROUTE = "route"
    EXECUTE = "execute"
    VERIFY = "verify"
    MEMORY = "memory"


# =============================================================================
# PIPELINE RESULT
# =============================================================================

@dataclass
class PipelineResult:
    """Complete pipeline execution result."""
    
    status: str  # success | failed | blocked | confirmation_required
    intent: str
    confidence: float
    
    # Stage results
    stages_completed: List[str] = field(default_factory=list)
    execution_result: Optional[Dict[str, Any]] = None
    verification_result: Optional[Dict[str, Any]] = None
    
    # Error handling
    error: Optional[str] = None
    failed_stage: Optional[str] = None
    
    # Metadata
    execution_time_ms: float = 0.0
    route: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "status": self.status,
            "intent": self.intent,
            "confidence": self.confidence,
            "stages_completed": self.stages_completed,
            "execution_result": self.execution_result,
            "verification_result": self.verification_result,
            "error": self.error,
            "failed_stage": self.failed_stage,
            "execution_time_ms": self.execution_time_ms,
            "route": self.route,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


# =============================================================================
# UNIFIED PIPELINE
# =============================================================================

class UnifiedPipeline:
    """
    Unified Pipeline Orchestrator for Autonomous AI Operating System.
    
    Complete pipeline:
        PERCEPTION → PRE-SAFETY → INTENT → PLAN → ROUTE → EXECUTE → VERIFY → MEMORY
    
    HARD RULES:
    - OUTPUT MUST BE STRICT JSON
    - NO TEXT, NO EXPLANATION, NO MARKDOWN
    - NO GUESSING, NO HALLUCINATION
    - USE ONLY ENUM INTENTS
    - INVALID → RETURN UNKNOWN
    - STOP ON FAILURE
    - VERIFY EACH STEP
    """
    
    def __init__(self):
        self.processor = get_processor()
        self.verifier = get_verifier()
        self.context_memory = get_context_memory()
        self.max_retries = 1
    
    async def process(self, input_text: str) -> PipelineResult:
        """
        Process input through complete pipeline.
        
        Returns PipelineResult (STRICT JSON).
        """
        start_time = time.time()
        stages_completed: List[str] = []
        
        try:
            # ===== STAGE 1: PERCEPTION =====
            if not input_text or not input_text.strip():
                return PipelineResult(
                    status="failed",
                    intent="UNKNOWN",
                    confidence=0.0,
                    error="Empty input",
                    failed_stage=PipelineStage.PERCEPTION
                )
            
            input_text = input_text.strip()
            stages_completed.append(PipelineStage.PERCEPTION)
            
            # ===== STAGE 2: PRE-SAFETY =====
            safety_result = pre_intent_safety_check(input_text)
            if safety_result:
                # Dangerous operation detected
                self.processor.context.pending_confirmation = safety_result
                
                return PipelineResult(
                    status="confirmation_required",
                    intent="CONFIRMATION_REQUIRED",
                    confidence=1.0,
                    stages_completed=[PipelineStage.PERCEPTION, PipelineStage.PRE_SAFETY],
                    execution_result=safety_result,
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            stages_completed.append(PipelineStage.PRE_SAFETY)
            
            # ===== STAGE 3: INTENT CLASSIFICATION =====
            intent_data = classify_multi_step(input_text)
            intent = intent_data.get("intent", "UNKNOWN")
            confidence = intent_data.get("confidence", 0.0)
            
            if intent not in ALL_VALID_INTENTS:
                return PipelineResult(
                    status="failed",
                    intent="UNKNOWN",
                    confidence=0.0,
                    stages_completed=stages_completed,
                    error="Invalid intent",
                    failed_stage=PipelineStage.INTENT
                )
            
            stages_completed.append(PipelineStage.INTENT)
            
            # ===== STAGE 4: PLAN =====
            # For MULTI_STEP, plan is the ordered steps
            # For single intents, plan is just the intent
            if intent == "MULTI_STEP":
                steps = intent_data.get("steps", [])
                if not steps:
                    return PipelineResult(
                        status="failed",
                        intent="MULTI_STEP",
                        confidence=0.0,
                        stages_completed=stages_completed,
                        error="Empty multi-step plan",
                        failed_stage=PipelineStage.PLAN
                    )
            
            stages_completed.append(PipelineStage.PLAN)
            
            # ===== STAGE 5: ROUTE =====
            route = route_intent(intent_data, input_text)
            intent_data["_route"] = route.value
            
            # Check if confirmation needed for dangerous intents
            if intent in (FILE_CONTROL_INTENTS | SYSTEM_CONTROL_INTENTS):
                if intent not in ("OPEN_FILE", "VOLUME_UP", "VOLUME_DOWN", 
                                  "BRIGHTNESS_UP", "BRIGHTNESS_DOWN"):
                    # Needs confirmation
                    slots = intent_data.get("slots", {})
                    confirmation = build_confirmation_response(intent, slots)
                    self.processor.context.pending_confirmation = confirmation
                    
                    return PipelineResult(
                        status="confirmation_required",
                        intent="CONFIRMATION_REQUIRED",
                        confidence=1.0,
                        stages_completed=stages_completed + [PipelineStage.ROUTE],
                        execution_result=confirmation,
                        route=route.value,
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
            
            stages_completed.append(PipelineStage.ROUTE)
            
            # ===== STAGE 6: EXECUTE =====
            execution_result = await self.processor.execute(intent_data)
            
            if execution_result.status == "confirmation_required":
                return PipelineResult(
                    status="confirmation_required",
                    intent=intent,
                    confidence=confidence,
                    stages_completed=stages_completed,
                    execution_result=execution_result.to_dict(),
                    route=route.value,
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            if execution_result.status != "success":
                # Retry once
                retry_result = await self._retry_execution(intent_data)
                if retry_result.status != "success":
                    return PipelineResult(
                        status="failed",
                        intent=intent,
                        confidence=confidence,
                        stages_completed=stages_completed,
                        execution_result=retry_result.to_dict(),
                        error=retry_result.message,
                        failed_stage=PipelineStage.EXECUTE,
                        route=route.value,
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
                execution_result = retry_result
            
            stages_completed.append(PipelineStage.EXECUTE)
            
            # ===== STAGE 7: VERIFY =====
            slots = intent_data.get("slots", {})
            verification = await self.verifier.verify(
                intent, slots, execution_result.to_dict()
            )
            
            if not verification.verified and verification.retry_suggested:
                # Retry execution
                retry_result = await self._retry_execution(intent_data)
                verification = await self.verifier.verify(
                    intent, slots, retry_result.to_dict()
                )
                if retry_result.status == "success":
                    execution_result = retry_result
            
            stages_completed.append(PipelineStage.VERIFY)
            
            # ===== STAGE 8: MEMORY =====
            self.context_memory.record_action(
                action_type=intent,
                action_data=slots,
                result=execution_result.status,
                metadata={
                    "route": route.value,
                    "verified": verification.verified
                }
            )
            
            stages_completed.append(PipelineStage.MEMORY)
            
            # ===== COMPLETE =====
            return PipelineResult(
                status="success" if execution_result.status == "success" else "failed",
                intent=intent,
                confidence=confidence,
                stages_completed=stages_completed,
                execution_result=execution_result.to_dict(),
                verification_result=verification.to_dict(),
                route=route.value,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            logger.error(f"[PIPELINE ERROR] {e}")
            return PipelineResult(
                status="failed",
                intent="UNKNOWN",
                confidence=0.0,
                stages_completed=stages_completed,
                error=str(e),
                failed_stage=stages_completed[-1] if stages_completed else PipelineStage.PERCEPTION,
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _retry_execution(self, intent_data: Dict[str, Any]) -> ExecutionResult:
        """Retry execution once."""
        logger.info(f"[PIPELINE] Retrying execution: {intent_data.get('intent')}")
        await asyncio.sleep(0.5)  # Brief pause before retry
        return await self.processor.execute(intent_data)
    
    async def confirm_and_execute(self) -> PipelineResult:
        """
        Confirm pending action and execute.
        
        Returns PipelineResult.
        """
        start_time = time.time()
        
        confirmed = self.processor.confirm_dangerous_action()
        if not confirmed:
            return PipelineResult(
                status="failed",
                intent="UNKNOWN",
                confidence=0.0,
                error="No pending confirmation",
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Execute the confirmed intent
        route = route_intent(confirmed, "")
        confirmed["_route"] = route.value
        
        execution_result = await self.processor.execute(confirmed)
        
        # Verify
        verification = await self.verifier.verify(
            confirmed["intent"],
            confirmed.get("slots", {}),
            execution_result.to_dict()
        )
        
        # Record to memory
        self.context_memory.record_action(
            action_type=confirmed["intent"],
            action_data=confirmed.get("slots", {}),
            result=execution_result.status,
            metadata={"confirmed": True, "verified": verification.verified}
        )
        
        return PipelineResult(
            status=execution_result.status,
            intent=confirmed["intent"],
            confidence=confirmed.get("confidence", 1.0),
            stages_completed=list(PipelineStage.__dict__.values())[:8],
            execution_result=execution_result.to_dict(),
            verification_result=verification.to_dict(),
            route=route.value,
            execution_time_ms=(time.time() - start_time) * 1000
        )
    
    def get_pending_confirmation(self) -> Optional[Dict[str, Any]]:
        """Get pending confirmation if any."""
        return self.processor.context.pending_confirmation
    
    def cancel_confirmation(self) -> bool:
        """Cancel pending confirmation."""
        if self.processor.context.pending_confirmation:
            self.processor.context.clear_confirmation()
            return True
        return False


# =============================================================================
# SINGLETON PIPELINE
# =============================================================================

_pipeline_instance: Optional[UnifiedPipeline] = None


def get_pipeline() -> UnifiedPipeline:
    """Get singleton pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = UnifiedPipeline()
    return _pipeline_instance


def reset_pipeline() -> None:
    """Reset pipeline instance."""
    global _pipeline_instance
    _pipeline_instance = None


# =============================================================================
# PUBLIC API - STRICT JSON OUTPUT
# =============================================================================

async def process(input_text: str) -> str:
    """
    Process input through complete pipeline.
    
    Returns STRICT JSON string.
    
    NO TEXT. NO EXPLANATION. NO MARKDOWN.
    """
    pipeline = get_pipeline()
    result = await pipeline.process(input_text)
    return result.to_json()


async def confirm() -> str:
    """
    Confirm pending action and execute.
    
    Returns STRICT JSON string.
    """
    pipeline = get_pipeline()
    result = await pipeline.confirm_and_execute()
    return result.to_json()


def cancel() -> str:
    """
    Cancel pending confirmation.
    
    Returns STRICT JSON string.
    """
    pipeline = get_pipeline()
    cancelled = pipeline.cancel_confirmation()
    return json.dumps({
        "status": "cancelled" if cancelled else "no_pending",
        "cancelled": cancelled
    })


def get_status() -> str:
    """
    Get current pipeline status.
    
    Returns STRICT JSON string.
    """
    pipeline = get_pipeline()
    pending = pipeline.get_pending_confirmation()
    context = get_session_context()
    
    return json.dumps({
        "has_pending_confirmation": pending is not None,
        "pending_intent": pending.get("original_intent") if pending else None,
        "current_app": context.current_app,
        "browser_active": context.browser_active,
        "last_action": context.last_action
    })


# =============================================================================
# SYNCHRONOUS WRAPPERS
# =============================================================================

def process_sync(input_text: str) -> str:
    """Synchronous wrapper for process."""
    return asyncio.run(process(input_text))


def confirm_sync() -> str:
    """Synchronous wrapper for confirm."""
    return asyncio.run(confirm())


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Pipeline
    "UnifiedPipeline",
    "PipelineResult",
    "PipelineStage",
    "get_pipeline",
    "reset_pipeline",
    
    # Public API
    "process",
    "confirm",
    "cancel",
    "get_status",
    
    # Sync wrappers
    "process_sync",
    "confirm_sync",
]
