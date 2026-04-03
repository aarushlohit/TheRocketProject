"""
Stage 3 — Intelligent Pipeline Integration.

This module integrates all Stage 3 components into the existing
execution engine, providing the complete intelligent pipeline:

Reactive Executor → Intelligent Planner + Executor

Pipeline Flow:
1. Receive intent (from vision model or direct)
2. refine_intent() - normalize and fix
3. plan_execution() - create execution plan
4. validate_plan() - guardrails check
5. execute_plan() - step-by-step execution with self-correction
6. verify - execution verification
7. send result - via WebSocket

Usage:
    from agent.core.intelligent_pipeline import IntelligentPipeline
    
    pipeline = IntelligentPipeline(platform, websocket_callback)
    result = await pipeline.process(intent_json)
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, Optional

from agent.core.intent_refiner import IntentRefiner, refine_intent, get_intent_refiner
from agent.core.planner import (
    ExecutionPlanner, 
    ExecutionPlan, 
    ExecutionStep,
    plan_execution,
    get_execution_planner,
)
from agent.core.context_memory import ContextMemory, get_context_memory
from agent.core.smart_delays import SmartDelays, get_smart_delays, DelayType
from agent.core.guardrails import (
    ExecutionGuardrails,
    get_guardrails,
    validate_plan,
    GuardrailResult,
)
from agent.core.self_correction import (
    SelfCorrection,
    get_self_correction,
    self_correct,
    CorrectionStrategy,
)
from agent.core.execution_controller import (
    ExecutionController,
    PlanExecutionResult,
    get_execution_controller,
)
from agent.core.feedback import FeedbackSender
from agent.core.user_profile import UserProfile, get_or_create_profile
from agent.platform.adapter import PlatformAdapter
from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# PIPELINE RESULT
# =============================================================================

class PipelineResult:
    """Complete result from intelligent pipeline."""
    
    def __init__(
        self,
        status: str,
        message: str,
        plan_result: Optional[PlanExecutionResult] = None,
        original_intent: Optional[Dict[str, Any]] = None,
        refined_intent: Optional[Dict[str, Any]] = None,
        plan: Optional[ExecutionPlan] = None,
        guard_result: Optional[GuardrailResult] = None,
        execution_time: float = 0.0,
    ):
        self.status = status
        self.message = message
        self.plan_result = plan_result
        self.original_intent = original_intent
        self.refined_intent = refined_intent
        self.plan = plan
        self.guard_result = guard_result
        self.execution_time = execution_time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "execution_time": self.execution_time,
            "plan_result": self.plan_result.to_dict() if self.plan_result else None,
            "original_intent": self.original_intent,
            "refined_intent": self.refined_intent,
            "plan": self.plan.to_dict() if self.plan else None,
            "guard_result": self.guard_result.to_dict() if self.guard_result else None,
        }
    
    def to_websocket_message(self) -> Dict[str, Any]:
        return {
            "type": "pipeline_result",
            "status": self.status,
            "message": self.message,
            "execution_time": self.execution_time,
            "completed_steps": self.plan_result.completed_steps if self.plan_result else 0,
            "total_steps": self.plan_result.total_steps if self.plan_result else 0,
            "failed_step": self.plan_result.failed_step if self.plan_result else None,
            "failed_reason": self.plan_result.failed_reason if self.plan_result else None,
        }


# =============================================================================
# INTELLIGENT PIPELINE
# =============================================================================

class IntelligentPipeline:
    """
    Complete intelligent execution pipeline.
    
    Integrates all Stage 3 components:
    - Intent refinement
    - Execution planning
    - Context memory
    - Smart delays
    - Guardrails
    - Self-correction
    - Execution control
    - Accessibility feedback
    
    This is the main entry point for Stage 3 intelligent execution.
    """
    
    def __init__(
        self,
        platform: PlatformAdapter,
        websocket_callback: Optional[Callable[[dict], Any]] = None,
        user_profile: Optional[UserProfile] = None,
    ):
        self.platform = platform
        self.websocket_callback = websocket_callback
        self.profile = user_profile or get_or_create_profile()
        
        # Initialize all components
        self.refiner = get_intent_refiner()
        self.planner = get_execution_planner()
        self.context = get_context_memory()
        self.delays = get_smart_delays()
        self.guardrails = get_guardrails()
        self.corrector = get_self_correction()
        
        # Feedback for accessibility
        self.feedback = FeedbackSender(
            profile=self.profile,
            websocket_callback=websocket_callback,
        )
        
        # Execution controller
        self.controller = ExecutionController(
            platform=platform,
            feedback=self.feedback,
            websocket_callback=websocket_callback,
            user_profile=self.profile,
        )
        
        print(f"\n========== [INTELLIGENT PIPELINE INITIALIZED] ==========")
        print(f"[PLATFORM] {type(platform).__name__}")
        print(f"[PROFILE] {self.profile.get_feedback_mode()}")
    
    def set_websocket_callback(self, callback: Callable[[dict], Any]):
        """Set WebSocket callback for all components."""
        self.websocket_callback = callback
        self.feedback.websocket_callback = callback
        self.controller.set_websocket_callback(callback)
    
    def update_profile(self, profile: UserProfile):
        """Update user profile for all components (UNIFIED)."""
        self.profile = profile
        self.feedback.update_profile(profile)
        if hasattr(self.controller, 'profile'):
            self.controller.profile = profile
        if hasattr(self.controller, 'feedback'):
            self.controller.feedback.update_profile(profile)
    
    # =========================================================================
    # MAIN PIPELINE
    # =========================================================================
    
    async def process(self, intent_data: Dict[str, Any]) -> PipelineResult:
        """
        Process an intent through the complete intelligent pipeline.
        
        Pipeline:
        1. Log input
        2. Refine intent
        3. Enrich with context
        4. Create plan
        5. Validate with guardrails
        6. Execute plan
        7. Return result
        
        Args:
            intent_data: Raw intent JSON from model
            
        Returns:
            PipelineResult with full execution details
        """
        start_time = time.time()
        
        print(f"\n{'='*70}")
        print(f"========== [INTELLIGENT PIPELINE START] ==========")
        print(f"{'='*70}")
        
        original_intent = intent_data.copy()
        
        try:
            # ================================================================
            # STEP 1: Validate input
            # ================================================================
            print(f"\n[PIPELINE STEP 1] Input validation")
            
            if not intent_data:
                return self._error_result("Empty intent data", start_time)
            
            if intent_data.get("status") == "error":
                error_msg = intent_data.get("message", "Model error")
                self.feedback.send_error(f"Model error: {error_msg}")
                return self._error_result(error_msg, start_time, original_intent)
            
            intent_type = intent_data.get("intent", "UNKNOWN")
            if intent_type == "UNKNOWN":
                self.feedback.send_warning("Could not understand command")
                return self._error_result("Unknown intent", start_time, original_intent)
            
            print(f"[INPUT] {intent_type}: {intent_data.get('slots')}")
            print(f"[CONFIDENCE] {intent_data.get('confidence', 0)}")
            
            # ================================================================
            # STEP 2: Notify start
            # ================================================================
            print(f"\n[PIPELINE STEP 2] Notify start")
            self.feedback.send_info("Processing command...")
            await self._send_websocket({
                "type": "pipeline_start",
                "intent": intent_type,
            })
            
            # ================================================================
            # STEP 3: Refine intent
            # ================================================================
            print(f"\n[PIPELINE STEP 3] Intent refinement")
            refined = self.refiner.refine(intent_data)
            print(f"[REFINED] {refined.get('intent')}: {refined.get('slots')}")
            
            # ================================================================
            # STEP 4: Context enrichment
            # ================================================================
            print(f"\n[PIPELINE STEP 4] Context enrichment")
            enriched = self.context.enrich_intent(refined)
            context_info = enriched.get("_context", {})
            print(f"[CONTEXT] last_app={context_info.get('last_app')}, last_browser={context_info.get('last_browser')}")
            
            # ================================================================
            # STEP 5: Create execution plan
            # ================================================================
            print(f"\n[PIPELINE STEP 5] Execution planning")
            plan = self.planner.plan(enriched)
            print(f"[PLAN CREATED] {len(plan)} steps")
            
            for i, step in enumerate(plan.steps):
                print(f"  [{i+1}] {step.intent}: {step.slots}")
            
            # ================================================================
            # STEP 6: Guardrails validation
            # ================================================================
            print(f"\n[PIPELINE STEP 6] Guardrails validation")
            guard_result = self.guardrails.validate_plan(plan)
            
            if not guard_result.passed:
                error_msg = f"Plan blocked: {guard_result.issues}"
                self.feedback.send_error(error_msg)
                await self._send_websocket({
                    "type": "guardrails_blocked",
                    "issues": guard_result.issues,
                })
                
                return PipelineResult(
                    status="blocked",
                    message=error_msg,
                    original_intent=original_intent,
                    refined_intent=refined,
                    plan=plan,
                    guard_result=guard_result,
                    execution_time=time.time() - start_time,
                )
            
            if guard_result.warnings:
                for warning in guard_result.warnings:
                    print(f"[WARNING] {warning}")
                    self.feedback.send_warning(warning)
            
            print(f"[GUARDRAILS] PASSED ✓")
            
            # ================================================================
            # STEP 7: Execute plan
            # ================================================================
            print(f"\n[PIPELINE STEP 7] Plan execution")
            self.feedback.send_executing(f"Executing {len(plan)} step(s)...")
            
            plan_result = await self.controller._execute_plan(plan)
            
            # ================================================================
            # STEP 8: Final result
            # ================================================================
            print(f"\n[PIPELINE STEP 8] Final result")
            
            elapsed = time.time() - start_time
            
            if plan_result.status == "success":
                message = f"Completed {plan_result.completed_steps} steps in {elapsed:.1f}s"
                self.feedback.send_complete(message)
                print(f"[SUCCESS] {message}")
            else:
                message = f"Failed at step {plan_result.failed_step}: {plan_result.failed_reason}"
                self.feedback.send_error(message)
                print(f"[FAILED] {message}")
            
            result = PipelineResult(
                status=plan_result.status,
                message=message,
                plan_result=plan_result,
                original_intent=original_intent,
                refined_intent=refined,
                plan=plan,
                guard_result=guard_result,
                execution_time=elapsed,
            )
            
            # Send final result via WebSocket
            await self._send_websocket(result.to_websocket_message())
            
            print(f"\n[PIPELINE COMPLETE] Status: {result.status}")
            print(f"{'='*70}")
            
            return result
            
        except Exception as e:
            logger.error(f"[PIPELINE ERROR] {e}")
            self.feedback.send_error(f"Pipeline error: {e}")
            
            return self._error_result(str(e), start_time, original_intent)
    
    def _error_result(
        self,
        message: str,
        start_time: float,
        original_intent: Optional[Dict] = None,
    ) -> PipelineResult:
        """Create error result."""
        return PipelineResult(
            status="failed",
            message=message,
            original_intent=original_intent,
            execution_time=time.time() - start_time,
        )
    
    async def _send_websocket(self, message: dict):
        """Send message via WebSocket."""
        if self.websocket_callback:
            if asyncio.iscoroutinefunction(self.websocket_callback):
                await self.websocket_callback(message)
            else:
                self.websocket_callback(message)
    
    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================
    
    def get_context(self) -> Dict[str, Any]:
        """Get current execution context."""
        return self.context.get_context()
    
    def clear_context(self):
        """Clear session context."""
        self.context.clear_session()
        self.corrector.reset_retry_counts()
        self.guardrails.reset_retry_count()
    
    def get_status(self) -> Dict[str, Any]:
        """Get pipeline status."""
        return {
            "is_executing": self.controller.is_executing,
            "context": self.get_context(),
            "current_plan": self.controller.current_plan.to_dict() if self.controller.current_plan else None,
        }


# =============================================================================
# SINGLETON AND FACTORY
# =============================================================================

_pipeline_instance: Optional[IntelligentPipeline] = None


def get_intelligent_pipeline(
    platform: Optional[PlatformAdapter] = None,
    websocket_callback: Optional[Callable] = None,
) -> Optional[IntelligentPipeline]:
    """Get or create IntelligentPipeline instance."""
    global _pipeline_instance
    
    if _pipeline_instance is None and platform is not None:
        _pipeline_instance = IntelligentPipeline(
            platform=platform,
            websocket_callback=websocket_callback,
        )
    
    return _pipeline_instance


def init_intelligent_pipeline(
    platform: PlatformAdapter,
    websocket_callback: Optional[Callable] = None,
    user_profile: Optional[UserProfile] = None,
) -> IntelligentPipeline:
    """Initialize IntelligentPipeline (replaces singleton)."""
    global _pipeline_instance
    
    _pipeline_instance = IntelligentPipeline(
        platform=platform,
        websocket_callback=websocket_callback,
        user_profile=user_profile,
    )
    
    return _pipeline_instance


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Main classes
    "PipelineResult",
    "IntelligentPipeline",
    
    # Factory functions
    "get_intelligent_pipeline",
    "init_intelligent_pipeline",
    
    # Re-exports for convenience
    "IntentRefiner",
    "refine_intent",
    "ExecutionPlanner",
    "plan_execution",
    "ContextMemory",
    "get_context_memory",
    "SmartDelays",
    "get_smart_delays",
    "ExecutionGuardrails",
    "validate_plan",
    "SelfCorrection",
    "self_correct",
    "ExecutionController",
    "PlanExecutionResult",
]
