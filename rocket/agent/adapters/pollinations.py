"""Pollinations fallback adapter."""

from __future__ import annotations

import base64
import os
import tempfile

import requests

from agent.adapters.prompts import ROCKET_PARSER_SYSTEM_PROMPT, parser_user_prompt


class PollinationsAdapter:
    def __init__(
        self,
        model: str = "mistral-small-3.2",
        *,
        image_model: str | None = None,
        audio_model: str | None = None,
    ) -> None:
        self.model = model
        self.image_model = image_model or model
        self.audio_model = audio_model or os.getenv("ROCKET_POLLINATIONS_AUDIO_MODEL", "whisper")
        self.endpoint = "https://gen.pollinations.ai/v1/chat/completions"
        self.audio_endpoint = "https://gen.pollinations.ai/v1/audio/transcriptions"

    def process_text(self, input_type: str, text: str) -> str:
        return self._chat_completion(
            model=self.model,
            system_prompt=ROCKET_PARSER_SYSTEM_PROMPT,
            user_prompt=parser_user_prompt(input_type, text),
        )

    def process_image(self, image_bytes: bytes, *, mime_type: str = "image/png", context: str = "") -> str:
        data_url = _data_url(mime_type, image_bytes)
        prompt = parser_user_prompt("image", text="", context=context)
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
        return self._chat_completion(
            model=self.image_model,
            system_prompt=ROCKET_PARSER_SYSTEM_PROMPT,
            user_content=content,
        )

    def transcribe_audio(self, audio_bytes: bytes, *, audio_format: str = "wav") -> str:
        api_key = os.getenv("POLLINATIONS_API_KEY")
        params = {}
        if api_key:
            params["key"] = api_key

        suffix = _audio_suffix(audio_format)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            with open(tmp_path, "rb") as audio_file:
                response = requests.post(
                    self.audio_endpoint,
                    params=params,
                    timeout=120,
                    files={"file": (os.path.basename(tmp_path), audio_file, _audio_mime(audio_format))},
                    data={"model": self.audio_model},
                )
            response.raise_for_status()
            try:
                data = response.json()
            except Exception:
                return _clean_task(response.text)
            if isinstance(data, dict):
                text = data.get("text") or data.get("transcript") or data.get("data") or ""
                if isinstance(text, str) and text.strip():
                    return _clean_task(text)
            return _clean_task(response.text)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _chat_completion(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str | None = None,
        user_content: list[dict[str, object]] | None = None,
    ) -> str:
        params = {}
        api_key = os.getenv("POLLINATIONS_API_KEY")
        if api_key:
            params["key"] = api_key

        payload: dict[str, object] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content if user_content is not None else user_prompt or ""},
            ],
            "temperature": 0.1,
            "max_tokens": 128,
        }
        response = requests.post(
            self.endpoint,
            params=params,
            timeout=120,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return _clean_task(content)


def _clean_task(value: str) -> str:
    task = " ".join(value.strip().split())
    return task.strip("` ")


def _data_url(mime_type: str, payload: bytes) -> str:
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _audio_suffix(audio_format: str) -> str:
    cleaned = audio_format.strip().lower().lstrip(".")
    if cleaned in {"mp3", "mpeg", "audio/mpeg"}:
        return ".mp3"
    if cleaned in {"flac"}:
        return ".flac"
    if cleaned in {"ogg"}:
        return ".ogg"
    return ".wav"


def _audio_mime(audio_format: str) -> str:
    cleaned = audio_format.strip().lower().lstrip(".")
    if cleaned in {"mp3", "mpeg", "audio/mpeg"}:
        return "audio/mpeg"
    if cleaned in {"flac"}:
        return "audio/flac"
    if cleaned in {"ogg"}:
        return "audio/ogg"
    return "audio/wav"
