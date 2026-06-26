"""NVIDIA Nemotron Omni adapter."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
from collections import deque
from typing import Any

from openai import AsyncOpenAI

from agent.adapters.pollinations import PollinationsAdapter, _clean_task
from agent.adapters.speech import SpeechManager
from agent.adapters.vision import VisionManager
from agent.adapters.prompts import (
    ROCKET_MISSION_COMPILER_SYSTEM_PROMPT,
    ROCKET_PARSER_SYSTEM_PROMPT,
    mission_compiler_user_prompt,
    parser_user_prompt,
)
from agent.runtime.browser_state import (
    BrowserState,
    compile_browser_mission,
    context_is_compatible_task,
    mission_to_task,
    parse_mission,
    predict_browser_state,
    strip_incompatible_context,
)

TRY_AGAIN_MISSION = {
    "intent": "BROWSER_ACTION",
    "context": "unknown",
    "mission": "try_again",
    "complexity": "LOW",
    "estimated_steps": 1,
    "success_criteria": ["input_unclear"],
    "instructions": ["Ask the user to repeat or redraw the command"],
}


class NemotronAdapter:
    """Primary perception adapter for Rocket Phase 1."""

    def __init__(
        self,
        fallback: PollinationsAdapter | None = None,
        model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        vision: VisionManager | None = None,
        speech: SpeechManager | None = None,
    ) -> None:
        self.model = model
        self.fallback = fallback
        self.client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY", ""),
        )
        self.vision = vision if vision is not None else VisionManager()
        self.speech = speech if speech is not None else SpeechManager()
        self.status: dict[str, str] = {
            "Nemotron": "unchecked",
            "MissionCompiler": "unchecked",
            "Pollinations": "configured" if fallback else "disabled",
            "KimiVision": "configured" if self.vision.available else "disabled",
            "Speech": "configured" if self.speech.available else "disabled",
        }
        self._last_task = ""
        self._active_app = ""
        self._profile_context = ""
        self._runtime_context = ""
        self._history: deque[str] = deque(maxlen=8)
        self._browser_state = BrowserState()

    async def health_check(self) -> None:
        self.status["Nemotron"] = "configured" if os.getenv("NVIDIA_API_KEY") else "missing NVIDIA_API_KEY"
        self.status["KimiVision"] = "configured" if self.vision.available else "disabled"
        self.status["Speech"] = self.speech.status if self.speech.status != "unchecked" else ("configured" if self.speech.available else "disabled")

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
        if self.vision.available:
            try:
                raw_command = await self.vision.parse_command(
                    image_bytes,
                    mime_type=mime_type,
                    system_prompt=ROCKET_PARSER_SYSTEM_PROMPT,
                    user_prompt=parser_user_prompt("image", context=self._context_text()),
                )
                self.status["KimiVision"] = "ok"
                task = await self._compile_with_mission_model(_clean_task(raw_command))
                if task:
                    if _should_remember_task(task):
                        self._remember_task(task)
                    return task
            except Exception as error:
                self.status["KimiVision"] = f"fallback: {error}"

        data_url = _data_url(mime_type, image_bytes)
        content: list[dict[str, Any]] = [
            {"type": "text", "text": parser_user_prompt("image", context=self._context_text())},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
        return await self._complete("image", content)

    async def process_audio(self, audio_bytes: bytes, audio_format: str = "wav") -> str:
        if self.speech.available:
            try:
                transcript = await asyncio.to_thread(
                    self.speech.transcribe, audio_bytes, audio_format=audio_format
                )
                if transcript and transcript.strip():
                    # Compile directly from transcript — skip the slow mission compiler LLM call.
                    # The transcript is already clean speech; compile_browser_mission handles intent.
                    task = self._compile_task(transcript.strip())
                    self.status["Speech"] = "ok"
                    if _should_remember_task(task):
                        self._remember_task(task)
                    return task
            except Exception as error:
                self.status["Speech"] = f"fallback: {error}"
                import sys; print(f"[Speech] all paths failed: {error}", file=sys.stderr)
        encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
        normalized_format = _audio_format(audio_format)
        content: list[dict[str, Any]] = [
            {"type": "text", "text": parser_user_prompt("audio", context=self._context_text())},
            {"type": "input_audio", "input_audio": {"data": encoded_audio, "format": normalized_format}},
        ]
        return await self._complete("audio", content)

    async def process_braille(self, braille_text: str) -> str:
        content = parser_user_prompt("braille", braille_text, context=self._context_text())
        return await self._complete("braille", content)

    async def _complete(self, input_type: str, user_content: Any) -> str:
        try:
            max_tokens = 384 if input_type in {"audio", "image"} else 256
            cautious_input = input_type in {"audio", "image"}
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ROCKET_PARSER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.0 if cautious_input else 0.1,
                top_p=0.9 if cautious_input else 0.95,
                max_tokens=max_tokens,
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": False},
                    "reasoning_budget": 0,
                },
                stream=False,
            )
            content = completion.choices[0].message.content or ""
            normalized_command = _clean_task(content)
            task = await self._compile_with_mission_model(normalized_command)
            if not task:
                raise RuntimeError("Nemotron returned an empty task.")
            self.status["Nemotron"] = "ok"
            if _should_remember_task(task):
                self._remember_task(task)
            return task
        except Exception as error:
            self.status["Nemotron"] = f"error: {error}"
            if self.fallback is None:
                raise
            fallback_text = _fallback_text(input_type, user_content)
            task = self._compile_task(self.fallback.process_text(input_type, fallback_text))
            if _should_remember_task(task):
                self._remember_task(task)
            return task

    async def _compile_with_mission_model(self, normalized_command: str) -> str:
        if _looks_like_parser_garbage(normalized_command):
            return mission_to_task(TRY_AGAIN_MISSION)
        if normalized_command.strip().lower() in {"try_again", "try again"}:
            return mission_to_task(TRY_AGAIN_MISSION)
        try:
            completion = await self.client.chat.completions.create(
                model=os.getenv("ROCKET_MISSION_COMPILER_MODEL", "minimaxai/minimax-m3"),
                messages=[
                    {"role": "system", "content": ROCKET_MISSION_COMPILER_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": mission_compiler_user_prompt(normalized_command, context=self._context_text()),
                    },
                ],
                temperature=0.0,
                top_p=0.9,
                max_tokens=384,
                stream=False,
            )
            compiled = _clean_task(completion.choices[0].message.content or "")
            self.status["MissionCompiler"] = "ok"
            return self._compile_task(compiled)
        except Exception as error:
            self.status["MissionCompiler"] = f"fallback: {error}"
            return self._compile_task(normalized_command)

    def _context_text(self) -> str:
        parts: list[str] = []
        if self._active_app:
            parts.append(f"Active app: {self._active_app}")
        parts.append(f"BrowserState: {json.dumps(self._browser_state.to_dict(), ensure_ascii=True)}")
        if self._last_task:
            parts.append(f"Last task: {self._last_task}")
        if self._history:
            parts.append("Recent tasks: " + " | ".join(self._history))
        if self._profile_context:
            parts.append(f"User profile: {self._profile_context}")
        if self._runtime_context:
            parts.append(f"Runtime setup: {self._runtime_context}")
        return "\n".join(parts)

    def _compile_task(self, raw_output: str) -> str:
        if _looks_like_parser_garbage(raw_output):
            return mission_to_task(TRY_AGAIN_MISSION)
        mission = parse_mission(raw_output)
        if mission is None:
            contextual = self._contextualize_task(raw_output)
            mission = compile_browser_mission(contextual, self._browser_state)
        else:
            normalized_source = _mission_source_text(mission, raw_output)
            fallback = compile_browser_mission(normalized_source, self._browser_state)
            mission = {**mission, **fallback}
        return mission_to_task(mission)

    def _contextualize_task(self, task: str) -> str:
        if not task:
            return task
        normalized = task.strip()
        lower = normalized.lower()
        if self._browser_state.current_site and _looks_like_generic_search(lower):
            query = re.sub(r"^(search|find|look up)\s+", "", normalized, flags=re.IGNORECASE).strip(" .")
            if query:
                return f"Search {query} on {_site_label(self._browser_state.current_site)}."
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
        mission = parse_mission(task)
        mission_text = str(mission.get("mission", "")) if mission else task
        self._browser_state = BrowserState.from_dict(
            mission.get("predicted_browser_state") if mission else predict_browser_state(self._browser_state, task).to_dict()
        )
        app = _extract_active_app(mission_text)
        if not app and self._browser_state.current_site:
            app = _site_label(self._browser_state.current_site)
        if app:
            self._active_app = app


def _data_url(mime_type: str, payload: bytes) -> str:
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _audio_format(value: str) -> str:
    cleaned = value.strip().lower().lstrip(".")
    if cleaned in {"wav", "mp3", "flac", "ogg"}:
        return cleaned
    if cleaned in {"audio/wav", "audio/x-wav"}:
        return "wav"
    if cleaned == "audio/mpeg":
        return "mp3"
    return "wav"


def _fallback_text(input_type: str, user_content: Any) -> str:
    if isinstance(user_content, str):
        return user_content
    if input_type == "audio":
        return (
            "Audio input was received but primary multimodal transcription failed. "
            "Do not guess from silence. If no reliable spoken command is available, return try_again."
        )
    if input_type == "image":
        return (
            "Drawing input was received but primary visual parsing failed. "
            "Do not guess from random marks. If no reliable drawn or handwritten command is visible, return try_again."
        )
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


def _site_label(site: str) -> str:
    labels = {
        "youtube.com": "YouTube",
        "spotify.com": "Spotify",
        "gmail.com": "Gmail",
        "github.com": "GitHub",
        "google.com": "Google",
        "reddit.com": "Reddit",
    }
    return labels.get(site, site)


def _mission_source_text(mission: dict[str, Any], raw_output: str) -> str:
    intent = str(mission.get("intent", "")).upper()
    mission_text = str(mission.get("mission", "")).strip()
    context = str(mission.get("context", "")).strip()
    if context and not context_is_compatible_task(mission_text, context, intent):
        return strip_incompatible_context(mission_text, context)
    if intent == "SEARCH" and mission_text:
        return mission_text
    if mission_text:
        return f"{mission_text} {context}".strip()
    return raw_output


def _should_remember_task(task: str) -> bool:
    mission = parse_mission(task)
    if mission is None:
        return not _looks_like_parser_garbage(task)
    text = " ".join(
        [
            str(mission.get("intent", "")),
            str(mission.get("context", "")),
            str(mission.get("mission", "")),
            " ".join(str(item) for item in mission.get("success_criteria", [])),
        ]
    ).lower()
    return "try_again" not in text and "input_unclear" not in text and not _looks_like_parser_garbage(text)


def _looks_like_parser_garbage(value: str) -> bool:
    lower = value.lower()
    if "opencoding" in lower:
        return True
    tokens = re.findall(r"[A-Za-z0-9.]+", value)
    if len(tokens) >= 12:
        numeric = sum(1 for token in tokens if re.fullmatch(r"\d+(\.\d+)?", token))
        if numeric / len(tokens) > 0.55:
            return True
    repeated_numbers = re.findall(r"(?:^|[,\s])1(?:\.5)?(?=[,\s]|$)", value)
    return len(repeated_numbers) >= 10
