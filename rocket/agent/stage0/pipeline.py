"""Execution-first intent pipeline for drawing and text inputs.

Deterministic runtime behavior:
- strict JSON parsing with enum validation
- single-pass inference
- raw-text fallback parsing
- minimal filtering prior to execution
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from pprint import pformat

from PIL import Image
import requests

from agent.core.context_manager import PRONOUN_TOKENS, get_context_manager
from agent.core.intent import Intent
from agent.stage0.validation import (
    StageZeroValidationError,
    build_unknown_intent,
    correct_app,
)
from agent.utils.logger import get_logger


logger = get_logger(__name__)

APP_CONTEXT_INTENTS = {"CLOSE_APP", "MINIMIZE_APP", "MAXIMIZE_APP", "RESTORE_APP", "FOCUS_WINDOW", "SAVE_FILE"}
SAVE_FILE_PATTERN = re.compile(r"^save(?:\s+file)?(?:\s+(?:as\s+)?)?(?P<filename>[^\s]+)?$")


# =============================================================================
# STAGE 4 — JSON-FIRST SYSTEM PROMPT (ENHANCED)
# =============================================================================
SYSTEM_PROMPT = """You are an execution-first intent parser for an autonomous AI OS.

HARD RULES:
1. OUTPUT MUST BE STRICT JSON ONLY.
2. NO markdown, NO explanation, NO extra text.
3. USE ONLY enum intents listed below.
4. INVALID OR UNCLEAR MUST RETURN UNKNOWN.
5. NEVER downgrade a valid clear intent.
6. If multiple actions are present, return MULTI_STEP with sequential steps.

SUPPORTED ENUM INTENTS:
OPEN_APP, CLOSE_APP, MINIMIZE_APP, MAXIMIZE_APP, RESTORE_APP, SWITCH_APP, FOCUS_WINDOW,
OPEN_URL, SEARCH_WEB, NEW_TAB, CLOSE_TAB, SWITCH_TAB, REFRESH_PAGE, SCROLL_UP, SCROLL_DOWN,
SAVE_FILE, TYPE_TEXT, CLEAR_TEXT, SELECT_TEXT, COPY, PASTE, CUT, PRESS_KEYS,
LOCK_SCREEN, MINIMIZE_ALL, MAXIMIZE_ALL, VOLUME_UP, VOLUME_DOWN, MUTE, UNMUTE, BRIGHTNESS_UP, BRIGHTNESS_DOWN,
OPEN_FILE, DELETE_FILE, CREATE_FILE, MOVE_FILE, RENAME_FILE,
CLICK_ELEMENT, SCROLL, WAIT,
MULTI_STEP, CONDITIONAL,
CONFIRMATION_REQUIRED, UNKNOWN.

OUTPUT FORMAT (SINGLE):
{
    "intent": "ENUM",
    "slots": {},
    "confidence": 0.0,
    "normalized_text": "text"
}

