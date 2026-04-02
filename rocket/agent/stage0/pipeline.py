"""Image processing + OCR-first inference pipeline for handwritten draw-to-action input."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from pprint import pformat

from PIL import Image
import requests

from agent.core.intent import Intent
from agent.stage2.ranker import RANKING_THRESHOLD, choose_best_candidate, rank_candidates
from agent.stage0.validation import (
    KNOWN_APPS,
    StageZeroValidationError,
    build_unknown_intent,
    correct_app,
)
from agent.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class InferenceCandidate:
    """A single OCR attempt for one image variant and model."""

    intent: Intent
    normalized_text: str
    model: str
    input_image_path: Path
    variant_name: str
    image_path: Path
    image_url: str
    raw_model_output: str
    message: str
    candidate_index: int = 0
    ranking_score: float = 0.0
    valid: bool = True


@dataclass
class InferenceResult:
    """Selected inference result after multi-variant OCR evaluation."""

    intent: Intent
    normalized_text: str
    model: str
    input_image_path: Path
    variant_name: str
    image_path: Path
    image_url: str
    raw_model_output: str
    message: str
    ranking_score: float
    candidates: list[InferenceCandidate]


def validate_api_key(api_key: str) -> bool:
    """Validate a Pollinations API key and raise on invalid keys."""
    response = requests.get(
        "https://gen.pollinations.ai/account/key",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    if response.status_code != 200:
        raise StageZeroValidationError(
            f"Invalid API key — status {response.status_code}. Fix before running."
        )
    return True


def extract_app_name(text: str) -> str | None:
    """Extract the word that follows 'open' from OCR text."""
    words = text.split()
    if "open" in words:
        idx = words.index("open")
        if idx + 1 < len(words):
            return words[idx + 1]
    return None


def parse_intent(text: str) -> dict:
    """Parse intent from OCR text without trusting the model for action selection."""
    if "open" in text:
        return {
            "intent": "OPEN_APP",
            "app": extract_app_name(text),
        }
    elif "close" in text:
        return {"intent": "CLOSE_APP"}
    elif "screenshot" in text:
        return {"intent": "SCREENSHOT"}
    return {"intent": "UNKNOWN"}


def call_model(image_url: str, api_key: str) -> str:
    """Call Pollinations Chat Completions for multimodal OCR."""
    url = "https://gen.pollinations.ai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": "gemini-fast",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "decode and extract text"},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    }

    print("\n========== [CHAT REQUEST BODY] ==========")
    print(body)

    response = requests.post(url, headers=headers, json=body, timeout=90)

    print("\n========== [MODEL STATUS] ==========")
    print(response.status_code)

    print("\n========== [MODEL RAW RESPONSE] ==========")
    print(response.text)

    if response.status_code != 200:
        raise Exception("Model request failed")

    data = response.json()
    text = data["choices"][0]["message"]["content"]
    return text.strip()


class DrawToActionPipeline:
    """Turns a binary drawing into a validated intent."""

    def __init__(
        self,
        api_key: str,
        storage_dir: Path,
        confidence_threshold: float = 0.6,
        trace_mode: bool = True,
    ):
        self.api_key = api_key
        self.storage_dir = storage_dir
        self.confidence_threshold = confidence_threshold
        self.trace_mode = trace_mode
        self.received_dir = self.storage_dir / "received"
        self.variants_dir = self.storage_dir / "variants"
        self.received_dir.mkdir(parents=True, exist_ok=True)
        self.variants_dir.mkdir(parents=True, exist_ok=True)

    async def process_drawing(
        self,
        image_bytes: bytes,
        *,
        preferred_app: str | None = None,
    ) -> InferenceResult:
        """Save, preprocess, run OCR, and select the safest parsed intent."""
        input_image_path = self._save_image(image_bytes)
        candidates: list[InferenceCandidate] = []

        for variant_name, variant_path in self._create_variants(input_image_path):
            image_url = await asyncio.to_thread(self._upload_image, variant_path)
            candidate = await self._infer_attempt(
                input_image_path=input_image_path,
                variant_name=variant_name,
                variant_path=variant_path,
                image_url=image_url,
                model="gemini-fast",
            )
            candidates.append(candidate)

        self._trace_block(
            "ALL CANDIDATES",
            [
                {
                    "variant": candidate.variant_name,
                    "model": candidate.model,
                    "text": candidate.normalized_text,
                    "confidence": candidate.intent.confidence,
                    "intent": candidate.intent.action,
                    "app": candidate.intent.parameters.get("app"),
                    "valid": candidate.valid,
                }
                for candidate in candidates
            ],
        )

        ranked_candidates = rank_candidates(candidates, preferred_app=preferred_app)
        self._trace_block(
            "RANKING SCORES",
            [
                {
                    "variant": ranked.candidate.variant_name,
                    "model": ranked.candidate.model,
                    "text": ranked.candidate.normalized_text,
                    "intent": ranked.candidate.intent.action,
                    "score": round(ranked.score, 4),
                }
                for ranked in ranked_candidates
            ],
        )

        ranked_choice = choose_best_candidate(
            candidates,
            preferred_app=preferred_app,
            threshold=max(self.confidence_threshold, RANKING_THRESHOLD),
        )
        selected = ranked_choice.candidate if ranked_choice is not None else None
        if selected is None:
            unknown_intent = build_unknown_intent(
                message="Could not determine intent",
                confidence=0.4,
                normalized_text="",
            )
            self._trace_block(
                "FINAL SELECTION",
                {
                    "variant": "none",
                    "model": "none",
                    "text": "",
                    "intent": unknown_intent.action,
                    "score": 0.0,
                },
            )
            return InferenceResult(
                intent=unknown_intent,
                normalized_text="",
                model="none",
                input_image_path=input_image_path,
                variant_name="none",
                image_path=input_image_path,
                image_url="",
                raw_model_output="No valid OCR output",
                message="Could not determine intent",
                ranking_score=0.0,
                candidates=candidates,
            )

        selected.ranking_score = ranked_choice.score
        self._trace_block(
            "FINAL SELECTION",
            {
                "variant": selected.variant_name,
                "model": selected.model,
                "text": selected.normalized_text,
                "intent": selected.intent.action,
                "app": selected.intent.parameters.get("app"),
                "score": selected.ranking_score,
            },
        )
        return InferenceResult(
            intent=selected.intent,
            normalized_text=selected.normalized_text,
            model=selected.model,
            input_image_path=selected.input_image_path,
            variant_name=selected.variant_name,
            image_path=selected.image_path,
            image_url=selected.image_url,
            raw_model_output=selected.raw_model_output,
            message=selected.message,
            ranking_score=selected.ranking_score,
            candidates=candidates,
        )

    async def close(self) -> None:
        return None

    def _save_image(self, image_bytes: bytes) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        output_path = self.received_dir / f"drawing_{timestamp}.png"
        output_path.write_bytes(image_bytes)
        self._trace_block("INPUT IMAGE", str(output_path))
        return output_path

    def _create_variants(self, image_path: Path) -> list[tuple[str, Path]]:
        with Image.open(image_path) as image:
            base_image = image.convert("RGB")
            original_path = self.variants_dir / f"{image_path.stem}_original.png"
            rotated_90_path = self.variants_dir / f"{image_path.stem}_rotated_90.png"
            rotated_270_path = self.variants_dir / f"{image_path.stem}_rotated_270.png"

            base_image.save(original_path)
            base_image.rotate(90, expand=True).save(rotated_90_path)
            base_image.rotate(270, expand=True).save(rotated_270_path)

        variants = [
            ("original", original_path),
            ("rotated_90", rotated_90_path),
            ("rotated_270", rotated_270_path),
        ]
        self._trace_block("VARIANTS", [name for name, _ in variants])
        return variants

    def _upload_image(self, image_path: Path) -> str:
        """Upload a variant to Pollinations media hosting."""
        with image_path.open("rb") as image_file:
            response = requests.post(
                "https://media.pollinations.ai/upload",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": (image_path.name, image_file, "image/png")},
                timeout=60,
            )

        if response.status_code != 200:
            raise StageZeroValidationError(f"Image upload failed: {response.status_code}")

        payload = response.json()
        image_url = payload.get("url")
        if not image_url:
            raise StageZeroValidationError("Image upload failed: no URL returned")

        self._trace_block("IMAGE URL", image_url)
        return image_url

    async def _infer_with_model(self, image_url: str) -> str:
        return await asyncio.to_thread(call_model, image_url, self.api_key)

    async def _infer_attempt(
        self,
        *,
        input_image_path: Path,
        variant_name: str,
        variant_path: Path,
        image_url: str,
        model: str,
    ) -> InferenceCandidate:
        try:
            ocr_text = await self._infer_with_model(image_url=image_url)
            print("[OCR TEXT]", ocr_text)

            raw_text = ocr_text.strip().lower()
            clean_text = raw_text.replace("\n", " ").strip()
            intent_result = parse_intent(clean_text)

            print("[OCR TEXT]")
            print(clean_text)
            print("[PARSED INTENT]")
            print(intent_result)

            self._trace_block("OCR TEXT", clean_text or "MISSING")
            self._trace_block("PARSED INTENT", intent_result)

            intent, message = self._build_intent(clean_text, intent_result)
            return InferenceCandidate(
                intent=intent,
                normalized_text=clean_text,
                model=model,
                input_image_path=input_image_path,
                variant_name=variant_name,
                image_path=variant_path,
                image_url=image_url,
                raw_model_output=ocr_text,
                message=message,
                valid=intent.action != "UNKNOWN",
            )
        except Exception as exc:
            self._trace_block("PARSED INTENT", {"intent": "UNKNOWN", "error": str(exc)})
            return InferenceCandidate(
                intent=build_unknown_intent(
                    message="Could not determine intent",
                    confidence=0.4,
                    normalized_text="",
                ),
                normalized_text="",
                model=model,
                input_image_path=input_image_path,
                variant_name=variant_name,
                image_path=variant_path,
                image_url=image_url,
                raw_model_output=str(exc),
                message="Could not determine intent",
                valid=False,
            )

    def _build_intent(self, clean_text: str, parsed_intent: dict) -> tuple[Intent, str]:
        action = parsed_intent.get("intent")

        if action == "OPEN_APP":
            raw_app = parsed_intent.get("app")
            corrected_app = correct_app(raw_app) if isinstance(raw_app, str) else None
            if not corrected_app or corrected_app not in KNOWN_APPS:
                return (
                    build_unknown_intent(
                        message="Could not determine intent",
                        confidence=0.4,
                        normalized_text=clean_text,
                    ),
                    "Could not determine intent",
                )

            return (
                Intent(
                    action="OPEN_APP",
                    parameters={"app": corrected_app},
                    confidence=0.9,
                    metadata={"normalized_text": clean_text},
                ),
                "Intent parsed from OCR text",
            )

        if action == "CLOSE_APP":
            return (
                Intent(
                    action="CLOSE_APP",
                    parameters={"target": "focused"},
                    confidence=0.85,
                    metadata={"normalized_text": clean_text},
                ),
                "Intent parsed from OCR text",
            )

        if action == "SCREENSHOT":
            return (
                Intent(
                    action="SCREENSHOT",
                    parameters={},
                    confidence=0.85,
                    metadata={"normalized_text": clean_text},
                ),
                "Intent parsed from OCR text",
            )

        return (
            build_unknown_intent(
                message="Could not determine intent",
                confidence=0.4,
                normalized_text=clean_text,
            ),
            "Could not determine intent",
        )

    def _trace_block(self, section: str, payload) -> None:
        if not self.trace_mode:
            return

        logger.info("---")
        logger.info(f"## [{section}]")
        logger.info("========================================")
        if isinstance(payload, str):
            logger.info(self._mask_sensitive(payload))
            return
        logger.info(self._mask_sensitive(pformat(payload, sort_dicts=False)))

    def _mask_sensitive(self, value: str) -> str:
        if not self.api_key:
            return value
        return value.replace(self.api_key, "****")


def select_best_result(results: list[InferenceCandidate]) -> InferenceCandidate | None:
    """Compatibility wrapper around the Stage 2 ranking engine."""
    ranked = choose_best_candidate(results)
    if ranked is None:
        return None
    ranked.candidate.ranking_score = ranked.score
    return ranked.candidate
