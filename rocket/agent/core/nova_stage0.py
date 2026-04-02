"""High-level Stage 0 orchestration for draw-to-action."""

from __future__ import annotations

from pprint import pformat

from agent.core.result import Result
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
        self.executor = ActionExecutor(
            platform=self.platform,
            artifacts_dir=config.data_dir / "artifacts",
            debug_mode=config.debug_mode,
            platform_type=config.platform_type,
        )
        logger.info("Nova Stage 0 agent initialized")

    async def handle_drawing_image(self, image_bytes: bytes) -> dict:
        """Run the full draw-to-action pipeline and return mobile-ready JSON."""
        try:
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

            if inference.intent.action == "UNKNOWN":
                payload = {
                    "status": "blocked",
                    "reason": "uncertain intent",
                    "intent": "UNKNOWN",
                    "message": inference.message,
                    "normalized_text": inference.normalized_text,
                    "confidence": inference.intent.confidence,
                    "model": inference.model,
                    "slots": inference.intent.parameters,
                }
                self._trace_block(
                    "FINAL RESULT",
                    {"status": payload["status"], "message": payload["message"]},
                )
                return payload

            result = await self.executor.execute(inference.intent)
            self._log_execution_result(result)
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
                {"status": payload["status"], "message": payload["message"]},
            )
            return payload
        except StageZeroValidationError as exc:
            logger.warning(f"Validation failure: {exc}")
            payload = {
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
                "status": "error",
                "intent": None,
                "message": f"Execution failed: {exc}",
            }
            self._trace_block(
                "FINAL RESULT",
                {"status": payload["status"], "message": payload["message"]},
            )
            return payload

    async def close(self) -> None:
        await self.pipeline.close()

    def _log_execution_result(self, result: Result) -> None:
        logger.info("[EXECUTION RESULT]")
        if result.status == "success":
            if hasattr(logger, "success"):
                logger.success(result.message)
            else:
                logger.info(result.message)
            return

        if result.status == "debug":
            logger.info("DRY RUN")
            logger.info(result.message)
            return

        logger.error(result.message)

    def _build_mobile_response(
        self,
        *,
        result: Result,
        intent_name: str,
        normalized_text: str,
        confidence: float,
        model: str,
        slots: dict,
    ) -> dict:
        payload = {
            "status": result.status,
            "intent": intent_name,
            "message": result.message,
            "normalized_text": normalized_text,
            "confidence": confidence,
            "model": model,
            "slots": slots,
        }
        if result.data:
            payload.update(result.data)
        return payload

    def _update_context(self, intent_name: str, slots: dict, result: Result) -> None:
        if result.status not in {"success", "debug"}:
            return
        if intent_name != "OPEN_APP":
            return

        app_name = slots.get("app")
        if isinstance(app_name, str) and app_name:
            self.last_opened_app = app_name

    def _trace_block(self, section: str, payload) -> None:
        if not self.trace_mode:
            return

        logger.info("---")
        logger.info(f"## [{section}]")
        logger.info("========================================")
        logger.info(pformat(payload, sort_dicts=False))
