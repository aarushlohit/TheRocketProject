from agent.core.intent import Intent
from agent.stage0.validation import (
    KNOWN_APPS,
    StageZeroValidationError,
    build_unknown_intent,
    extract_json_object,
    guard_intent,
    validate_ai_payload,
)


def test_extract_json_from_code_fence():
    payload = extract_json_object(
        """```json
        {"extracted_text":"open chrome","intent":"OPEN_APP","slots":{"app":"firefox"},"confidence":0.93,"message":"ok"}
        ```"""
    )

    assert payload["intent"] == "OPEN_APP"
    assert payload["extracted_text"] == "open chrome"


def test_validate_open_url_derives_from_extracted_text():
    intent, cleaned_text, debug_info = validate_ai_payload(
        {
            "extracted_text": "open google.com",
            "intent": "OPEN_URL",
            "slots": {"url": "not-used.com"},
            "confidence": 0.88,
            "message": "ok",
        }
    )

    assert intent.action == "OPEN_URL"
    assert intent.parameters["url"] == "https://google.com"
    assert cleaned_text == "open google.com"
    assert debug_info["detected_app"] is None


def test_validate_rejects_missing_extracted_text():
    try:
        validate_ai_payload(
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.91,
                "message": "shortcut",
            }
        )
    except StageZeroValidationError as exc:
        assert "extracted_text must be a non-empty string" in str(exc)
        return

    raise AssertionError("Expected validation failure for missing extracted_text")


def test_validate_rejects_model_shortcut_without_extracted_text():
    try:
        validate_ai_payload(
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.91,
                "normalized_text": "chrome",
                "message": "shortcut",
            }
        )
    except StageZeroValidationError as exc:
        assert "rejecting model shortcut" in str(exc)
        return

    raise AssertionError("Expected shortcut rejection when extracted_text is missing")


def test_validate_ignores_hallucinated_slot_and_uses_extracted_text():
    intent, cleaned_text, debug_info = validate_ai_payload(
        {
            "extracted_text": "open vscode",
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.95,
            "message": "ok",
        }
    )

    assert intent.action == "OPEN_APP"
    assert intent.parameters["app"] == "vscode"
    assert cleaned_text == "open vscode"
    assert debug_info["detected_app"] == "vscode"


def test_validate_fuzzy_corrects_vscod():
    intent, cleaned_text, debug_info = validate_ai_payload(
        {
            "extracted_text": "open vscod",
            "intent": "OPEN_APP",
            "slots": {},
            "confidence": 0.9,
            "message": "ok",
        }
    )

    assert intent.action == "OPEN_APP"
    assert intent.parameters["app"] == "vscode"
    assert cleaned_text == "open vscod"
    assert debug_info["detected_app"] == "vscode"


def test_validate_returns_unknown_when_app_not_matched():
    intent, _, debug_info = validate_ai_payload(
        {
            "extracted_text": "open splunk",
            "intent": "OPEN_APP",
            "slots": {},
            "confidence": 0.95,
            "message": "ok",
        }
    )

    assert intent.action == "UNKNOWN"
    assert intent.confidence == 0.4
    assert debug_info["detected_app"] is None


def test_guard_intent_downgrades_unknown_app_to_unknown():
    guarded_intent, message = guard_intent(
        Intent(
            action="OPEN_APP",
            parameters={"app": "spotify"},
            confidence=0.91,
            metadata={"normalized_text": "open spotify"},
        )
    )

    assert "spotify" not in KNOWN_APPS
    assert guarded_intent.action == "UNKNOWN"
    assert guarded_intent.confidence == 0.5
    assert message == "Uncertain intent"


def test_build_unknown_intent():
    intent = build_unknown_intent(
        message="Could not determine intent",
        confidence=0.4,
        normalized_text="scribble",
    )

    assert intent.action == "UNKNOWN"
    assert intent.confidence == 0.4
    assert intent.metadata["message"] == "Could not determine intent"
