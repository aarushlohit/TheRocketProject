"""Image upload + AI inference pipeline for handwritten draw-to-action input."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import httpx

from agent.core.intent import Intent
from agent.stage0.validation import (
    StageZeroValidationError,
    extract_json_object,
    validate_ai_payload,
)
from agent.utils.logger import get_logger


logger = get_logger(__name__)


SYSTEM_PROMPT = (
    "You are an assistive AI system. Infer intent from messy handwritten input, "
    "correct spelling, and return strict JSON only. Allowed intents: "
    "OPEN_APP,CLOSE_APP,MINIMIZE,MAXIMIZE,SCREENSHOT,OPEN_URL. Use slots.app "
    "for OPEN_APP, slots.app or slots.target for CLOSE_APP, slots.target='focused' "
    "for MINIMIZE or MAXIMIZE when unspecified, absolute slots.url for OPEN_URL, "
    "and empty slots for SCREENSHOT. Return "
    "{\"intent\":\"...\",\"slots\":{},\"confidence\":0.0,\"normalized_text\":\"...\"}."
)


@dataclass
class InferenceResult:
    """Validated inference output from the AI pipeline."""

    intent: Intent
    normalized_text: str
    model: str
    image_path: Path
    image_url: str


class DrawToActionPipeline:
    """Turns a binary drawing into a validated intent."""

    def __init__(
        self,
        api_key: str,
        storage_dir: Path,
        confidence_threshold: float = 0.6,
    ):
        self.api_key = api_key
        self.storage_dir = storage_dir
        self.confidence_threshold = confidence_threshold
        self.received_dir = self.storage_dir / "received"
        self.received_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0))

    async def process_drawing(self, image_bytes: bytes) -> InferenceResult:
        """Save, upload, infer, and validate a drawn command."""
        image_path = self._save_image(image_bytes)
        image_url = await self._upload_image(image_path)

        primary_intent, normalized_text = await self._infer_with_model(
            model="gemini-fast",
            image_url=image_url,
        )
        if primary_intent.confidence >= self.confidence_threshold:
            return InferenceResult(
                intent=primary_intent,
                normalized_text=normalized_text,
                model="gemini-fast",
                image_path=image_path,
                image_url=image_url,
            )

        logger.warning(
            f"Primary model confidence {primary_intent.confidence:.2f} below threshold, trying fallback"
        )
        fallback_intent, fallback_text = await self._infer_with_model(
            model="qwen-vision",
            image_url=image_url,
        )

        if fallback_intent.confidence < self.confidence_threshold:
            raise StageZeroValidationError(
                "Could not confidently infer an intent from the drawing"
            )

        return InferenceResult(
            intent=fallback_intent,
            normalized_text=fallback_text,
            model="qwen-vision",
            image_path=image_path,
            image_url=image_url,
        )

    async def close(self) -> None:
        await self.client.aclose()

    def _save_image(self, image_bytes: bytes) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        output_path = self.received_dir / f"drawing_{timestamp}.png"
        output_path.write_bytes(image_bytes)
        logger.info(f"Saved drawing to {output_path}")
        return output_path

    async def _upload_image(self, image_path: Path) -> str:
        with image_path.open("rb") as image_file:
            response = await self.client.post(
                "https://media.pollinations.ai/upload",
                params={"key": self.api_key},
                files={"file": (image_path.name, image_file, "image/png")},
            )

        response.raise_for_status()
        payload = response.json()
        image_url = payload.get("url")

        if not image_url:
            raise StageZeroValidationError("Upload response did not include an image URL")

        logger.info(f"Uploaded drawing to {image_url}")
        return image_url

    async def _infer_with_model(self, model: str, image_url: str) -> tuple[Intent, str]:
        endpoint = f"https://gen.pollinations.ai/text/{quote(SYSTEM_PROMPT, safe='')}"
        response = await self.client.get(
            endpoint,
            params={
                "model": model,
                "image": image_url,
                "key": self.api_key,
            },
        )
        response.raise_for_status()

        raw_text = response.text.strip()
        logger.info(f"Model {model} responded with {len(raw_text)} characters")

        payload = extract_json_object(raw_text)
        intent, normalized_text = validate_ai_payload(payload)
        return intent, normalized_text
