"""Validation helpers for structured AI output."""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from agent.core.intent import Intent


ALLOWED_INTENTS = {
    "OPEN_APP",
    "CLOSE_APP",
    "MINIMIZE",
    "MAXIMIZE",
    "SCREENSHOT",
    "OPEN_URL",
}


class StageZeroValidationError(ValueError):
    """Raised when the AI response is missing required structure."""


def extract_json_object(raw_response: str) -> dict:
    """Extract the first JSON object from an LLM response."""
    cleaned = raw_response.strip()
    cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        start_index = cleaned.find("{")
        if start_index == -1:
            raise StageZeroValidationError("Model response does not contain a JSON object")

        parsed = None
        while start_index != -1:
            try:
                candidate, _ = decoder.raw_decode(cleaned[start_index:])
                parsed = candidate
                break
            except json.JSONDecodeError:
                start_index = cleaned.find("{", start_index + 1)

        if parsed is None:
            raise StageZeroValidationError("Could not decode a valid JSON object from model response")

    if not isinstance(parsed, dict):
        raise StageZeroValidationError("Model response must be a JSON object")

    return parsed


def validate_ai_payload(payload: dict) -> tuple[Intent, str]:
    """Validate raw AI output and convert it into an executable Intent."""
    intent_name = payload.get("intent")
    slots = payload.get("slots")
    confidence = payload.get("confidence")
    normalized_text = payload.get("normalized_text")

    if intent_name not in ALLOWED_INTENTS:
        raise StageZeroValidationError(f"Unsupported intent: {intent_name}")
    if not isinstance(slots, dict):
        raise StageZeroValidationError("slots must be a JSON object")
    if not isinstance(confidence, (int, float)):
        raise StageZeroValidationError("confidence must be numeric")
    if not 0.0 <= float(confidence) <= 1.0:
        raise StageZeroValidationError("confidence must be between 0 and 1")
    if not isinstance(normalized_text, str) or not normalized_text.strip():
        raise StageZeroValidationError("normalized_text must be a non-empty string")

    normalized_slots = _normalize_slots(intent_name, slots)
    intent = Intent(
        action=intent_name,
        parameters=normalized_slots,
        confidence=float(confidence),
        metadata={"normalized_text": normalized_text.strip()},
    )
    intent.validate()
    return intent, normalized_text.strip()


def _normalize_slots(intent_name: str, slots: dict) -> dict:
    if intent_name == "OPEN_APP":
        app = _get_required_string(slots, "app")
        return {"app": app.lower()}

    if intent_name == "CLOSE_APP":
        app = _get_optional_string(slots, "app")
        target = _get_optional_string(slots, "target") or "focused"
        if app:
            return {"app": app.lower(), "target": target}
        return {"target": target}

    if intent_name in {"MINIMIZE", "MAXIMIZE"}:
        app = _get_optional_string(slots, "app")
        target = _get_optional_string(slots, "target") or "focused"
        normalized = {"target": target}
        if app:
            normalized["app"] = app.lower()
        return normalized

    if intent_name == "SCREENSHOT":
        return {}

    if intent_name == "OPEN_URL":
        url = _get_required_string(slots, "url")
        parsed = urlparse(url if "://" in url else f"https://{url}")
        if not parsed.scheme or not parsed.netloc:
            raise StageZeroValidationError("OPEN_URL requires a valid absolute URL")
        return {"url": parsed.geturl()}

    raise StageZeroValidationError(f"Unhandled intent: {intent_name}")


def _get_required_string(payload: dict, key: str) -> str:
    value = _get_optional_string(payload, key)
    if not value:
        raise StageZeroValidationError(f"slots.{key} is required")
    return value


def _get_optional_string(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise StageZeroValidationError(f"slots.{key} must be a non-empty string")
    return value.strip()
