"""Validation helpers for structured AI output."""

from __future__ import annotations

import difflib
import json
import re
from urllib.parse import urlparse

from agent.core.intent import Intent
from agent.utils.app_map import canonicalize_app_name


ALLOWED_INTENTS = {
    "OPEN_APP",
    "CLOSE_APP",
    "MINIMIZE",
    "MAXIMIZE",
    "SCREENSHOT",
    "OPEN_URL",
    "UNKNOWN",
}

KNOWN_APPS = [
    "chrome",
    "firefox",
    "calculator",
    "terminal",
    "vscode",
]

TEXT_APP_MAP = {
    "browser": "chrome",
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "calculator": "calculator",
    "calc": "calculator",
    "terminal": "terminal",
    "cmd": "terminal",
    "vscode": "vscode",
    "vs code": "vscode",
    "code": "vscode",
}

ACTION_ALIASES = {
    "open": "OPEN_APP",
    "close": "CLOSE_APP",
    "minimize": "MINIMIZE",
    "minimise": "MINIMIZE",
    "maximize": "MAXIMIZE",
    "maximise": "MAXIMIZE",
    "screenshot": "SCREENSHOT",
    "screen": "SCREENSHOT",
    "capture": "SCREENSHOT",
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


def validate_ai_payload(payload: dict) -> tuple[Intent, str, dict]:
    """Validate raw AI output and convert it into a text-derived executable Intent."""
    extracted_text = payload.get("extracted_text")
    model_intent = payload.get("intent")
    slots = payload.get("slots")
    confidence = payload.get("confidence")
    normalized_text = payload.get("normalized_text")
    message = payload.get("message")

    if not isinstance(slots, dict):
        raise StageZeroValidationError("slots must be a JSON object")
    if not isinstance(confidence, (int, float)):
        raise StageZeroValidationError("confidence must be numeric")
    if not 0.0 <= float(confidence) <= 1.0:
        raise StageZeroValidationError("confidence must be between 0 and 1")
    if not isinstance(extracted_text, str) or not extracted_text.strip():
        if isinstance(normalized_text, str) and normalized_text.strip():
            raise StageZeroValidationError(
                "extracted_text is required; rejecting model shortcut without text extraction"
            )
        raise StageZeroValidationError("extracted_text must be a non-empty string")
    if model_intent is not None and model_intent not in ALLOWED_INTENTS:
        raise StageZeroValidationError(f"Unsupported intent: {model_intent}")

    raw_extracted_text = extracted_text.strip()
    cleaned_text = _clean_extracted_text(raw_extracted_text)
    if not cleaned_text:
        raise StageZeroValidationError("extracted_text could not be cleaned into usable text")

    intent, debug_info = derive_intent_from_text(
        raw_text=raw_extracted_text,
        cleaned_text=cleaned_text,
        confidence=float(confidence),
        message=message if isinstance(message, str) else None,
    )
    intent.metadata = {
        "normalized_text": cleaned_text,
        "extracted_text": raw_extracted_text,
        "message": intent.metadata.get("message") if intent.metadata else None,
        "model_intent": model_intent,
        "model_slots": slots,
        "debug": debug_info,
    }
    intent.validate()
    return intent, cleaned_text, debug_info


def guard_intent(intent: Intent) -> tuple[Intent, str | None]:
    """Apply Stage 1 reliability guards before execution is allowed."""
    message = _message_from_metadata(intent)

    if "app" in intent.parameters and isinstance(intent.parameters["app"], str):
        canonical_app = canonicalize_app_name(intent.parameters["app"])
        intent.parameters["app"] = canonical_app
        if canonical_app not in KNOWN_APPS:
            intent.confidence = min(intent.confidence, 0.5)
            message = "Uncertain intent"

    if intent.action == "UNKNOWN":
        return build_unknown_intent(
            message=message or "Could not determine intent",
            confidence=min(intent.confidence, 0.4),
            normalized_text=_normalized_text_from_metadata(intent),
        ), message or "Could not determine intent"

    if intent.confidence < 0.6:
        return build_unknown_intent(
            message=message or "Uncertain intent",
            confidence=0.5,
            normalized_text=_normalized_text_from_metadata(intent),
        ), message or "Uncertain intent"

    return intent, message


def build_unknown_intent(
    message: str = "Could not determine intent",
    confidence: float = 0.4,
    normalized_text: str = "",
) -> Intent:
    """Construct a safe UNKNOWN intent that will never execute."""
    return Intent(
        action="UNKNOWN",
        parameters={},
        confidence=confidence,
        metadata={
            "normalized_text": normalized_text,
            "message": message,
        },
    )


def derive_intent_from_text(
    *,
    raw_text: str,
    cleaned_text: str,
    confidence: float,
    message: str | None,
) -> tuple[Intent, dict]:
    """Derive intent from extracted text instead of trusting model slots."""
    debug_info = {
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "detected_app": None,
    }

    if _text_is_unclear(raw_text, cleaned_text):
        intent = build_unknown_intent(
            message=message or "Uncertain intent",
            confidence=0.4,
            normalized_text=cleaned_text,
        )
        return intent, debug_info

    action_name, app_name = text_to_intent(cleaned_text)
    debug_info["detected_app"] = app_name
    if action_name is None:
        intent = build_unknown_intent(
            message=message or "Could not determine intent",
            confidence=0.4,
            normalized_text=cleaned_text,
        )
        return intent, debug_info

    if action_name == "OPEN_APP":
        if not app_name or canonicalize_app_name(app_name) not in KNOWN_APPS:
            debug_info["detected_app"] = None
            intent = build_unknown_intent(
                message=message or "Uncertain intent",
                confidence=0.4,
                normalized_text=cleaned_text,
            )
            return intent, debug_info

        return (
            Intent(
                action="OPEN_APP",
                parameters={"app": app_name},
                confidence=confidence,
                metadata={"normalized_text": cleaned_text, "message": message},
            ),
            debug_info,
        )

    if action_name == "OPEN_URL":
        url = _extract_url_from_text(cleaned_text)
        if not url:
            intent = build_unknown_intent(
                message=message or "Uncertain intent",
                confidence=0.4,
                normalized_text=cleaned_text,
            )
            return intent, debug_info
        return (
            Intent(
                action="OPEN_URL",
                parameters={"url": url},
                confidence=confidence,
                metadata={"normalized_text": cleaned_text, "message": message},
            ),
            debug_info,
        )

    if action_name == "SCREENSHOT":
        return (
            Intent(
                action="SCREENSHOT",
                parameters={},
                confidence=confidence,
                metadata={"normalized_text": cleaned_text, "message": message},
            ),
            debug_info,
        )

    tokens = cleaned_text.split()
    post_action_tokens = _post_action_tokens(tokens)
    if (
        action_name in {"CLOSE_APP", "MINIMIZE", "MAXIMIZE"}
        and post_action_tokens
        and app_name is None
        and post_action_tokens[0] not in {"focused", "window"}
    ):
        intent = build_unknown_intent(
            message=message or "Uncertain intent",
            confidence=0.4,
            normalized_text=cleaned_text,
        )
        return intent, debug_info
    parameters = {"target": "focused"}
    if app_name:
        parameters["app"] = app_name
    return (
        Intent(
            action=action_name,
            parameters=parameters,
            confidence=confidence,
            metadata={"normalized_text": cleaned_text, "message": message},
        ),
        debug_info,
    )


def _normalize_slots(intent_name: str, slots: dict) -> dict:
    if intent_name == "OPEN_APP":
        app = _get_required_string(slots, "app")
        return {"app": canonicalize_app_name(app)}

    if intent_name == "CLOSE_APP":
        app = _get_optional_string(slots, "app")
        target = _get_optional_string(slots, "target") or "focused"
        if app:
            return {"app": canonicalize_app_name(app), "target": target}
        return {"target": target}

    if intent_name in {"MINIMIZE", "MAXIMIZE"}:
        app = _get_optional_string(slots, "app")
        target = _get_optional_string(slots, "target") or "focused"
        normalized = {"target": target}
        if app:
            normalized["app"] = canonicalize_app_name(app)
        return normalized

    if intent_name == "SCREENSHOT":
        return {}

    if intent_name == "OPEN_URL":
        url = _get_required_string(slots, "url")
        parsed = urlparse(url if "://" in url else f"https://{url}")
        if not parsed.scheme or not parsed.netloc:
            raise StageZeroValidationError("OPEN_URL requires a valid absolute URL")
        return {"url": parsed.geturl()}

    if intent_name == "UNKNOWN":
        return {}

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


def _normalized_text_from_metadata(intent: Intent) -> str:
    if intent.metadata and isinstance(intent.metadata.get("normalized_text"), str):
        return intent.metadata["normalized_text"]
    return ""


def _message_from_metadata(intent: Intent) -> str | None:
    if intent.metadata and isinstance(intent.metadata.get("message"), str):
        return intent.metadata["message"]
    return None


def text_to_intent(text: str) -> tuple[str | None, str | None]:
    """Derive intent and app directly from extracted text."""
    lowered = text.lower()
    tokens = lowered.split()

    intent = None
    if "open" in tokens:
        if _extract_url_from_text(lowered):
            intent = "OPEN_URL"
            return intent, None
        else:
            intent = "OPEN_APP"
    elif "close" in tokens:
        intent = "CLOSE_APP"
    elif "screenshot" in tokens or "screen" in tokens or "capture" in tokens:
        intent = "SCREENSHOT"
    elif "minimize" in tokens or "minimise" in tokens:
        intent = "MINIMIZE"
    elif "maximize" in tokens or "maximise" in tokens:
        intent = "MAXIMIZE"

    app = None
    if len(tokens) > 1:
        action_index = 0
        for index, token in enumerate(tokens):
            if token in ACTION_ALIASES:
                action_index = index
                break
        if action_index + 1 < len(tokens):
            app = correct_app(tokens[action_index + 1])

    return intent, app


def correct_app(app: str | None) -> str | None:
    """Fuzzy-correct an extracted app token against known apps."""
    if not app:
        return None

    direct = TEXT_APP_MAP.get(app)
    if direct:
        return canonicalize_app_name(direct)

    match = difflib.get_close_matches(app, KNOWN_APPS, n=1, cutoff=0.6)
    if match:
        return canonicalize_app_name(match[0])

    alias_match = difflib.get_close_matches(app, list(TEXT_APP_MAP.keys()), n=1, cutoff=0.6)
    if alias_match:
        return canonicalize_app_name(TEXT_APP_MAP[alias_match[0]])

    return app


def _clean_extracted_text(text: str) -> str:
    lowered = text.strip().lower()
    cleaned = re.sub(r"[^a-z0-9.:/\-\s]", " ", lowered)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _text_is_unclear(raw_text: str, cleaned_text: str) -> bool:
    if not cleaned_text or len(cleaned_text) < 3:
        return True
    unclear_markers = {"?", "unclear", "illegible", "unknown"}
    lowered = raw_text.lower()
    return any(marker in lowered for marker in unclear_markers)


def _detect_action(tokens: list[str]) -> str | None:
    if not tokens:
        return None

    url_candidate = _extract_url_from_text(" ".join(tokens))
    if url_candidate and "open" in tokens:
        return "OPEN_URL"

    for token in tokens[:3]:
        direct = ACTION_ALIASES.get(token)
        if direct:
            return direct

        fuzzy = difflib.get_close_matches(token, list(ACTION_ALIASES.keys()), n=1, cutoff=0.75)
        if fuzzy:
            return ACTION_ALIASES[fuzzy[0]]

    return None


def _extract_app_from_text(tokens: list[str]) -> str | None:
    remaining = _post_action_tokens(tokens)
    if not remaining:
        return None

    if len(remaining) >= 2:
        phrase = " ".join(remaining[:2])
        direct = TEXT_APP_MAP.get(phrase)
        if direct:
            return canonicalize_app_name(direct)

    candidate = remaining[0]
    direct = TEXT_APP_MAP.get(candidate)
    if direct:
        return canonicalize_app_name(direct)

    fuzzy = difflib.get_close_matches(candidate, list(TEXT_APP_MAP.keys()), n=1, cutoff=0.7)
    if fuzzy:
        return canonicalize_app_name(TEXT_APP_MAP[fuzzy[0]])

    fuzzy_known = difflib.get_close_matches(candidate, KNOWN_APPS, n=1, cutoff=0.7)
    if fuzzy_known:
        return canonicalize_app_name(fuzzy_known[0])

    return None


def _post_action_tokens(tokens: list[str]) -> list[str]:
    if not tokens:
        return []

    action_index = 0
    for index, token in enumerate(tokens):
        if _detect_action([token]) is not None:
            action_index = index
            break

    return [
        token
        for token in tokens[action_index + 1 :]
        if token not in {"app", "the", "please"}
    ]


def _extract_url_from_text(cleaned_text: str) -> str | None:
    match = re.search(r"(https?://\S+|www\.\S+|[a-z0-9-]+\.[a-z]{2,})", cleaned_text)
    if not match:
        return None

    url = match.group(1)
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if not parsed.scheme or not parsed.netloc:
        return None
    return parsed.geturl()
