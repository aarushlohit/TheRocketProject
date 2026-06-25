"""Vision parsing manager.

Primary visual model: Moonshot Kimi K2.6 (served through the NVIDIA
``integrate.api.nvidia.com`` OpenAI-compatible endpoint). The Nemotron Omni
multimodal model remains the fallback and lives in :mod:`agent.adapters.nemotron`.

The manager only turns raw drawing/screenshot bytes into a single short command
string. Mission compilation stays in the Nemotron adapter so the existing
context, browser-state and verification behaviour is unchanged.
"""

from __future__ import annotations

import base64
import os
from typing import Any

from openai import AsyncOpenAI

DEFAULT_KIMI_VISION_MODEL = "moonshotai/kimi-k2.6"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


class VisionManager:
    """Primary image-understanding path backed by Kimi K2.6."""

    def __init__(
        self,
        *,
        model: str | None = None,
        client: AsyncOpenAI | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model = model or os.getenv("ROCKET_VISION_MODEL", DEFAULT_KIMI_VISION_MODEL)
        self._api_key = api_key if api_key is not None else os.getenv("NVIDIA_API_KEY", "")
        self._client = client
        self.status: str = "unchecked"

    @property
    def available(self) -> bool:
        """Whether the primary vision path can be attempted."""

        if os.getenv("ROCKET_DISABLE_KIMI_VISION"):
            return False
        return self._client is not None or bool(self._api_key)

    def _ensure_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(base_url=NVIDIA_BASE_URL, api_key=self._api_key)
        return self._client

    async def parse_command(
        self,
        image_bytes: bytes,
        *,
        mime_type: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Return a single raw command string extracted from the image.

        Raises on any failure so the caller can fall back to Nemotron Omni.
        """

        client = self._ensure_client()
        data_url = _data_url(mime_type or "image/png", image_bytes)
        content: list[dict[str, Any]] = [
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
        completion = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            temperature=0.0,
            top_p=0.9,
            max_tokens=384,
            extra_body={"chat_template_kwargs": {"thinking": False}},
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        if not text:
            raise RuntimeError("Kimi vision returned an empty command.")
        self.status = "ok"
        return text


def _data_url(mime_type: str, payload: bytes) -> str:
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"
