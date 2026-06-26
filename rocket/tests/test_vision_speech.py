from __future__ import annotations

import asyncio
import unittest

from agent.adapters.nemotron import NemotronAdapter
from agent.adapters.speech import SpeechManager
from agent.adapters.vision import VisionManager
from agent.runtime.browser_state import parse_mission


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.message = type("M", (), {"content": content})()


class _FakeCompletions:
    def __init__(self, content: str) -> None:
        self._content = content
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return type("C", (), {"choices": [_FakeMessage(self._content)]})()


class _FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = type("Chat", (), {"completions": _FakeCompletions(content)})()


class _FakeAlt:
    def __init__(self, transcript: str) -> None:
        self.transcript = transcript


class _FakeResult:
    def __init__(self, transcript: str) -> None:
        self.alternatives = [_FakeAlt(transcript)]


class _FakeAsrService:
    def __init__(self, transcript: str) -> None:
        self._transcript = transcript
        self.calls: list = []

    def offline_recognize(self, audio_bytes, config):
        self.calls.append((audio_bytes, config))
        return type("R", (), {"results": [_FakeResult(self._transcript)]})()


def _run(coro):
    return asyncio.run(coro)


class VisionManagerTests(unittest.TestCase):
    def test_available_when_client_injected(self) -> None:
        manager = VisionManager(client=_FakeClient("Open YouTube."), api_key="")
        self.assertTrue(manager.available)

    def test_unavailable_without_key_or_client(self) -> None:
        manager = VisionManager(client=None, api_key="")
        self.assertFalse(manager.available)

    def test_parse_command_returns_text(self) -> None:
        manager = VisionManager(client=_FakeClient("Open YouTube."), api_key="")
        result = _run(
            manager.parse_command(
                b"\x89PNG",
                mime_type="image/png",
                system_prompt="sys",
                user_prompt="user",
            )
        )
        self.assertEqual(result, "Open YouTube.")
        self.assertEqual(manager.status, "ok")

    def test_empty_command_raises(self) -> None:
        manager = VisionManager(client=_FakeClient("   "), api_key="")
        with self.assertRaises(RuntimeError):
            _run(
                manager.parse_command(
                    b"x", mime_type="image/png", system_prompt="s", user_prompt="u"
                )
            )


class SpeechManagerTests(unittest.TestCase):
    def test_available_when_service_injected(self) -> None:
        manager = SpeechManager(asr_service=_FakeAsrService("hi"), api_key="")
        self.assertTrue(manager.available)

    def test_unavailable_without_key_or_service_and_no_sr(self) -> None:
        # With speech_recognition / faster-whisper installed, local fallback makes it available.
        manager = SpeechManager(asr_service=None, api_key="")
        self.assertTrue(manager.available)

    def test_transcribe_returns_first_transcript(self) -> None:
        service = _FakeAsrService("Open Spotify")
        manager = SpeechManager(asr_service=service, api_key="")
        self.assertEqual(manager.transcribe(b"RIFFxxxx"), "Open Spotify")
        self.assertEqual(len(service.calls), 1)

    def test_empty_transcript_raises(self) -> None:
        manager = SpeechManager(asr_service=_FakeAsrService(""), api_key="")
        with self.assertRaises(RuntimeError):
            manager.transcribe(b"RIFFxxxx")


class NemotronPrimaryPathTests(unittest.TestCase):
    def test_kimi_primary_drives_image_mission(self) -> None:
        import os
        from unittest.mock import patch

        vision = VisionManager(client=_FakeClient("Open YouTube."), api_key="")
        speech = SpeechManager(asr_service=None, api_key="")
        adapter = NemotronAdapter(vision=vision, speech=speech)

        # Disable drawing-direct so the Kimi extraction path is exercised.
        with patch.dict(os.environ, {"ROCKET_DRAWING_DIRECT": "0"}):
            task = _run(adapter.process_image(b"\x89PNG", mime_type="image/png"))
        mission = parse_mission(task)

        self.assertIsNotNone(mission)
        self.assertEqual(mission["context"], "youtube.com")

    def test_drawing_direct_mode_returns_image_mission(self) -> None:
        import os
        from unittest.mock import patch

        adapter = NemotronAdapter()
        with patch.dict(os.environ, {"ROCKET_DRAWING_DIRECT": "1"}):
            task = _run(adapter.process_image(b"\x89PNGdata", mime_type="image/png"))
        mission = parse_mission(task)
        self.assertEqual(mission["intent"], "DRAWING")
        self.assertEqual(mission["context"], "image")
        self.assertIn("image_path", mission)
        self.assertTrue(mission["image_path"].endswith(".png"))
        self.assertEqual(adapter.status["KimiVision"], "direct")

    def test_riva_primary_drives_audio_mission(self) -> None:
        vision = VisionManager(client=None, api_key="")
        speech = SpeechManager(asr_service=_FakeAsrService("Open YouTube."), api_key="")
        adapter = NemotronAdapter(vision=vision, speech=speech)

        task = _run(adapter.process_audio(b"RIFFxxxxxxxx", audio_format="wav"))
        mission = parse_mission(task)

        self.assertIsNotNone(mission)
        self.assertEqual(mission["context"], "youtube.com")
        self.assertEqual(adapter.status["Speech"], "ok")

    def test_status_reports_disabled_when_vision_unavailable(self) -> None:
        adapter = NemotronAdapter(
            vision=VisionManager(client=None, api_key=""),
            speech=SpeechManager(asr_service=None, api_key=""),
        )
        self.assertEqual(adapter.status["KimiVision"], "disabled")


if __name__ == "__main__":
    unittest.main()