OUTPUT FORMAT (MULTI):
{
    "intent": "MULTI_STEP",
    "steps": [
        {"intent": "ENUM", "slots": {}}
    ],
    "confidence": 0.0,
    "normalized_text": "text"
}
"""


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
    """
    Selected inference result after multi-variant OCR evaluation.
    
    STAGE 4 ENHANCED: Includes consistency and trust metadata.
    """

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
    
    # Stage 4 metadata (optional for backward compatibility)
    consistency_score: float = 0.0
    trust_score: float = 0.0
    should_execute: bool = True
    validation_passed: bool = True


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


SUPPORTED_ENUM_INTENTS = {
    "OPEN_APP", "CLOSE_APP", "MINIMIZE_APP", "MAXIMIZE_APP", "RESTORE_APP", "SWITCH_APP", "FOCUS_WINDOW",
    "OPEN_URL", "SEARCH_WEB", "NEW_TAB", "CLOSE_TAB", "SWITCH_TAB", "REFRESH_PAGE", "SCROLL_UP", "SCROLL_DOWN",
    "SAVE_FILE", "TYPE_TEXT", "CLEAR_TEXT", "SELECT_TEXT", "COPY", "PASTE", "CUT", "PRESS_KEYS",
    "LOCK_SCREEN", "MINIMIZE_ALL", "MAXIMIZE_ALL", "VOLUME_UP", "VOLUME_DOWN", "MUTE", "UNMUTE", "BRIGHTNESS_UP", "BRIGHTNESS_DOWN",
    "OPEN_FILE", "DELETE_FILE", "CREATE_FILE", "MOVE_FILE", "RENAME_FILE",
    "CLICK_ELEMENT", "SCROLL", "WAIT", "MULTI_STEP", "CONDITIONAL", "CONFIRMATION_REQUIRED", "UNKNOWN",
    "SCREENSHOT", "MINIMIZE", "MAXIMIZE",
}


def extract_percentage(text: str) -> dict:
    lowered = text.lower()
    match = re.search(r"(\d+)", lowered)
    if match:
        return {"value": int(match.group(1))}

    if "slight" in lowered or "slightly" in lowered or "a bit" in lowered or "little" in lowered:
        return {"value": 5}

    if "more" in lowered or "increase" in lowered:
        return {"value": 10}

    if "high" in lowered or "loud" in lowered:
        return {"value": 15}

    if "max" in lowered or "full" in lowered:
        return {"value": 100}

    if "low" in lowered or "reduce" in lowered:
        return {"value": 5}

    return {"value": 5}


def resolve_intent(text: str) -> tuple[str, dict]:
    normalized = text.strip().lower()

    print(f"[INPUT TEXT] {normalized}")

    # ALWAYS FIRST
    if "volume" in normalized:
        value = extract_percentage(normalized)["value"]

        if "up" in normalized or "increase" in normalized:
            print("[RESOLVED INTENT] VOLUME_UP")
            return "VOLUME_UP", {"value": value}

        if "down" in normalized or "reduce" in normalized or "decrease" in normalized:
            print("[RESOLVED INTENT] VOLUME_DOWN")
            return "VOLUME_DOWN", {"value": value}

    if "mute" in normalized and "unmute" not in normalized:
        print("[RESOLVED INTENT] MUTE")
        return "MUTE", {}

    if "unmute" in normalized:
        print("[RESOLVED INTENT] UNMUTE")
        return "UNMUTE", {}

    if "minimize all" in normalized or "show desktop" in normalized:
        print("[RESOLVED INTENT] MINIMIZE_ALL")
        return "MINIMIZE_ALL", {}

    if "maximize all" in normalized or "maximize everything" in normalized:
        print("[RESOLVED INTENT] MAXIMIZE_ALL")
        return "MAXIMIZE_ALL", {}

    save_match = SAVE_FILE_PATTERN.match(normalized)
    if save_match:
        filename = save_match.group("filename")
        if filename and filename in PRONOUN_TOKENS:
            filename = None
        slots = {"filename": filename} if filename else {}
        print("[RESOLVED INTENT] SAVE_FILE")
        return "SAVE_FILE", slots

    parsed = parse_intent(normalized)
    intent = parsed.get("intent", "UNKNOWN")
    slots = parsed.get("slots", {}) if isinstance(parsed.get("slots"), dict) else {}
    slots = _strip_pronoun_slots(intent, slots)

    if intent == "MULTI_STEP":
        print("[BLOCKED] MULTI_STEP disabled")
        print("[RESOLVED INTENT] UNKNOWN")
        return "UNKNOWN", {}

    if intent == "PRESS_KEYS" and "volume" in normalized:
        print("[BLOCKED] Model tried PRESS_KEYS for volume")
        print("[RESOLVED INTENT] UNKNOWN")
        return "UNKNOWN", {}

    print(f"[RESOLVED INTENT] {intent}")
    return intent, slots


def _strip_pronoun_slots(intent: str, slots: dict) -> dict:
    if intent not in APP_CONTEXT_INTENTS or not isinstance(slots, dict):
        return slots

    normalized_slots = dict(slots)

    app = normalized_slots.get("app")
    if isinstance(app, str) and app.strip().lower() in PRONOUN_TOKENS:
        normalized_slots.pop("app", None)

    window = normalized_slots.get("window")
    if isinstance(window, str) and window.strip().lower() in PRONOUN_TOKENS:
        normalized_slots.pop("window", None)

    return normalized_slots


def _parse_single_intent(text: str) -> dict:
    """Deterministic text-to-intent fallback parser."""
    cleaned = text.strip().lower()
    if not cleaned:
        return {"intent": "UNKNOWN", "slots": {}, "confidence": 0.0}

    if cleaned.startswith(("open ", "launch ", "start ")):
        target = cleaned.split(" ", 1)[1].strip() if " " in cleaned else ""
        if target.startswith(("http://", "https://", "www.")) or "." in target:
            url = target if target.startswith(("http://", "https://")) else f"https://{target}"
            return {"intent": "OPEN_URL", "slots": {"url": url}, "confidence": 0.85}
        return {"intent": "OPEN_APP", "slots": {"app": target}, "confidence": 0.85}

    if cleaned.startswith("close tab"):
        return {"intent": "CLOSE_TAB", "slots": {}, "confidence": 0.85}
    if cleaned.startswith("new tab"):
        return {"intent": "NEW_TAB", "slots": {}, "confidence": 0.85}
    if cleaned.startswith("switch tab"):
        parts = cleaned.split()
        tab_index = None
        if parts and parts[-1].isdigit():
            tab_index = int(parts[-1])
        slots = {"tab_index": tab_index} if tab_index is not None else {}
        return {"intent": "SWITCH_TAB", "slots": slots, "confidence": 0.8}
    if cleaned.startswith("refresh"):
        return {"intent": "REFRESH_PAGE", "slots": {}, "confidence": 0.8}

    if cleaned.startswith("search "):
        query = cleaned.split(" ", 1)[1].strip()
        return {"intent": "SEARCH_WEB", "slots": {"query": query}, "confidence": 0.85}

    save_match = SAVE_FILE_PATTERN.match(cleaned)
    if save_match:
        filename = save_match.group("filename")
        if filename and filename in PRONOUN_TOKENS:
            filename = None
        slots = {"filename": filename} if filename else {}
        return {"intent": "SAVE_FILE", "slots": slots, "confidence": 0.9}

    if cleaned.startswith("type ") or cleaned.startswith("write ") or cleaned.startswith("input "):
        text_value = cleaned.split(" ", 1)[1].strip() if " " in cleaned else ""
        return {"intent": "TYPE_TEXT", "slots": {"text": text_value}, "confidence": 0.85}
    if cleaned.startswith("clear text"):
        return {"intent": "CLEAR_TEXT", "slots": {}, "confidence": 0.8}
    if cleaned.startswith("select text") or cleaned.startswith("select all"):
        return {"intent": "SELECT_TEXT", "slots": {}, "confidence": 0.8}
    if cleaned == "copy":
        return {"intent": "COPY", "slots": {}, "confidence": 0.8}
    if cleaned == "paste":
        return {"intent": "PASTE", "slots": {}, "confidence": 0.8}
    if cleaned == "cut":
        return {"intent": "CUT", "slots": {}, "confidence": 0.8}
    if cleaned.startswith("press "):
        keys = cleaned.split(" ", 1)[1].strip().replace(" ", "")
        return {"intent": "PRESS_KEYS", "slots": {"keys": keys}, "confidence": 0.8}

    if cleaned.startswith("close "):
        app = cleaned.split(" ", 1)[1].strip() if " " in cleaned else ""
        slots = {"app": app} if app else {}
        return {"intent": "CLOSE_APP", "slots": slots, "confidence": 0.8}
    if cleaned.startswith("minimize"):
        return {"intent": "MINIMIZE_APP", "slots": {}, "confidence": 0.8}
    if cleaned.startswith("maximize"):
        return {"intent": "MAXIMIZE_APP", "slots": {}, "confidence": 0.8}
    if cleaned.startswith("restore"):
        target = cleaned.split(" ", 1)[1].strip() if " " in cleaned else ""
        slots = {"app": target} if target and target != "window" else {}
        return {"intent": "RESTORE_APP", "slots": slots, "confidence": 0.8}
    if cleaned.startswith("switch app"):
        return {"intent": "SWITCH_APP", "slots": {}, "confidence": 0.8}
    if cleaned.startswith("focus "):
        target = cleaned.split(" ", 1)[1].strip()
        return {"intent": "FOCUS_WINDOW", "slots": {"window": target}, "confidence": 0.8}

    if "lock screen" in cleaned:
        return {"intent": "LOCK_SCREEN", "slots": {}, "confidence": 0.9}
    if "minimize all" in cleaned or "show desktop" in cleaned:
        return {"intent": "MINIMIZE_ALL", "slots": {}, "confidence": 0.9}
    if "maximize all" in cleaned or "maximize everything" in cleaned:
        return {"intent": "MAXIMIZE_ALL", "slots": {}, "confidence": 0.9}
    if "volume up" in cleaned:
        return {"intent": "VOLUME_UP", "slots": {}, "confidence": 0.8}
    if "volume down" in cleaned:
        return {"intent": "VOLUME_DOWN", "slots": {}, "confidence": 0.8}
    if "unmute" in cleaned:
        return {"intent": "UNMUTE", "slots": {}, "confidence": 0.8}
    if "mute" in cleaned and "unmute" not in cleaned:
        return {"intent": "MUTE", "slots": {}, "confidence": 0.8}
    if "brightness up" in cleaned:
        return {"intent": "BRIGHTNESS_UP", "slots": {}, "confidence": 0.75}
    if "brightness down" in cleaned:
        return {"intent": "BRIGHTNESS_DOWN", "slots": {}, "confidence": 0.75}

    if cleaned.startswith("open file "):
        return {"intent": "OPEN_FILE", "slots": {"path": cleaned.split("open file ", 1)[1].strip()}, "confidence": 0.8}
    if cleaned.startswith("delete file ") or cleaned.startswith("remove file "):
        path = cleaned.split("file ", 1)[1].strip()
        return {"intent": "DELETE_FILE", "slots": {"path": path}, "confidence": 0.85}
    if cleaned.startswith("create file "):
        return {"intent": "CREATE_FILE", "slots": {"path": cleaned.split("create file ", 1)[1].strip()}, "confidence": 0.8}
    if cleaned.startswith("move file ") and " to " in cleaned:
        source_dest = cleaned.split("move file ", 1)[1]
        source, destination = source_dest.split(" to ", 1)
        return {"intent": "MOVE_FILE", "slots": {"source": source.strip(), "destination": destination.strip()}, "confidence": 0.8}
    if cleaned.startswith("rename file ") and " to " in cleaned:
        source_dest = cleaned.split("rename file ", 1)[1]
        source, new_name = source_dest.split(" to ", 1)
        return {"intent": "RENAME_FILE", "slots": {"path": source.strip(), "new_name": new_name.strip()}, "confidence": 0.8}

    if cleaned.startswith("click "):
        target = cleaned.split("click ", 1)[1].strip()
        return {"intent": "CLICK_ELEMENT", "slots": {"target": target}, "confidence": 0.8}
    if cleaned.startswith("scroll up"):
        return {"intent": "SCROLL_UP", "slots": {}, "confidence": 0.8}
    if cleaned.startswith("scroll down"):
        return {"intent": "SCROLL_DOWN", "slots": {}, "confidence": 0.8}
    if cleaned.startswith("scroll "):
        direction = cleaned.split(" ", 1)[1].strip()
        return {"intent": "SCROLL", "slots": {"direction": direction}, "confidence": 0.75}
    if cleaned.startswith("wait"):
        return {"intent": "WAIT", "slots": {}, "confidence": 0.75}

    if cleaned.startswith("if ") and " then " in cleaned:
        return {"intent": "CONDITIONAL", "slots": {"raw": cleaned}, "confidence": 0.7}

    if "screenshot" in cleaned or "screen capture" in cleaned:
        return {"intent": "SCREENSHOT", "slots": {}, "confidence": 0.8}

    return {"intent": "UNKNOWN", "slots": {}, "confidence": 0.0}


def parse_intent(text: str) -> dict:
    """Parse intent from OCR/raw text with deterministic fallback rules."""
    normalized = text.strip().lower()
    if not normalized:
        return {"intent": "UNKNOWN", "slots": {}, "confidence": 0.0, "normalized_text": ""}

    for separator in [" and then ", " then ", " and "]:
        if separator in normalized:
            parts = [segment.strip() for segment in normalized.split(separator) if segment.strip()]
            steps = []
            for part in parts:
                step = _parse_single_intent(part)
                if step.get("intent") != "UNKNOWN":
                    steps.append({"intent": step.get("intent"), "slots": step.get("slots", {})})
            if len(steps) > 1:
                return {
                    "intent": "MULTI_STEP",
                    "slots": {"steps": steps},
                    "steps": steps,
                    "confidence": 0.85,
                    "normalized_text": normalized,
                }

    parsed = _parse_single_intent(normalized)
    parsed.setdefault("slots", {})
    parsed["normalized_text"] = normalized
    if parsed.get("intent") not in SUPPORTED_ENUM_INTENTS:
        return {"intent": "UNKNOWN", "slots": {}, "confidence": 0.0, "normalized_text": normalized}
    return parsed


def clean_json_response(text: str) -> str:
    """Clean JSON response by removing markdown code blocks."""
    text = text.strip()
    
    # Handle ```json ... ``` blocks
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    return text.strip()


# =============================================================================
# HARDENED MODEL CALLING (PRODUCTION-GRADE)
# =============================================================================
# Import hardened pipeline with circuit breaker, retry, rate limiting
from agent.core.hardened_pipeline import (
    call_model_hardened,
    validate_and_execute_check,
    validate_image_url,
    CONFIDENCE_THRESHOLD as HARDENED_CONFIDENCE_THRESHOLD,
)
from agent.core.circuit_breaker import get_circuit_breaker
from agent.core.rate_limiter import get_rate_limiter


def call_gemini(image_url: str, api_key: str) -> dict:
    """
    Call Gemini via Pollinations Chat Completions.
    
    NOTE: This is a legacy wrapper. Use call_model_hardened() for production.
    """
    from agent.core.hardened_pipeline import call_gemini_with_retry
    
    circuit_breaker = get_circuit_breaker()
    result, error = call_gemini_with_retry(image_url, api_key, circuit_breaker)
    
    if result is None:
        raise Exception(f"Gemini failed: {error}")
    
    return result


def call_qwen(image_url: str, api_key: str) -> dict:
    """
    Call Qwen Vision as fallback model.
    
    NOTE: This is a legacy wrapper. Use call_model_hardened() for production.
    """
    from agent.core.hardened_pipeline import call_qwen_with_retry
    
    circuit_breaker = get_circuit_breaker()
    result, error = call_qwen_with_retry(image_url, api_key, circuit_breaker)
    
    if result is None:
        raise Exception(f"Qwen failed: {error}")
    
    return result


def call_model_with_fallback(image_url: str, api_key: str) -> dict:
    """
    HARDENED model call with automatic fallback: Gemini → Qwen.
    
    Features:
    - Circuit breaker (disables failed models temporarily)
    - Exponential backoff retry (3 attempts per model)
    - Rate limiting (1 request per 2 seconds)
    - Image validation
    - Comprehensive logging
    - Graceful degradation (never crashes)
    
    Returns:
    - On success: parsed intent JSON with _model_used
    - On failure: status="error" with reason and retryable flag
    """
    return call_model_hardened(image_url, api_key, validate_image=True)


def _call_model_legacy_text(image_url: str, api_key: str) -> str:
    """Call legacy chat-completions OCR endpoint and return raw text."""
    response = requests.post(
        "https://gen.pollinations.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gemini-fast",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "decode and extract text"},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
        },
        timeout=90,
    )

    if response.status_code != 200:
        raise Exception(
            f"Model request failed: HTTP {response.status_code} - {response.text}"
        )

    payload = response.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise Exception("Model response missing message content") from exc

    return str(content).strip()


def call_model(image_url: str, api_key: str) -> dict | str:
    """
    Resilient model call strategy:
    1) hardened JSON model call
    2) fallback to legacy raw-text extraction
    """
    primary_error = None
    try:
        hardened = call_model_with_fallback(image_url, api_key)
        if isinstance(hardened, dict) and hardened.get("status") != "error":
            return hardened
        if isinstance(hardened, dict) and hardened.get("status") == "error":
            primary_error = hardened.get("reason", "hardened_model_error")
    except Exception as exc:
        primary_error = str(exc)

    try:
        return _call_model_legacy_text(image_url, api_key)
    except Exception as legacy_exc:
        raise Exception(f"Model calls failed: {primary_error}; legacy={legacy_exc}") from legacy_exc


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
        self._last_valid_result: InferenceResult | None = None
        self.context_manager = get_context_manager()
        self.received_dir.mkdir(parents=True, exist_ok=True)
        self.variants_dir.mkdir(parents=True, exist_ok=True)

    async def process_drawing(
        self,
        image_bytes: bytes,
        *,
        preferred_app: str | None = None,
    ) -> InferenceResult:
        """Deterministic perception -> intent conversion for drawing input."""
        print(f"\n{'='*70}")
        print(f"[EXECUTION-READY PIPELINE] Processing drawing")
        print(f"{'='*70}")

        input_image_path = self._save_image(image_bytes)
        image_url = ""

        try:
            image_url = await asyncio.to_thread(self._upload_image, input_image_path)
            candidate = await self._infer_attempt(
                input_image_path=input_image_path,
                variant_name="original",
                variant_path=input_image_path,
                image_url=image_url,
                model="gemini-fast",
            )
        except Exception as exc:
            candidate = InferenceCandidate(
                intent=build_unknown_intent(
                    message="Model unavailable",
                    confidence=0.0,
                    normalized_text="",
                ),
                normalized_text="",
                model="none",
                input_image_path=input_image_path,
                variant_name="original",
                image_path=input_image_path,
                image_url=image_url,
                raw_model_output=str(exc),
                message="Model unavailable",
                valid=False,
            )

        if candidate.intent.action == "OPEN_APP" and candidate.intent.confidence >= 0.7:
            print("[DIRECT EXECUTION RULE] OPEN_APP confidence >= 0.7")

        result = InferenceResult(
            intent=candidate.intent,
            normalized_text=candidate.normalized_text,
            model=candidate.model,
            input_image_path=input_image_path,
            variant_name=candidate.variant_name,
            image_path=candidate.image_path,
            image_url=candidate.image_url,
            raw_model_output=candidate.raw_model_output,
            message=candidate.message,
            ranking_score=candidate.intent.confidence,
            candidates=[candidate],
            consistency_score=1.0,
            trust_score=1.0,
            should_execute=True,
            validation_passed=True,
        )

        if result.intent.action != "UNKNOWN":
            self._last_valid_result = result

        return result

    async def process_text_input(self, text: str) -> InferenceResult:
        """Deterministic text -> intent parsing path (no model dependency)."""
        normalized_text = text.strip().lower()
        intent_name, slots = resolve_intent(normalized_text)
        confidence = 0.85 if intent_name != "UNKNOWN" else 0.0

        intent, message = self._build_intent_from_json(
            intent_name=intent_name,
            slots=slots,
            confidence=confidence,
            normalized_text=normalized_text,
        )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        input_path = self.received_dir / f"text_{timestamp}.txt"
        input_path.write_text(text, encoding="utf-8")

        candidate = InferenceCandidate(
            intent=intent,
            normalized_text=normalized_text,
            model="text-resolver",
            input_image_path=input_path,
            variant_name="text",
            image_path=input_path,
            image_url="",
            raw_model_output=text,
            message=message,
            valid=intent.action != "UNKNOWN",
        )

        result = InferenceResult(
            intent=candidate.intent,
            normalized_text=candidate.normalized_text,
            model=candidate.model,
            input_image_path=input_path,
            variant_name="text",
            image_path=input_path,
            image_url="",
            raw_model_output=text,
            message=message,
            ranking_score=candidate.intent.confidence,
            candidates=[candidate],
            consistency_score=1.0,
            trust_score=1.0,
            should_execute=True,
            validation_passed=True,
        )

        if result.intent.action != "UNKNOWN":
            self._last_valid_result = result

        return result

    async def close(self) -> None:
        return None

    def _save_image(self, image_bytes: bytes) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
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

    async def _infer_with_model(self, image_url: str) -> dict | str:
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
            # Model may return strict JSON or legacy raw OCR text.
            model_output = await self._infer_with_model(image_url=image_url)
            model_output = self._normalize_model_output(model_output)

            print("\n========== [MODEL OUTPUT RECEIVED] ==========")
            print(model_output)

            # Extract fields from strict JSON response
            intent_name = model_output.get("intent", "UNKNOWN")
            slots = model_output.get("slots", {})
            if intent_name == "MULTI_STEP" and isinstance(model_output.get("steps"), list):
                slots = dict(slots) if isinstance(slots, dict) else {}
                slots["steps"] = model_output.get("steps", [])
            confidence = model_output.get("confidence", 0.0)
            normalized_text = model_output.get("normalized_text", "")

            print(f"[INTENT] {intent_name}")
            print(f"[SLOTS] {slots}")
            print(f"[CONFIDENCE] {confidence}")
            print(f"[NORMALIZED TEXT] {normalized_text}")

            self._trace_block("MODEL JSON", model_output)

            # Build intent from JSON response
            intent, message = self._build_intent_from_json(
                intent_name=intent_name,
                slots=slots,
                confidence=confidence,
                normalized_text=normalized_text,
            )

            return InferenceCandidate(
                intent=intent,
                normalized_text=normalized_text,
                model=model,
                input_image_path=input_image_path,
                variant_name=variant_name,
                image_path=variant_path,
                image_url=image_url,
                raw_model_output=str(model_output),
                message=message,
                valid=intent.action != "UNKNOWN",
            )
        except Exception as exc:
            print(f"\n[INFERENCE ERROR] {exc}")
            self._trace_block("INFERENCE ERROR", {"error": str(exc)})
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

    def _build_intent_from_json(
        self,
        intent_name: str,
        slots: dict,
        confidence: float,
        normalized_text: str,
    ) -> tuple[Intent, str]:
        """Build Intent from strict JSON model response."""
        print(f"\n========== [BUILDING INTENT] ==========")
        print(f"Intent: {intent_name}, Slots: {slots}, Confidence: {confidence}")

        intent_name = str(intent_name or "UNKNOWN").strip().upper()
        if intent_name not in SUPPORTED_ENUM_INTENTS:
            intent_name = "UNKNOWN"

        try:
            model_confidence = float(confidence)
        except (TypeError, ValueError):
            model_confidence = 0.0
        model_confidence = max(0.0, min(1.0, model_confidence))

        if not isinstance(slots, dict):
            slots = {}

        slots = self._apply_context_resolution(intent_name, slots)

        metadata = {"normalized_text": normalized_text}

        if intent_name == "MULTI_STEP":
            steps = slots.get("steps", [])
            if not isinstance(steps, list):
                steps = []
            normalized_steps = []
            for step in steps:
                if not isinstance(step, dict):
                    continue
                step_intent = str(step.get("intent", "UNKNOWN")).strip().upper()
                if step_intent not in SUPPORTED_ENUM_INTENTS or step_intent == "UNKNOWN":
                    continue
                step_slots = step.get("slots", {})
                if not isinstance(step_slots, dict):
                    step_slots = {}
                normalized_steps.append({"intent": step_intent, "slots": step_slots})

            if not normalized_steps:
                return (
                    build_unknown_intent(
                        message="Could not determine multi-step actions",
                        confidence=0.0,
                        normalized_text=normalized_text,
                    ),
                    "Could not determine multi-step actions",
                )

            return (
                Intent(
                    action="MULTI_STEP",
                    parameters={"steps": normalized_steps},
                    confidence=model_confidence,
                    metadata=metadata,
                ),
                "Intent parsed from model JSON",
            )

        if intent_name == "OPEN_APP":
            raw_app = slots.get("app")
            corrected_app = correct_app(raw_app) if isinstance(raw_app, str) else None
            app_value = corrected_app or (raw_app.strip() if isinstance(raw_app, str) else "")
            print(f"[APP RESOLUTION] raw={raw_app} -> resolved={app_value}")

            if not app_value:
                return (
                    build_unknown_intent(
                        message="Could not determine app",
                        confidence=0.0,
                        normalized_text=normalized_text,
                    ),
                    "Could not determine app",
                )

            return (
                Intent(
                    action="OPEN_APP",
                    parameters={"app": app_value},
                    confidence=model_confidence,
                    metadata=metadata,
                ),
                "Intent parsed from model JSON",
            )

        if intent_name == "OPEN_URL":
            url = slots.get("url")
            if not url:
                return (
                    build_unknown_intent(
                        message="No URL provided",
                        confidence=0.0,
                        normalized_text=normalized_text,
                    ),
                    "No URL provided",
                )
            url = str(url).strip()
            if url and not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            return (
                Intent(
                    action="OPEN_URL",
                    parameters={"url": url},
                    confidence=model_confidence,
                    metadata=metadata,
                ),
                "Intent parsed from model JSON",
            )

        if intent_name == "SEARCH_WEB":
            query = str(slots.get("query", normalized_text)).strip()
            return (
                Intent(
                    action="SEARCH_WEB",
                    parameters={"query": query},
                    confidence=model_confidence,
                    metadata=metadata,
                ),
                "Intent parsed from model JSON",
            )

        if intent_name == "TYPE_TEXT":
            text = str(slots.get("text", ""))
            return (
                Intent(
                    action="TYPE_TEXT",
                    parameters={"text": text},
                    confidence=model_confidence,
                    metadata=metadata,
                ),
                "Intent parsed from model JSON",
            )

        if intent_name == "SAVE_FILE":
            save_slots: dict[str, str] = {}
            filename = slots.get("filename")
            app = slots.get("app")
            if isinstance(filename, str) and filename.strip():
                save_slots["filename"] = filename.strip()
            if isinstance(app, str) and app.strip():
                save_slots["app"] = app.strip()
            return (
                Intent(
                    action="SAVE_FILE",
                    parameters=save_slots,
                    confidence=model_confidence,
                    metadata=metadata,
                ),
                "Intent parsed from model JSON",
            )

        if intent_name == "CLOSE_APP":
            app = slots.get("app")
            close_slots = {"app": str(app).strip()} if isinstance(app, str) and app.strip() else {}
            return (
                Intent(
                    action="CLOSE_APP",
                    parameters=close_slots,
                    confidence=model_confidence,
                    metadata=metadata,
                ),
                "Intent parsed from model JSON",
            )

        if intent_name in {
            "MINIMIZE_APP", "MAXIMIZE_APP", "RESTORE_APP", "SWITCH_APP", "FOCUS_WINDOW",
            "NEW_TAB", "CLOSE_TAB", "SWITCH_TAB", "REFRESH_PAGE", "SCROLL_UP", "SCROLL_DOWN",
            "SAVE_FILE", "CLEAR_TEXT", "SELECT_TEXT", "COPY", "PASTE", "CUT", "PRESS_KEYS",
            "LOCK_SCREEN", "MINIMIZE_ALL", "MAXIMIZE_ALL", "VOLUME_UP", "VOLUME_DOWN", "MUTE", "UNMUTE", "BRIGHTNESS_UP", "BRIGHTNESS_DOWN",
            "OPEN_FILE", "DELETE_FILE", "CREATE_FILE", "MOVE_FILE", "RENAME_FILE",
            "CLICK_ELEMENT", "SCROLL", "WAIT", "CONDITIONAL", "CONFIRMATION_REQUIRED",
            "SCREENSHOT", "MINIMIZE", "MAXIMIZE",
        }:
            return (
                Intent(
                    action=intent_name,
                    parameters=slots,
                    confidence=model_confidence,
                    metadata=metadata,
                ),
                "Intent parsed from model JSON",
            )

        return (
            build_unknown_intent(
                message="Could not determine intent",
                confidence=0.0,
                normalized_text=normalized_text,
            ),
            "Could not determine intent",
        )

    def _apply_context_resolution(self, intent_name: str, slots: dict) -> dict:
        if intent_name not in APP_CONTEXT_INTENTS:
            return slots

        resolved_slots = dict(slots)
        resolved_slots = _strip_pronoun_slots(intent_name, resolved_slots)

        if not resolved_slots.get("app"):
            resolved_app = self.context_manager.resolve_app(resolved_slots)
            if resolved_app:
                resolved_slots["app"] = resolved_app
                print(f"[CONTEXT INJECTED] {resolved_app}")

        if intent_name == "FOCUS_WINDOW" and not resolved_slots.get("window") and resolved_slots.get("app"):
            resolved_slots["window"] = resolved_slots["app"]

        print(f"[CONTEXT RESOLVED APP] {resolved_slots.get('app')}")
        return resolved_slots

    def _normalize_model_output(self, model_output: dict | str) -> dict:
        """Normalize model output from either JSON or legacy text OCR."""
        if isinstance(model_output, dict):
            normalized_text = str(model_output.get("normalized_text", "")).strip().lower()
            if not normalized_text and isinstance(model_output.get("text"), str):
                normalized_text = str(model_output.get("text", "")).strip().lower()

            try:
                confidence = float(model_output.get("confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
            confidence = max(0.0, min(1.0, confidence))

            # IGNORE MODEL INTENT COMPLETELY
            intent_name = None
            slots = {}
            _ = intent_name, slots

            final_intent = "UNKNOWN"
            final_slots: dict = {}
            if normalized_text:
                final_intent, final_slots = resolve_intent(normalized_text)

            print(f"[FINAL INTENT LOCKED] {final_intent}")

            return {
                "intent": final_intent if final_intent in SUPPORTED_ENUM_INTENTS else "UNKNOWN",
                "slots": final_slots,
                "steps": [],
                "confidence": confidence,
                "normalized_text": normalized_text,
            }

        if not isinstance(model_output, str):
            raise StageZeroValidationError("Unsupported model output type")

        cleaned_output = clean_json_response(model_output)
        if cleaned_output.startswith("{"):
            try:
                parsed_output = json.loads(cleaned_output)
            except json.JSONDecodeError:
                parsed_output = None
            if isinstance(parsed_output, dict):
                return self._normalize_model_output(parsed_output)

        normalized_text = model_output.strip().lower()
        intent_name, slots = resolve_intent(normalized_text)
        print(f"[FINAL INTENT LOCKED] {intent_name}")

        return {
            "intent": intent_name,
            "slots": slots,
            "steps": [],
            "confidence": 0.85 if intent_name != "UNKNOWN" else 0.0,
            "normalized_text": normalized_text,
        }

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

    def _build_debug_curl(self, model: str, image_url: str, prompt_text: str) -> str:
        """Build a masked curl command for reproducing model requests."""
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        }
        command = (
            "curl -X POST "
            f"\"https://gen.pollinations.ai/v1/chat/completions?key={self.api_key}\" "
            "-H \"Content-Type: application/json\" "
            f"-d \"{json.dumps(payload)}\""
        )
        return self._mask_sensitive(command)


def select_best_result(results: list[InferenceCandidate]) -> InferenceCandidate | None:
    """Select the highest-confidence candidate deterministically."""
    if not results:
        return None
    return max(results, key=lambda candidate: candidate.intent.confidence)
