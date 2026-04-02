from agent.stage0.validation import (
    StageZeroValidationError,
    extract_json_object,
    validate_ai_payload,
)


def test_extract_json_from_code_fence():
    payload = extract_json_object(
        """```json
        {"intent":"OPEN_APP","slots":{"app":"chrome"},"confidence":0.93,"normalized_text":"open chrome"}
        ```"""
    )

    assert payload["intent"] == "OPEN_APP"
    assert payload["slots"]["app"] == "chrome"


def test_validate_open_url_adds_https():
    intent, normalized_text = validate_ai_payload(
        {
            "intent": "OPEN_URL",
            "slots": {"url": "google.com"},
            "confidence": 0.88,
            "normalized_text": "open google.com",
        }
    )

    assert intent.action == "OPEN_URL"
    assert intent.parameters["url"] == "https://google.com"
    assert normalized_text == "open google.com"


def test_validate_rejects_missing_required_slot():
    try:
        validate_ai_payload(
            {
                "intent": "OPEN_APP",
                "slots": {},
                "confidence": 0.91,
                "normalized_text": "open chrome",
            }
        )
    except StageZeroValidationError as exc:
        assert "slots.app is required" in str(exc)
        return

    raise AssertionError("Expected validation failure for missing app slot")
