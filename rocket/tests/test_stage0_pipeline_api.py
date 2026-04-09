import asyncio
import io
from pathlib import Path

from PIL import Image

from agent.stage0 import pipeline as pipeline_module
from agent.stage0.pipeline import (
    DrawToActionPipeline,
    call_model,
    extract_app_name,
    parse_intent,
    validate_api_key,
)
from agent.stage0.validation import StageZeroValidationError


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (12, 12), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_call_model_uses_chat_completions_post(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        text = '{"choices": [{"message": {"content": "open chrome"}}]}'

        def json(self):
            return {"choices": [{"message": {"content": "open chrome"}}]}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(pipeline_module.requests, "post", fake_post)

    result = call_model("https://media.pollinations.ai/example.png", "secret-key")

    assert result == "open chrome"
    assert captured["timeout"] == 90
    assert captured["url"] == "https://gen.pollinations.ai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["json"]["model"] == "gemini-fast"
    assert captured["json"]["messages"][0]["content"][0] == {
        "type": "text",
        "text": "decode and extract text",
    }
    assert captured["json"]["messages"][0]["content"][1] == {
        "type": "image_url",
        "image_url": {"url": "https://media.pollinations.ai/example.png"},
    }


def test_call_model_raises_on_non_200(monkeypatch):
    class FakeResponse:
        status_code = 500
        text = "server error"

        def json(self):
            return {}

    monkeypatch.setattr(
        pipeline_module.requests,
        "post",
        lambda url, headers, json, timeout: FakeResponse(),
    )

    try:
        call_model("https://media.pollinations.ai/example.png", "key")
    except Exception as exc:
        assert "Model request failed" in str(exc)
        return

    raise AssertionError("Expected model request failure")


def test_upload_image_uses_official_media_post(monkeypatch, tmp_path):
    image_path = Path(tmp_path) / "sample.png"
    Image.new("RGB", (4, 4), color="white").save(image_path)
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"url": "https://media.pollinations.ai/example.png"}

    def fake_post(url, headers, files, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        assert "file" in files
        return FakeResponse()

    monkeypatch.setattr(pipeline_module.requests, "post", fake_post)

    pipeline = DrawToActionPipeline(
        api_key="secret-key",
        storage_dir=Path(tmp_path),
        trace_mode=False,
    )
    result = pipeline._upload_image(image_path)

    assert result == "https://media.pollinations.ai/example.png"
    assert captured["url"] == "https://media.pollinations.ai/upload"
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    assert captured["timeout"] == 60


def test_extract_app_name_open_chrome():
    assert extract_app_name("open chrome") == "chrome"


def test_extract_app_name_without_second_word():
    assert extract_app_name("open") is None


def test_parse_intent_open_app():
    parsed = parse_intent("open chrome")
    assert parsed["intent"] == "OPEN_APP"
    assert parsed["slots"] == {"app": "chrome"}
    assert parsed["normalized_text"] == "open chrome"


def test_parse_intent_close():
    parsed = parse_intent("close window")
    assert parsed["intent"] == "CLOSE_APP"
    assert parsed["slots"] == {"app": "window"}


def test_parse_intent_restore():
    parsed = parse_intent("restore window")
    assert parsed["intent"] == "RESTORE_APP"
    assert parsed["slots"] == {}


def test_parse_intent_screenshot():
    parsed = parse_intent("take screenshot now")
    assert parsed["intent"] == "SCREENSHOT"


def test_parse_intent_unknown():
    parsed = parse_intent("hello world")
    assert parsed["intent"] == "UNKNOWN"


def test_process_drawing_uses_ocr_text_for_intent(monkeypatch, tmp_path):
    async def fake_infer_with_model(self, image_url):
        return "open chrome\n"

    monkeypatch.setattr(DrawToActionPipeline, "_infer_with_model", fake_infer_with_model)
    monkeypatch.setattr(
        DrawToActionPipeline,
        "_upload_image",
        lambda self, image_path: "https://media.pollinations.ai/example.png",
    )

    pipeline = DrawToActionPipeline(
        api_key="secret-key",
        storage_dir=Path(tmp_path),
        trace_mode=False,
    )

    result = asyncio.run(pipeline.process_drawing(_png_bytes()))

    assert result.intent.action == "OPEN_APP"
    assert result.intent.parameters == {"app": "chrome"}
    assert result.normalized_text == "open chrome"


def test_process_drawing_returns_unknown_for_unmatched_app(monkeypatch, tmp_path):
    async def fake_infer_with_model(self, image_url):
        return "open splunk\n"

    monkeypatch.setattr(DrawToActionPipeline, "_infer_with_model", fake_infer_with_model)
    monkeypatch.setattr(
        DrawToActionPipeline,
        "_upload_image",
        lambda self, image_path: "https://media.pollinations.ai/example.png",
    )

    pipeline = DrawToActionPipeline(
        api_key="secret-key",
        storage_dir=Path(tmp_path),
        trace_mode=False,
    )

    result = asyncio.run(pipeline.process_drawing(_png_bytes()))

    assert result.intent.action == "OPEN_APP"
    assert result.intent.parameters == {"app": "splunk"}


def test_process_drawing_does_not_reuse_last_valid_intent_on_model_failure(monkeypatch, tmp_path):
    calls = {"count": 0}

    async def fake_infer_with_model(self, image_url):
        calls["count"] += 1
        if calls["count"] == 1:
            return "open chrome\n"
        raise RuntimeError("model down")

    monkeypatch.setattr(DrawToActionPipeline, "_infer_with_model", fake_infer_with_model)
    monkeypatch.setattr(
        DrawToActionPipeline,
        "_upload_image",
        lambda self, image_path: "https://media.pollinations.ai/example.png",
    )

    pipeline = DrawToActionPipeline(
        api_key="secret-key",
        storage_dir=Path(tmp_path),
        trace_mode=False,
    )

    first = asyncio.run(pipeline.process_drawing(_png_bytes()))
    second = asyncio.run(pipeline.process_drawing(_png_bytes()))

    assert first.intent.action == "OPEN_APP"
    assert second.intent.action == "UNKNOWN"


def test_process_text_input_uses_resolve_intent_not_multistep(tmp_path):
    pipeline = DrawToActionPipeline(
        api_key="secret-key",
        storage_dir=Path(tmp_path),
        trace_mode=False,
    )

    result = asyncio.run(pipeline.process_text_input("open chrome and search github"))

    assert result.intent.action == "UNKNOWN"


def test_normalize_model_output_ignores_model_intent_for_volume(tmp_path):
    pipeline = DrawToActionPipeline(
        api_key="secret-key",
        storage_dir=Path(tmp_path),
        trace_mode=False,
    )

    normalized = pipeline._normalize_model_output(
        {
            "intent": "PRESS_KEYS",
            "slots": {"keys": "volumeup"},
            "confidence": 0.9,
            "normalized_text": "volume up more",
        }
    )

    assert normalized["intent"] == "VOLUME_UP"
    assert normalized["slots"] == {"value": 10}


def test_normalize_model_output_blocks_model_multistep(tmp_path):
    pipeline = DrawToActionPipeline(
        api_key="secret-key",
        storage_dir=Path(tmp_path),
        trace_mode=False,
    )

    normalized = pipeline._normalize_model_output(
        {
            "intent": "MULTI_STEP",
            "steps": [
                {"intent": "OPEN_APP", "slots": {"app": "chrome"}},
                {"intent": "SEARCH_WEB", "slots": {"query": "github"}},
            ],
            "confidence": 0.9,
            "normalized_text": "open chrome and search github",
        }
    )

    assert normalized["intent"] == "UNKNOWN"
    assert normalized["slots"] == {}


def test_process_text_input_resolves_unmute(tmp_path):
    pipeline = DrawToActionPipeline(
        api_key="secret-key",
        storage_dir=Path(tmp_path),
        trace_mode=False,
    )

    result = asyncio.run(pipeline.process_text_input("unmute"))

    assert result.intent.action == "UNMUTE"


def test_process_text_input_resolves_minimize_all(tmp_path):
    pipeline = DrawToActionPipeline(
        api_key="secret-key",
        storage_dir=Path(tmp_path),
        trace_mode=False,
    )

    result = asyncio.run(pipeline.process_text_input("show desktop"))

    assert result.intent.action == "MINIMIZE_ALL"


def test_validate_api_key_success(monkeypatch):
    class FakeResp:
        status_code = 200
        text = "ok"

    monkeypatch.setattr(
        pipeline_module.requests,
        "get",
        lambda url, headers, timeout: FakeResp(),
    )
    assert validate_api_key("good-key") is True


def test_validate_api_key_failure(monkeypatch):
    class FakeResp:
        status_code = 401
        text = "unauthorized"

    monkeypatch.setattr(
        pipeline_module.requests,
        "get",
        lambda url, headers, timeout: FakeResp(),
    )
    try:
        validate_api_key("bad-key")
    except StageZeroValidationError as exc:
        assert "Invalid API key" in str(exc)
        return

    raise AssertionError("Expected invalid key failure")
