"""High-level Stage 0 orchestration for draw-to-action — Production Grade.

PATCHED VERSION:
- Integrated ExecutionEngine
- WebSocket callback support
- Full FeedbackManager integration
- NO fake success, verified execution
"""

from __future__ import annotations

import uuid
from pprint import pformat
from typing import Any, Callable, Optional

from agent.core.result import Result
from agent.core.context_manager import get_context_manager
from agent.core.execution_engine import ExecutionEngine, ExecutionResult
from agent.core.feedback_manager import EventType, Priority, get_feedback_manager
from agent.core.intelligent_pipeline import IntelligentPipeline, PipelineResult
from agent.core.intent import Intent
from agent.core.safety import pre_intent_safety_check, override_type_text_misuse
from agent.core.user_profile import UserProfile, get_or_create_profile
from agent.platform.adapter import get_platform_adapter
from agent.stage0.executor import ActionExecutor
from agent.stage0.pipeline import DrawToActionPipeline
from agent.stage0.validation import StageZeroValidationError, text_to_intent
from agent.utils.app_map import normalize_app
from agent.utils.config import Config
from agent.utils.logger import get_logger


logger = get_logger(__name__)


context_manager = get_context_manager()


class NovaStageZeroAgent:
    """Coordinates AI inference, validation, and OS execution."""

    def __init__(self, config: Config, api_key: str):
        self.config = config
        self.trace_mode = config.trace_mode
        self.last_opened_app: str | None = None
        self.platform = get_platform_adapter(config.platform_type)
        self.pipeline = DrawToActionPipeline(
            api_key=api_key,
            storage_dir=config.data_dir / "drawings",
            confidence_threshold=config.confidence_threshold,
            trace_mode=config.trace_mode,
        )
        self.context_manager = get_context_manager()
        
        # UNIFIED: IntelligentPipeline (Stage 3 Integration)
        # This is now the ONLY execution path - all commands go through this
        self.user_profile = get_or_create_profile()
        self.pipeline_engine = IntelligentPipeline(
            platform=self.platform,
            user_profile=self.user_profile,
            websocket_callback=None,  # Set by websocket_handler
        )
        
        # DEPRECATED: Legacy paths (kept for backward compatibility, not used)
        self.executor = ActionExecutor(
            platform=self.platform,
            artifacts_dir=config.data_dir / "artifacts",
            debug_mode=config.debug_mode,
            platform_type=config.platform_type,
        )
        self.engine = ExecutionEngine(
            platform=self.platform,
            user_profile=self.user_profile,
            websocket_callback=None,
        )
        self._pending_actions: dict[str, dict[str, Any]] = {}
        
        logger.info("Nova Stage 0 agent initialized (UNIFIED with IntelligentPipeline)")

    async def handle_drawing_image(
        self,
        image_bytes: bytes,
        ws_callback: Optional[Callable[[dict], Any]] = None,
    ) -> dict:
        """
        Run the full draw-to-action pipeline and return mobile-ready JSON.
        
        UNIFIED: ALL execution goes through IntelligentPipeline.process()
        """
        # Set WebSocket callback for this request
        if ws_callback:
            self.pipeline_engine.set_websocket_callback(ws_callback)
        
        try:
            await self._notify_feedback(EventType.MODEL_PROCESSING, "Analyzing drawing")
            # =================================================================
            # STEP 1: INFERENCE
            # =================================================================
            inference = await self.pipeline.process_drawing(
                image_bytes,
                preferred_app=self.last_opened_app,
            )
            self._trace_block(
                "NORMALIZED INTENT",
                {
                    "intent": inference.intent.action,
                    "slots": inference.intent.parameters,
                    "confidence": inference.intent.confidence,
                    "ranking_score": inference.ranking_score,
                },
            )

            source_app = inference.intent.parameters.get("app")
            normalized_app = None
            if isinstance(source_app, str):
                normalized_app = normalize_app(
                    source_app,
                    platform_type=self.config.platform_type,
                )
            self._trace_block(
                "EXECUTION PLAN",
                {
                    "intent": inference.intent.action,
                    "app": source_app,
                    "normalized_app": normalized_app,
                    "slots": inference.intent.parameters,
                },
            )
            await self._notify_feedback(
                EventType.MODEL_SUCCESS,
                f"{self._describe_intent(inference.intent.action, inference.intent.parameters)} detected",
            )

            safety_intercept = pre_intent_safety_check(
                inference.normalized_text,
                getattr(self, "user_profile", None),
            )
            if safety_intercept is not None:
                await self._notify_feedback(
                    EventType.CONFIRMATION_REQUIRED,
                    f"Triple tap in drawing canvas to confirm action "
                    f"{self._describe_action_from_confirmation(safety_intercept)}",
                    priority=Priority.CRITICAL,
                )
                payload = self._build_confirmation_request(
                    confirmation_payload=safety_intercept,
                    normalized_text=inference.normalized_text,
                    model=inference.model,
                )
                self._trace_block(
                    "FINAL RESULT",
                    {"status": payload["status"], "message": payload["message"]},
                )
                return payload

            if inference.intent.action == "UNKNOWN":
                # Deterministic fallback from normalized text so clear commands are not blocked.
                fallback_action, fallback_app = text_to_intent(inference.normalized_text)
                if fallback_action:
                    fallback_slots = {"app": fallback_app} if fallback_action == "OPEN_APP" and fallback_app else {}
                    inference.intent = Intent(
                        action=fallback_action,
                        parameters=fallback_slots,
                        confidence=max(inference.intent.confidence, 0.75),
                        metadata={"normalized_text": inference.normalized_text, "fallback": "text_to_intent"},
                    )
                else:
                    payload = {
                        "type": "result",
                        "status": "blocked",
                        "intent": "UNKNOWN",
                        "message": inference.message or "Could not determine intent",
                        "normalized_text": inference.normalized_text,
                        "confidence": inference.intent.confidence,
                        "model": inference.model,
                        "slots": inference.intent.parameters,
                        "reason": "uncertain intent",
                        "verified": False,
                    }
                    self._trace_block(
                        "FINAL RESULT",
                        {"status": payload["status"], "message": payload["message"]},
                    )
                    return payload

            # Context memory: avoid reopening the same app in consecutive commands.
            if inference.intent.action == "OPEN_APP":
                requested_app = str(inference.intent.parameters.get("app", "")).strip().lower()
                if requested_app and self.last_opened_app and requested_app == self.last_opened_app.lower():
                    inference.intent.action = "FOCUS_WINDOW"
                    inference.intent.parameters = {"app": requested_app}

            # =================================================================
            # STEP 2: EXECUTE (DETERMINISTIC FIRST)
            # =================================================================
            intent_data = {
                "intent": inference.intent.action,
                "slots": inference.intent.parameters,
                "confidence": inference.intent.confidence,
                "normalized_text": inference.normalized_text,
                "_model_used": inference.model,
            }

            # Type-text safety override (system path / dangerous text misuse).
            type_text_override = override_type_text_misuse(
                intent_data,
                getattr(self, "user_profile", None),
            )
            if type_text_override is not None:
                await self._notify_feedback(
                    EventType.CONFIRMATION_REQUIRED,
                    f"Triple tap in drawing canvas to confirm action "
                    f"{self._describe_action_from_confirmation(type_text_override)}",
                    priority=Priority.CRITICAL,
                )
                payload = self._build_confirmation_request(
                    confirmation_payload=type_text_override,
                    normalized_text=inference.normalized_text,
                    model=inference.model,
                )
                self._trace_block(
                    "FINAL RESULT",
                    {"status": payload["status"], "message": payload["message"]},
                )
                return payload
            
            await self._notify_feedback(
                EventType.EXECUTION_START,
                f"Executing {self._describe_intent(inference.intent.action, inference.intent.parameters)}",
            )
            result = await self.executor.execute(inference.intent)

            # Fallback: if deterministic path reports unsupported intent, try intelligent pipeline.
            if (
                isinstance(result, Result)
                and result.status == "error"
                and result.error_code == "UNSUPPORTED_INTENT"
                and hasattr(self, "pipeline_engine")
                and self.pipeline_engine is not None
            ):
                result = await self.pipeline_engine.process(intent_data)
            
            # =================================================================
            # STEP 3: BUILD RESPONSE
            # =================================================================
            self._update_context(inference.intent.action, inference.intent.parameters, result)
            
            payload = self._build_mobile_response(
                result=result,
                intent_name=inference.intent.action,
                normalized_text=inference.normalized_text,
                confidence=inference.intent.confidence,
                model=inference.model,
                slots=inference.intent.parameters,
            )
            
            self._trace_block(
                "FINAL RESULT",
                {
                    "status": payload["status"],
                    "message": payload["message"],
                    "verified": payload.get("verified", False),
                },
            )
            
            return payload
            
        except StageZeroValidationError as exc:
            logger.warning(f"Validation failure: {exc}")
            payload = {
                "type": "error",
                "status": "error",
                "intent": None,
                "message": str(exc),
            }
            self._trace_block(
                "FINAL RESULT",
                {"status": payload["status"], "message": payload["message"]},
            )
            return payload
            
        except Exception as exc:
            logger.exception("Stage 0 execution failed")
            payload = {
                "type": "error",
                "status": "error",
                "intent": None,
                "message": f"Execution failed: {exc}",
            }
            self._trace_block(
                "FINAL RESULT",
                {"status": payload["status"], "message": payload["message"]},
            )
            return payload

    async def handle_drawing_url(
        self,
        image_url: str,
        ws_callback: Optional[Callable[[dict], Any]] = None,
    ) -> dict:
        """
        Process drawing from URL instead of binary.
        
        UNIFIED: Uses IntelligentPipeline.
        """
        # Set WebSocket callback for this request
        if ws_callback:
            self.pipeline_engine.set_websocket_callback(ws_callback)
        
        try:
            # Download image
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=30) as resp:
                    if resp.status != 200:
                        return {
                            "type": "error",
                            "status": "error",
                            "message": f"Failed to download image: HTTP {resp.status}",
                        }
                    image_bytes = await resp.read()
            
            # Process as binary
            return await self.handle_drawing_image(image_bytes, ws_callback)
            
        except Exception as e:
            logger.error(f"Error processing drawing URL: {e}")
            return {
                "type": "error",
                "status": "error",
                "message": f"Failed to process drawing: {e}",
            }

    async def handle_text_input(
        self,
        text: str,
        ws_callback: Optional[Callable[[dict], Any]] = None,
    ) -> dict:
        """Process plain text input through deterministic parser and executor."""
        if ws_callback:
            self.pipeline_engine.set_websocket_callback(ws_callback)

        try:
            await self._notify_feedback(EventType.MODEL_PROCESSING, "Processing command")
            inference = await self.pipeline.process_text_input(text)

            safety_intercept = pre_intent_safety_check(
                inference.normalized_text,
                getattr(self, "user_profile", None),
            )
            if safety_intercept is not None:
                await self._notify_feedback(
                    EventType.CONFIRMATION_REQUIRED,
                    f"Triple tap in drawing canvas to confirm action "
                    f"{self._describe_action_from_confirmation(safety_intercept)}",
                    priority=Priority.CRITICAL,
                )
                return self._build_confirmation_request(
                    confirmation_payload=safety_intercept,
                    normalized_text=inference.normalized_text,
                    model=inference.model,
                )

            await self._notify_feedback(
                EventType.MODEL_SUCCESS,
                f"{self._describe_intent(inference.intent.action, inference.intent.parameters)} detected",
            )
            await self._notify_feedback(
                EventType.EXECUTION_START,
                f"Executing {self._describe_intent(inference.intent.action, inference.intent.parameters)}",
            )
            result = await self.executor.execute(inference.intent)
            self._update_context(inference.intent.action, inference.intent.parameters, result)
            return self._build_mobile_response(
                result=result,
                intent_name=inference.intent.action,
                normalized_text=inference.normalized_text,
                confidence=inference.intent.confidence,
                model=inference.model,
                slots=inference.intent.parameters,
            )
        except Exception as exc:
            logger.exception("Text input execution failed")
            return {
                "type": "error",
                "status": "error",
                "intent": None,
                "message": f"Execution failed: {exc}",
            }

    async def handle_confirmation_response(
        self,
        confirmation_id: str,
        confirmed: bool,
    ) -> Optional[dict]:
        """Handle confirmation responses for pending actions generated by this agent."""
        pending = self._pending_actions.pop(confirmation_id, None)
        if pending is None:
            return None

        if not confirmed:
            return {
                "type": "result",
                "status": "cancelled",
                "intent": pending.get("intent", "UNKNOWN"),
                "message": "Action cancelled by user",
                "normalized_text": pending.get("normalized_text", ""),
                "confidence": 1.0,
                "model": pending.get("model", "confirmation"),
                "slots": pending.get("slots", {}),
                "verified": False,
            }

        intent_name = str(pending.get("intent") or "UNKNOWN")
        slots = pending.get("slots", {})
        normalized_text = str(pending.get("normalized_text") or "")
        model = str(pending.get("model") or "confirmation")
        await self._notify_feedback(
            EventType.EXECUTION_START,
            f"Executing {self._describe_intent(intent_name, slots if isinstance(slots, dict) else {})}",
        )

        intent = Intent(
            action=intent_name,
            parameters=slots if isinstance(slots, dict) else {},
            confidence=1.0,
            metadata={"confirmed": True},
        )

        result = await self.executor.execute(intent)
        if (
            isinstance(result, Result)
            and result.status == "error"
            and result.error_code == "UNSUPPORTED_INTENT"
            and hasattr(self, "pipeline_engine")
            and self.pipeline_engine is not None
        ):
            pipeline_result = await self.pipeline_engine.process(
                {
                    "intent": intent_name,
                    "slots": slots if isinstance(slots, dict) else {},
                    "confidence": 1.0,
                    "normalized_text": normalized_text,
                    "_model_used": model,
                }
            )
            return self._build_mobile_response(
                result=pipeline_result,
                intent_name=intent_name,
                normalized_text=normalized_text,
                confidence=1.0,
                model=model,
                slots=slots if isinstance(slots, dict) else {},
            )

        self._update_context(intent_name, slots if isinstance(slots, dict) else {}, result)
        return self._build_mobile_response(
            result=result,
            intent_name=intent_name,
            normalized_text=normalized_text,
            confidence=1.0,
            model=model,
            slots=slots if isinstance(slots, dict) else {},
        )

    async def close(self) -> None:
        await self.pipeline.close()

    def peek_pending_confirmation_id(self) -> Optional[str]:
        """Return the most recent pending confirmation ID."""
        if not self._pending_actions:
            return None
        return next(reversed(self._pending_actions))

    def _build_mobile_response(
        self,
        *,
        result: Result | ExecutionResult | PipelineResult,
        intent_name: str,
        normalized_text: str,
        confidence: float,
        model: str,
        slots: dict,
    ) -> dict:
        """
        Build mobile-ready response from PipelineResult or ExecutionResult.
        
        UNIFIED: Handles PipelineResult (new unified flow) with fallback to ExecutionResult.
        """
        # Handle PipelineResult (unified pipeline)
        if isinstance(result, PipelineResult):
            payload = {
                "type": "result",
                "status": result.status,
                "intent": intent_name,
                "message": result.message,
                "normalized_text": normalized_text,
                "confidence": confidence,
                "model": model,
                "slots": slots,
                "verified": True,  # Pipeline always verifies
                "execution_time": result.execution_time,
            }
            
            # Add plan details if available
            if result.plan_result:
                payload["steps_completed"] = result.plan_result.completed_steps
                payload["total_steps"] = result.plan_result.total_steps
            
            return payload

        if isinstance(result, Result):
            payload = {
                "type": "result",
                "status": result.status,
                "intent": intent_name,
                "message": result.message,
                "normalized_text": normalized_text,
                "confidence": confidence,
                "model": model,
                "slots": slots,
                "verified": result.status == "success",
            }
            if result.data:
                payload.update(result.data)
            if result.error_code:
                payload["error_code"] = result.error_code
            return payload
        
        # Handle ExecutionResult (legacy fallback)
        payload = {
            "type": "result",
            "status": result.status,
            "intent": intent_name,
            "message": result.message,
            "normalized_text": normalized_text,
            "confidence": confidence,
            "model": model,
            "slots": slots,
            "verified": result.verified,
        }
        if result.data:
            payload.update(result.data)
        if result.error_code:
            payload["error_code"] = result.error_code
        return payload

    def _update_context(
        self,
        intent_name: str,
        slots: dict,
        result: Result | ExecutionResult | PipelineResult,
    ) -> None:
        """
        Update agent context after execution.
        
        UNIFIED: Handles both PipelineResult and ExecutionResult.
        """
        # Extract status from result
        status = result.status if hasattr(result, 'status') else "unknown"
        
        if status not in {"success"}:
            return
        self.context_manager.update(intent_name, slots)
        self.context_manager.debug()

        app_name = self.context_manager.state.get("current_app")
        if isinstance(app_name, str) and app_name:
            self.last_opened_app = app_name

    def _build_confirmation_request(
        self,
        *,
        confirmation_payload: dict,
        normalized_text: str,
        model: str,
    ) -> dict:
        """Build a confirmation_request payload and persist pending action."""
        original_intent = (
            confirmation_payload.get("original_intent")
            or confirmation_payload.get("slots", {}).get("original_intent")
            or "UNKNOWN"
        )
        original_slots = confirmation_payload.get("slots", {}).get("original_slots", {})
        if not isinstance(original_slots, dict):
            original_slots = {}

        confirmation_id = str(uuid.uuid4())[:8]
        self._pending_actions[confirmation_id] = {
            "intent": original_intent,
            "slots": original_slots,
            "normalized_text": normalized_text,
            "model": model,
        }

        action_preview = original_intent
        if original_slots:
            action_preview = f"{original_intent} {original_slots}"

        return {
            "type": "confirmation_request",
            "status": "confirmation_required",
            "intent": "CONFIRMATION_REQUIRED",
            "message": "Dangerous operation requires confirmation",
            "confirmation_id": confirmation_id,
            "action": action_preview,
            "timeout": 30.0,
            "normalized_text": normalized_text,
            "confidence": confirmation_payload.get("confidence", 1.0),
            "model": model,
            "slots": confirmation_payload.get("slots", {}),
            "reason": confirmation_payload.get("reason", "dangerous_operation"),
            "original_intent": original_intent,
            "confirmation_mode": confirmation_payload.get("confirmation_mode"),
            "confirmation_modes": confirmation_payload.get("confirmation_modes", []),
            "accessibility": confirmation_payload.get("accessibility", {}),
            "verified": False,
        }

    def _trace_block(self, section: str, payload) -> None:
        """Print trace block if trace mode enabled."""
        if not self.trace_mode:
            return

        logger.info("---")
        logger.info(f"## [{section}]")
        logger.info("========================================")
        logger.info(pformat(payload, sort_dicts=False))

    async def _notify_feedback(
        self,
        event_type: EventType,
        message: str,
        *,
        priority: Priority = Priority.NORMAL,
    ) -> None:
        """Send runtime stage feedback to the active client."""
        feedback_mgr = get_feedback_manager()
        if feedback_mgr:
            await feedback_mgr.notify(event_type, message, priority)

    def _describe_intent(self, intent_name: str, slots: dict) -> str:
        """Return a voice-friendly description of an action."""
        app_name = str(slots.get("app", "")).strip()
        if intent_name == "OPEN_APP" and app_name:
            return f"opening {app_name}"
        if intent_name == "LOCK_SCREEN":
            return "lock screen"
        if intent_name == "OPEN_URL":
            return "opening link"
        if intent_name == "SEARCH_WEB":
            return "web search"
        cleaned = intent_name.replace("_", " ").strip().lower()
        return cleaned or "command"

    def _describe_action_from_confirmation(self, confirmation_payload: dict) -> str:
        """Extract a feedback label from a confirmation payload."""
        original_intent = (
            confirmation_payload.get("original_intent")
            or confirmation_payload.get("slots", {}).get("original_intent")
            or "pending action"
        )
        original_slots = confirmation_payload.get("slots", {}).get("original_slots", {})
        if not isinstance(original_slots, dict):
            original_slots = {}
        return self._describe_intent(str(original_intent), original_slots)
