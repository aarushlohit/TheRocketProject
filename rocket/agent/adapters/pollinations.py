"""Pollinations fallback adapter."""

from __future__ import annotations

import os

import requests

from agent.adapters.prompts import ROCKET_PARSER_SYSTEM_PROMPT, parser_user_prompt


class PollinationsAdapter:
    def __init__(self, model: str = "mistral-small-3.2") -> None:
        self.model = model
        self.endpoint = "https://gen.pollinations.ai/v1/chat/completions"

    def process_text(self, input_type: str, text: str) -> str:
        params = {}
        api_key = os.getenv("POLLINATIONS_API_KEY")
        if api_key:
            params["key"] = api_key

        response = requests.post(
            self.endpoint,
            params=params,
            timeout=60,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": ROCKET_PARSER_SYSTEM_PROMPT},
                    {"role": "user", "content": parser_user_prompt(input_type, text)},
                ],
                "temperature": 0.1,
                "max_tokens": 128,
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return _clean_task(content)


def _clean_task(value: str) -> str:
    task = " ".join(value.strip().split())
    return task.strip("` ")
