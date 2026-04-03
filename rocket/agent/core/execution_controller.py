"""
Stage 3 — Execution Controller Module.

Orchestrates multi-step plan execution:
- Step-by-step execution
- Self-correction integration
- Context memory updates
- Accessibility feedback
- WebSocket notifications
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from agent.core.planner import ExecutionPlan, ExecutionStep, plan_execution
from agent.core.intent_refiner import refine_intent
from agent.core.context_memory import ContextMemory, get_context_memory
from agent.core.smart_delays import SmartDelays, get_smart_delays, DelayType
from agent.core.guardrails import ExecutionGuardrails, get_guardrails, GuardrailResult
from agent.core.self_correction import (
    SelfCorrection,
    get_self_correction,
    CorrectionStrategy,
    CorrectionResult,
)
from agent.core.feedback import FeedbackSender
from agent.core.user_profile import UserProfile, get_or_create_profile
from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# PLAN EXECUTION RESULT
# =============================================================================

@dataclass
class PlanExecutionResult:
    """Result of executing an entire plan."""
    
    status: str  # success, partial, failed
    completed_steps: int
    total_steps: int
    failed_step: Optional[int]
    failed_reason: Optional[str]
    results: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "failed_step": self.failed_step,
            "failed_reason": self.failed_reason,
            "results": self.results,
        }
    
    def to_websocket_message(self) -> Dict[str, Any]:
        return {
            "type": "plan_result",
            **self.to_dict(),
        }


# =============================================================================
# EXECUTION CONTROLLER
# =============================================================================

class ExecutionController:
    """
    Orchestrates intelligent plan execution.
    
    Pipeline:
    1. Receive intent
    2. Refine intent
    3. Create execution plan
    4. Validate with guardrails
    5. Execute each step with:
       - Start notification
       - Execution
       - Verification
       - Self-correction on failure
       - Context memory update
       - Result notification
    6. Return final result
    """
    
    def __init__(
        self,
        platform,  # PlatformAdapter
        feedback: Optional[FeedbackSender] = None,
        websocket_callback: Optional[Callable[[dict], Any]] = None,
        user_profile: Optional[UserProfile] = None,
    ):
        self.platform = platform
        self.profile = user_profile or get_or_create_profile()
        self.websocket_callback = websocket_callback
        
        # Initialize components
        self.feedback = feedback or FeedbackSender(
            profile=self.profile,
            websocket_callback=websocket_callback,
        )
        self.context = get_context_memory()
        self.delays = get_smart_delays()
        self.guardrails = get_guardrails()
        self.corrector = get_self_correction()
        
        # Execution state
        self.current_plan: Optional[ExecutionPlan] = None
        self.is_executing = False
    
    def set_websocket_callback(self, callback: Callable[[dict], Any]):
        """Set WebSocket callback."""
        self.websocket_callback = callback
        self.feedback.websocket_callback = callback
    
    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================
    
    async def execute(self, intent_data: Dict[str, Any]) -> PlanExecutionResult:
        """
        Main entry point: Execute an intent.
        
        Full pipeline:
        1. Refine intent
        2. Create plan
        3. Validate plan
        4. Execute plan
        5. Return result
        
        Args:
            intent_data: Raw intent JSON from model
            
        Returns:
            PlanExecutionResult
        """
        print(f"\n{'='*60}")
        print(f"========== [EXECUTION CONTROLLER] ==========")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Step 1: Notify planning start
            await self._notify("Planning actions...")
            self.feedback.send_info("Planning actions...")
            
            # Step 2: Refine intent
            print(f"\n[STEP 1] Refining intent...")
            refined = refine_intent(intent_data)
            print(f"[REFINED] {refined.get('intent')}: {refined.get('slots')}")
            
            # Step 3: Enrich with context
            print(f"\n[STEP 2] Enriching with context...")
            enriched = self.context.enrich_intent(refined)
            
            # Step 4: Create plan
            print(f"\n[STEP 3] Creating execution plan...")
            plan = plan_execution(enriched)
            self.current_plan = plan
            print(f"[PLAN] {len(plan)} steps created")
            
            # Step 5: Validate with guardrails
            print(f"\n[STEP 4] Validating with guardrails...")
            guard_result = self.guardrails.validate_plan(plan)
            
            if not guard_result.passed:
                await self._notify_error(f"Plan validation failed: {guard_result.issues}")
                return PlanExecutionResult(
                    status="failed",
                    completed_steps=0,
                    total_steps=len(plan),
                    failed_step=None,
                    failed_reason=f"Guardrails: {guard_result.issues}",
                    results=[],
                )
            
            if guard_result.warnings:
                print(f"[WARNINGS] {guard_result.warnings}")
            
            # Step 6: Execute plan
            print(f"\n[STEP 5] Executing plan...")
            result = await self._execute_plan(plan)
            
            # Step 7: Final notification
            elapsed = time.time() - start_time
            if result.status == "success":
                await self._notify(f"Completed {result.completed_steps} steps in {elapsed:.1f}s")
                self.feedback.send_complete(f"All {result.completed_steps} steps completed")
            else:
                await self._notify(f"Execution failed at step {result.failed_step}: {result.failed_reason}")
                self.feedback.send_error(f"Failed: {result.failed_reason}")
            
            # Send result via WebSocket
            await self._send_websocket(result.to_websocket_message())
            
            return result
            
        except Exception as e:
            logger.error(f"[CONTROLLER] Execution error: {e}")
            self.feedback.send_error(str(e))
            
            return PlanExecutionResult(
                status="failed",
                completed_steps=0,
                total_steps=0,
                failed_step=None,
                failed_reason=str(e),
                results=[],
            )
    
    # =========================================================================
    # PLAN EXECUTION
    # =========================================================================
    
    async def _execute_plan(self, plan: ExecutionPlan) -> PlanExecutionResult:
        """Execute all steps in a plan."""
        self.is_executing = True
        plan.status = "executing"
        results = []
        
        # Reset correction retry counts
        self.corrector.reset_retry_counts()
        self.guardrails.reset_retry_count()
        
        print(f"\n========== [PLAN EXECUTION] ==========")
        print(f"[TOTAL STEPS] {len(plan)}")
        
        for i, step in enumerate(plan.steps):
            print(f"\n--- Step {i+1}/{len(plan)} ---")
            
            # Notify step start
            await self._notify_step_start(i, step)
            
            # Execute step with retry logic
            step_result = await self._execute_step_with_correction(step, i)
            results.append(step_result)
            
            # Check result
            if step_result.get("status") == "success":
                plan.mark_step_success()
                await self._notify_step_complete(i, step)
                
                # Update context memory
                self.context.record_action(
                    action_type=step.intent,
                    action_data=step.slots,
                    result="success",
                )
                
                # Wait between steps
                await self.delays.async_wait(DelayType.BETWEEN_STEPS)
                
            else:
                plan.mark_step_failed(step_result.get("error", "Unknown error"))
                await self._notify_step_failed(i, step, step_result.get("error", ""))
                
                # Record failure in context
                self.context.record_action(
                    action_type=step.intent,
                    action_data=step.slots,
                    result="failed",
                    metadata={"error": step_result.get("error")},
                )
                
                # Stop execution
                self.is_executing = False
                plan.status = "failed"
                
                return PlanExecutionResult(
                    status="failed",
                    completed_steps=i,
                    total_steps=len(plan),
                    failed_step=i,
                    failed_reason=step_result.get("error"),
                    results=results,
                )
            
            plan.advance()
        
        self.is_executing = False
        plan.status = "completed"
        
        return PlanExecutionResult(
            status="success",
            completed_steps=len(plan),
            total_steps=len(plan),
            failed_step=None,
            failed_reason=None,
            results=results,
        )
    
    async def _execute_step_with_correction(
        self,
        step: ExecutionStep,
        step_index: int,
    ) -> Dict[str, Any]:
        """Execute a step with self-correction on failure."""
        current_step = step
        
        while True:
            # Execute the step
            result = await self._execute_single_step(current_step)
            
            if result.get("status") == "success":
                return result
            
            # Step failed - attempt correction
            print(f"\n[STEP FAILED] {result.get('error')}")
            
            # Get correction strategy
            correction = self.corrector.correct(
                step={"intent": current_step.intent, "slots": current_step.slots},
                error=result.get("error", "Unknown error"),
                step_index=step_index,
            )
            
            print(f"[CORRECTION] {correction.strategy.value}: {correction.message}")
            
            # Check if we can retry
            if not correction.can_retry:
                print(f"[NO RETRY] {correction.message}")
                return result
            
            # Apply correction strategy
            if correction.strategy == CorrectionStrategy.ABORT:
                return result
            
            # Notify retry
            retry_count = self.corrector.get_retry_count(step_index)
            await self._notify_retry(step_index, retry_count, correction.message)
            
            # Apply delay
            if correction.delay > 0:
                print(f"[WAITING] {correction.delay}s before retry")
                await asyncio.sleep(correction.delay)
            
            # Update step if modified
            if correction.modified_step:
                current_step = ExecutionStep(
                    intent=correction.modified_step.get("intent", current_step.intent),
                    slots=correction.modified_step.get("slots", current_step.slots),
                    confidence=current_step.confidence,
                    index=step_index,
                )
                current_step.retries = retry_count
                print(f"[MODIFIED STEP] {current_step.intent}: {current_step.slots}")
    
    async def _execute_single_step(self, step: ExecutionStep) -> Dict[str, Any]:
        """Execute a single step."""
        intent = step.intent
        slots = step.slots
        
        print(f"[EXECUTE] {intent}: {slots}")
        
        try:
            # Dispatch to appropriate handler
            if intent == "OPEN_APP":
                result = await self.platform.open_app(slots.get("app", ""))
                
                # Wait for app to launch
                app = slots.get("app", "")
                await self.delays.async_wait(DelayType.APP_LAUNCH, {"app": app})
                
                if result.get("status") == "success":
                    return {"status": "success", "message": f"Opened {app}"}
                else:
                    return {"status": "failed", "error": f"Failed to open {app}"}
            
            elif intent == "OPEN_URL":
                url = slots.get("url", "")
                result = await self.platform.open_url(url)
                
                await self.delays.async_wait(DelayType.URL_LOAD)
                
                if result.get("status") == "success":
                    return {"status": "success", "message": f"Opened {url}"}
                else:
                    return {"status": "failed", "error": f"Failed to open {url}"}
            
            elif intent == "SEARCH_WEB":
                query = slots.get("query", "")
                
                # Check if we should reopen browser
                if slots.get("_reopen_browser"):
                    browser = self.context.get_last_browser()
                    await self.platform.open_app(browser)
                    await self.delays.async_wait(DelayType.BROWSER_LAUNCH, {"app": browser})
                
                result = await self.platform.search_web(query)
                
                await self.delays.async_wait(DelayType.SEARCH_LOAD)
                
                if result.get("status") == "success":
                    return {"status": "success", "message": f"Searched: {query}"}
                else:
                    return {"status": "failed", "error": "Search failed"}
            
            elif intent == "TYPE_TEXT":
                text = slots.get("text", "")
                slow_mode = slots.get("_slow_mode", False)
                
                # Get typing delay
                delay = self.delays.get_delay(
                    DelayType.TYPING,
                    {"text_length": len(text), "slow_mode": slow_mode}
                )
                
                result = await self.platform.type_text(text, delay=delay)
                
                if result.get("status") == "success":
                    return {"status": "success", "message": f"Typed {len(text)} chars"}
                else:
                    return {"status": "failed", "error": "Type failed"}
            
            elif intent == "PRESS_KEYS":
                keys = slots.get("keys", "")
                if isinstance(keys, str):
                    keys = keys.split("+")
                
                result = await self.platform.press_keys(keys)
                
                if result.get("status") == "success":
                    return {"status": "success", "message": f"Pressed {'+'.join(keys)}"}
                else:
                    return {"status": "failed", "error": "Key press failed"}
            
            elif intent == "SCREENSHOT":
                from pathlib import Path
                output_dir = Path(slots.get("output_dir", "./screenshots"))
                result = await self.platform.screenshot(output_dir)
                return {"status": "success", "message": "Screenshot taken", "path": str(result)}
            
            elif intent == "CLOSE_APP":
                app = slots.get("app")
                result = await self.platform.close_app(app)
                if result.get("status") == "success":
                    return {"status": "success", "message": f"Closed {app or 'window'}"}
                else:
                    return {"status": "failed", "error": "Close failed"}
            
            elif intent == "MINIMIZE":
                result = await self.platform.minimize()
                return {"status": "success", "message": "Window minimized"}
            
            elif intent == "MAXIMIZE":
                result = await self.platform.maximize()
                return {"status": "success", "message": "Window maximized"}
            
            elif intent == "SCROLL":
                direction = slots.get("direction", "down")
                amount = slots.get("amount", 3)
                result = await self.platform.scroll(direction, amount)
                return {"status": "success", "message": f"Scrolled {direction}"}
            
            else:
                return {"status": "failed", "error": f"Unknown intent: {intent}"}
                
        except Exception as e:
            logger.error(f"[STEP ERROR] {e}")
            return {"status": "failed", "error": str(e)}
    
    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================
    
    async def _notify(self, message: str):
        """Send general notification."""
        print(f"[NOTIFY] {message}")
        await self._send_websocket({
            "type": "notification",
            "message": message,
        })
    
    async def _notify_error(self, message: str):
        """Send error notification."""
        print(f"[ERROR NOTIFY] {message}")
        self.feedback.send_error(message)
        await self._send_websocket({
            "type": "error",
            "message": message,
        })
    
    async def _notify_step_start(self, index: int, step: ExecutionStep):
        """Notify step start."""
        total = len(self.current_plan) if self.current_plan else 0
        message = f"Executing step {index + 1}/{total}: {step.intent}"
        
        print(f"[STEP START] {message}")
        self.feedback.send_executing(message)
        
        await self._send_websocket({
            "type": "step_start",
            "step": index,
            "total": total,
            "intent": step.intent,
            "slots": step.slots,
        })
    
    async def _notify_step_complete(self, index: int, step: ExecutionStep):
        """Notify step completion."""
        message = f"Step {index + 1} completed: {step.intent}"
        
        print(f"[STEP COMPLETE] {message}")
        self.feedback.send_success(message)
        
        await self._send_websocket({
            "type": "step_result",
            "step": index,
            "status": "success",
            "intent": step.intent,
        })
    
    async def _notify_step_failed(self, index: int, step: ExecutionStep, error: str):
        """Notify step failure."""
        message = f"Step {index + 1} failed: {error}"
        
        print(f"[STEP FAILED] {message}")
        self.feedback.send_error(message)
        
        await self._send_websocket({
            "type": "step_result",
            "step": index,
            "status": "failed",
            "intent": step.intent,
            "error": error,
        })
    
    async def _notify_retry(self, index: int, retry_count: int, reason: str):
        """Notify retry attempt."""
        message = f"Retrying step {index + 1} (attempt {retry_count + 1}): {reason}"
        
        print(f"[RETRY] {message}")
        self.feedback.send_warning(message)
        
        await self._send_websocket({
            "type": "retry",
            "step": index,
            "attempt": retry_count + 1,
            "reason": reason,
        })
    
    async def _send_websocket(self, message: dict):
        """Send message via WebSocket."""
        if self.websocket_callback:
            if asyncio.iscoroutinefunction(self.websocket_callback):
                await self.websocket_callback(message)
            else:
                self.websocket_callback(message)


# =============================================================================
# SINGLETON AND CONVENIENCE
# =============================================================================

_controller_instance: Optional[ExecutionController] = None


def get_execution_controller(
    platform=None,
    feedback: Optional[FeedbackSender] = None,
    websocket_callback: Optional[Callable] = None,
) -> ExecutionController:
    """Get or create ExecutionController instance."""
    global _controller_instance
    
    if _controller_instance is None and platform is not None:
        _controller_instance = ExecutionController(
            platform=platform,
            feedback=feedback,
            websocket_callback=websocket_callback,
        )
    
    return _controller_instance


async def execute_plan(
    intent_data: Dict[str, Any],
    platform=None,
    websocket_callback: Optional[Callable] = None,
) -> PlanExecutionResult:
    """
    Convenience function to execute an intent.
    
    Args:
        intent_data: Intent JSON from model
        platform: PlatformAdapter instance
        websocket_callback: Optional WebSocket callback
        
    Returns:
        PlanExecutionResult
    """
    controller = get_execution_controller(platform, websocket_callback=websocket_callback)
    if controller is None:
        raise RuntimeError("ExecutionController not initialized - provide platform")
    
    return await controller.execute(intent_data)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "PlanExecutionResult",
    "ExecutionController",
    "get_execution_controller",
    "execute_plan",
]
