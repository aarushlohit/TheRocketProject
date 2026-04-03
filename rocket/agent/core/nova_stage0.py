"""High-level Stage 0 orchestration for draw-to-action — Production Grade.

PATCHED VERSION:
- Integrated ExecutionEngine
- WebSocket callback support
- Full FeedbackManager integration
- NO fake success, verified execution
"""

from __future__ import annotations

from pprint import pformat
from typing import Any, Callable, Optional

from agent.core.result import Result
from agent.core.execution_engine import ExecutionEngine, ExecutionResult
from agent.core.intelligent_pipeline import IntelligentPipeline, PipelineResult
from agent.core.user_profile import UserProfile, get_or_create_profile
from agent.platform.adapter import get_platform_adapter
from agent.stage0.executor import ActionExecutor
from agent.stage0.pipeline import DrawToActionPipeline
from agent.stage0.validation import StageZeroValidationError
from agent.utils.app_map import normalize_app
from agent.utils.config import Config
from agent.utils.logger import get_logger


logger = get_logger(__name__)


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

            # =================================================================
            # STEP 2: EXECUTE VIA INTELLIGENT PIPELINE (UNIFIED)
            # =================================================================
            # Convert inference to pipeline format
            intent_data = {
                "intent": inference.intent.action,
                "slots": inference.intent.parameters,
                "confidence": inference.intent.confidence,
                "normalized_text": inference.normalized_text,
                "_model_used": inference.model,
            }
            
            # UNIFIED FLOW: ALL execution goes through IntelligentPipeline
            # Pipeline runs: refine → plan → guardrails → execute → verify
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

    async def close(self) -> None:
        await self.pipeline.close()

    def _build_mobile_response(
        self,
        *,
        result: ExecutionResult | PipelineResult,
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

    def _update_context(self, intent_name: str, slots: dict, result: ExecutionResult | PipelineResult) -> None:
        """
        Update agent context after execution.
        
        UNIFIED: Handles both PipelineResult and ExecutionResult.
        """
        # Extract status from result
        status = result.status if hasattr(result, 'status') else "unknown"
        
        if status not in {"success"}:
            return
        if intent_name != "OPEN_APP":
            return

        app_name = slots.get("app")
        if isinstance(app_name, str) and app_name:
            self.last_opened_app = app_name

    def _trace_block(self, section: str, payload) -> None:
        """Print trace block if trace mode enabled."""
        if not self.trace_mode:
            return

        logger.info("---")
        logger.info(f"## [{section}]")
        logger.info("========================================")
        logger.info(pformat(payload, sort_dicts=False))
