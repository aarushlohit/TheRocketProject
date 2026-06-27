from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from agent.adapters.pollinations import PollinationsAdapter


class _FakeResponse:
    def __init__(self, payload: dict[str, object] | None = None, text: str = "") -> None:
        self._payload = payload or {}
        self.text = text
        self.status_checked = False

    def raise_for_status(self) -> None:
        self.status_checked = True

    def json(self) -> dict[str, object]:
        return self._payload


class PollinationsAdapterTests(unittest.TestCase):
    def test_process_text_uses_mistral_model_and_returns_clean_content(self) -> None:
        response = _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "Open WhatsApp",
                        }
                    }
                ]
            }
        )

        with patch("agent.adapters.pollinations.requests.post", return_value=response) as mock_post:
            adapter = PollinationsAdapter(model="mistral-small-3.2")
            result = adapter.process_text("voice", "open whatsapp")

        self.assertEqual(result, "Open WhatsApp")
        self.assertTrue(response.status_checked)
        self.assertEqual(mock_post.call_args.kwargs["json"]["model"], "mistral-small-3.2")
        message = mock_post.call_args.kwargs["json"]["messages"][1]["content"]
        self.assertIn("Input type: voice", message)
        self.assertIn("Input: open whatsapp", message)

    def test_process_image_sends_multimodal_message(self) -> None:
        response = _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "Open YouTube and search cats",
                        }
                    }
                ]
            }
        )

        with patch("agent.adapters.pollinations.requests.post", return_value=response) as mock_post:
            adapter = PollinationsAdapter(model="mistral-small-3.2")
            result = adapter.process_image(b"\x89PNG\r\n\x1a\n", mime_type="image/png", context="drawing")

        self.assertEqual(result, "Open YouTube and search cats")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "mistral-small-3.2")
        image_message = payload["messages"][1]["content"]
        self.assertEqual(image_message[0]["type"], "text")
        self.assertEqual(image_message[1]["type"], "image_url")
        self.assertTrue(image_message[1]["image_url"]["url"].startswith("data:image/png;base64,"))

    def test_transcribe_audio_posts_multipart_payload(self) -> None:
        response = _FakeResponse({"text": "Open Calculator"})

        with patch("agent.adapters.pollinations.requests.post", return_value=response) as mock_post:
            adapter = PollinationsAdapter(model="mistral-small-3.2", audio_model="whisper")
            result = adapter.transcribe_audio(b"RIFF1234", audio_format="wav")

        self.assertEqual(result, "Open Calculator")
        self.assertTrue(response.status_checked)
        self.assertEqual(mock_post.call_args.kwargs["data"]["model"], "whisper")
        self.assertIn("file", mock_post.call_args.kwargs["files"])

    @unittest.skipUnless(os.getenv("POLLINATIONS_API_KEY"), "Pollinations API key not configured")
    def test_live_smoke_request(self) -> None:
        adapter = PollinationsAdapter(model="mistral-small-3.2")
        result = adapter.process_text("voice", "say hello")
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
