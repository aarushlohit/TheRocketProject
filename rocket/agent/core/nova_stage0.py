"""High-level Stage 0 orchestration for draw-to-action."""

from __future__ import annotations

from agent.core.result import Result
from agent.platform.adapter import get_platform_adapter
from agent.stage0.executor import ActionExecutor
from agent.stage0.pipeline import DrawToActionPipeline
from agent.stage0.validation import StageZeroValidationError
from agent.utils.config import Config
from agent.utils.logger import get_logger


logger = get_logger(__name__)


class NovaStageZeroAgent:
    """Coordinates AI inference, validation, and OS execution."""

    def __init__(self, config: Config, api_key: str):
        self.config = config
        self.platform = get_platform_adapter(config.platform_type)
        self.pipeline = DrawToActionPipeline(
            api_key=api_key,
            storage_dir=config.data_dir / "drawings",
            confidence_threshold=config.confidence_threshold,
        )
        self.executor = ActionExecutor(
            platform=self.platform,
            artifacts_dir=config.data_dir / "artifacts",
        )
        logger.info("Nova Stage 0 agent initialized")

    async def handle_drawing_image(self, image_bytes: bytes) -> dict:
        """Run the full draw-to-action pipeline and return mobile-ready JSON."""
        try:
            inference = await self.pipeline.process_drawing(image_bytes)
            result = await self.executor.execute(inference.intent)
            return self._build_mobile_response(
                result=result,
                intent_name=inference.intent.action,
                normalized_text=inference.normalized_text,
                confidence=inference.intent.confidence,
                model=inference.model,
                slots=inference.intent.parameters,
            )
        except StageZeroValidationError as exc:
            logger.warning(f"Validation failure: {exc}")
            return {
                "status": "error",
                "intent": None,
                "message": str(exc),
            }
        except Exception as exc:
            logger.exception("Stage 0 execution failed")
            return {
                "status": "error",
                "intent": None,
                "message": f"Execution failed: {exc}",
            }

    async def close(self) -> None:
        await self.pipeline.close()

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
