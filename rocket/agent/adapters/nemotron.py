"""NVIDIA Nemotron Omni adapter."""

from __future__ import annotations

import base64
import os
from typing import Any

from openai import AsyncOpenAI

from agent.adapters.pollinations import PollinationsAdapter, _clean_task
from agent.adapters.prompts import ROCKET_PARSER_SYSTEM_PROMPT, parser_user_prompt


class NemotronAdapter:
    """Primary perception adapter for Rocket Phase 1."""

    def __init__(
        self,
        fallback: PollinationsAdapter | None = None,
        model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    ) -> None:
        self.model = model
        self.fallback = fallback
        self.client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY", ""),
        )
        self.status: dict[str, str] = {
            "Nemotron": "unchecked",
            "Pollinations": "configured" if fallback else "disabled",
        }

    async def health_check(self) -> None:
        self.status["Nemotron"] = "configured" if os.getenv("NVIDIA_API_KEY") else "missing NVIDIA_API_KEY"

    async def process_image(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        data_url = _data_url(mime_type, image_bytes)
        content: list[dict[str, Any]] = [
            {"type": "text", "text": parser_user_prompt("image")},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
        return await self._complete("image", content)

    async def process_audio(self, audio_bytes: bytes) -> str:
        encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
        content: list[dict[str, Any]] = [
            {"type": "text", "text": parser_user_prompt("audio")},
            {"type": "input_audio", "input_audio": {"data": encoded_audio, "format": "wav"}},
        ]
        return await self._complete("audio", content)

    async def process_braille(self, braille_text: str) -> str:
        content = parser_user_prompt("braille", braille_text)
        return await self._complete("braille", content)

    async def _complete(self, input_type: str, user_content: Any) -> str:
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ROCKET_PARSER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                top_p=0.95,
                max_tokens=256,
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": False},
                    "reasoning_budget": 0,
                },
                stream=False,
            )
            content = completion.choices[0].message.content or ""
            task = _clean_task(content)
            if not task:
                raise RuntimeError("Nemotron returned an empty task.")
            self.status["Nemotron"] = "ok"
            return task
        except Exception as error:
            self.status["Nemotron"] = f"error: {error}"
            if self.fallback is None:
                raise
            fallback_text = _fallback_text(input_type, user_content)
            return self.fallback.process_text(input_type, fallback_text)


def _data_url(mime_type: str, payload: bytes) -> str:
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _fallback_text(input_type: str, user_content: Any) -> str:
    if isinstance(user_content, str):
        return user_content
    return f"{input_type} input was received but primary multimodal parsing failed. Generate a concise executable task from the available input context."
