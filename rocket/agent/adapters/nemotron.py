"""NVIDIA Nemotron Omni adapter."""

from __future__ import annotations

import base64
import json
import os
import re
from collections import deque
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
        self._last_task = ""
        self._active_app = ""
        self._profile_context = ""
        self._runtime_context = ""
        self._history: deque[str] = deque(maxlen=8)

    async def health_check(self) -> None:
        self.status["Nemotron"] = "configured" if os.getenv("NVIDIA_API_KEY") else "missing NVIDIA_API_KEY"

    def set_profile_context(self, profile: dict[str, Any] | None, system_prompt: str = "") -> None:
        if not profile:
            return
        compact = {
            key: value
            for key, value in profile.items()
            if value not in ("", None, [], {})
            and key
            in {
                "name",
                "preferred_name",
                "country",
                "browser",
                "editor",
                "speech_speed",
                "accessibility_mode",
                "trust_level",
                "disabilities",
            }
        }
        self._profile_context = json.dumps(
            {
                "profile": compact,
                "system_prompt": system_prompt.strip(),
            },
            ensure_ascii=True,
        )

    def set_runtime_context(self, setup: dict[str, Any] | None) -> None:
        if not setup:
            return
        compact = {
            key: value
            for key, value in setup.items()
            if key
            in {
                "setup_complete",
                "access_mode",
                "workspace_path",
                "opencode_config_dir",
                "powers_source_dir",
                "credential_mode",
                "credential_refs",
                "backup_enabled",
            }
        }
        self._runtime_context = json.dumps(compact, ensure_ascii=True)

    async def process_image(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        data_url = _data_url(mime_type, image_bytes)
        content: list[dict[str, Any]] = [
            {"type": "text", "text": parser_user_prompt("image", context=self._context_text())},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
        return await self._complete("image", content)

    async def process_audio(self, audio_bytes: bytes) -> str:
        encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
        content: list[dict[str, Any]] = [
            {"type": "text", "text": parser_user_prompt("audio", context=self._context_text())},
            {"type": "input_audio", "input_audio": {"data": encoded_audio, "format": "wav"}},
        ]
        return await self._complete("audio", content)

    async def process_braille(self, braille_text: str) -> str:
        content = parser_user_prompt("braille", braille_text, context=self._context_text())
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
            task = self._contextualize_task(_clean_task(content))
            if not task:
                raise RuntimeError("Nemotron returned an empty task.")
            self.status["Nemotron"] = "ok"
            self._remember_task(task)
            return task
        except Exception as error:
            self.status["Nemotron"] = f"error: {error}"
            if self.fallback is None:
                raise
            fallback_text = _fallback_text(input_type, user_content)
            task = self._contextualize_task(self.fallback.process_text(input_type, fallback_text))
            self._remember_task(task)
            return task

    def _context_text(self) -> str:
        parts: list[str] = []
        if self._active_app:
            parts.append(f"Active app: {self._active_app}")
        if self._last_task:
            parts.append(f"Last task: {self._last_task}")
        if self._history:
            parts.append("Recent tasks: " + " | ".join(self._history))
        if self._profile_context:
            parts.append(f"User profile: {self._profile_context}")
        if self._runtime_context:
            parts.append(f"Runtime setup: {self._runtime_context}")
        return "\n".join(parts)

    def _contextualize_task(self, task: str) -> str:
        if not task:
            return task
        normalized = task.strip()
        lower = normalized.lower()
        if self._active_app and _looks_like_generic_search(lower) and self._active_app.lower() not in lower:
            query = re.sub(r"^(search|find|look up)\s+", "", normalized, flags=re.IGNORECASE).strip(" .")
            if query:
                return f"Search {query} on {self._active_app}."
        if self._active_app in {"Chrome", "Microsoft Edge"}:
            site = _navigation_site(lower)
            if site:
                return f"Navigate existing {self._active_app} tab to {site}."
        return normalized

    def _remember_task(self, task: str) -> None:
        self._last_task = task
        self._history.append(task)
        app = _extract_active_app(task)
        if app:
            self._active_app = app


def _data_url(mime_type: str, payload: bytes) -> str:
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _fallback_text(input_type: str, user_content: Any) -> str:
    if isinstance(user_content, str):
        return user_content
    return f"{input_type} input was received but primary multimodal parsing failed. Generate a concise executable task from the available input context."


def _looks_like_generic_search(task: str) -> bool:
    if not re.match(r"^(search|find|look up)\b", task):
        return False
    scoped_words = (" youtube", " google", " browser", " chrome", " edge", " web", " spotify", " whatsapp")
    return not any(word in task for word in scoped_words)


def _extract_active_app(task: str) -> str:
    lower = task.lower()
    app_patterns = (
        ("youtube", "YouTube"),
        ("whatsapp", "WhatsApp"),
        ("spotify", "Spotify"),
        ("chrome", "Chrome"),
        ("edge", "Microsoft Edge"),
        ("settings", "Windows Settings"),
        ("vscode", "VSCode"),
        ("visual studio code", "VSCode"),
        ("explorer", "File Explorer"),
        ("notepad", "Notepad"),
    )
    for needle, app in app_patterns:
        if needle in lower and re.search(r"\b(open|launch|start|search|play|use|go|navigate)\b", lower):
            return app
    return ""


def _navigation_site(task: str) -> str:
    patterns = (
        (r"\b(go to|open|navigate to|visit)\s+(youtube|you tube)\b", "https://www.youtube.com"),
        (r"\b(go to|open|navigate to|visit)\s+(google)\b", "https://www.google.com"),
        (r"\b(go to|open|navigate to|visit)\s+(github)\b", "https://github.com"),
        (r"\b(go to|open|navigate to|visit)\s+(gmail)\b", "https://mail.google.com"),
        (r"\b(go to|open|navigate to|visit)\s+(whatsapp web)\b", "https://web.whatsapp.com"),
    )
    for pattern, url in patterns:
        if re.search(pattern, task):
            return url
    return ""
