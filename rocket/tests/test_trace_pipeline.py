import asyncio
from pathlib import Path

from agent.stage0.pipeline import DrawToActionPipeline
from agent.utils.config import TRACE_MODE, load_config


def test_trace_mode_defaults_to_enabled(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
agent:
  trace_mode: false
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert TRACE_MODE is True
    assert config.trace_mode is False


def test_debug_curl_masks_api_key(tmp_path):
    pipeline = DrawToActionPipeline(
        api_key="super-secret-key",
        storage_dir=Path(tmp_path),
        trace_mode=True,
    )

    curl_command = pipeline._build_debug_curl(
        "gemini-fast",
        "https://example.com/image.png",
        "prompt text",
    )
    masked_text = pipeline._mask_sensitive("token=super-secret-key")

    assert "super-secret-key" not in curl_command
    assert "key=****" in curl_command
    assert masked_text == "token=****"

    asyncio.run(pipeline.close())
