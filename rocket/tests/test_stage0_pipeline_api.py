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
    assert parse_intent("open chrome") == {"intent": "OPEN_APP", "app": "chrome"}


def test_parse_intent_close():
    assert parse_intent("close window") == {"intent": "CLOSE_APP"}


def test_parse_intent_screenshot():
    assert parse_intent("take screenshot now") == {"intent": "SCREENSHOT"}


def test_parse_intent_unknown():
    assert parse_intent("hello world") == {"intent": "UNKNOWN"}


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

    assert result.intent.action == "UNKNOWN"
    assert result.message == "Could not determine intent"


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
