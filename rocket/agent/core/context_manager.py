"""Lightweight runtime context manager for Stage 0 intent execution."""

from __future__ import annotations

from typing import Any


PRONOUN_TOKENS = {"it", "that", "this"}


class ContextManager:
    def __init__(self):
        self.state = {
            "current_app": None,
            "last_app": None,
            "last_intent": None,
            "last_text": None,
            "last_target": None,
        }

    def update(self, intent: str, slots: dict[str, Any]) -> None:
        slots = slots or {}
        app = self._clean_app(slots.get("app"))
        text = slots.get("text")
        target = slots.get("target") or slots.get("window") or app

        if app:
            self.state["last_app"] = app
            if intent == "CLOSE_APP":
                if self.state["current_app"] == app:
                    self.state["current_app"] = None
            else:
                self.state["current_app"] = app
            self.state["last_target"] = app
        elif isinstance(target, str) and target.strip():
            self.state["last_target"] = target.strip()

        if isinstance(text, str) and text:
            self.state["last_text"] = text

        self.state["last_intent"] = intent

    def resolve_app(self, slots: dict[str, Any]) -> str | None:
        slots = slots or {}
        explicit_app = self._clean_app(slots.get("app"))
        if explicit_app:
            return explicit_app

        if self.state["last_app"]:
            return self.state["last_app"]

        if self.state["current_app"]:
            return self.state["current_app"]

        return None

    def debug(self) -> None:
        print(f"[CONTEXT STATE] last_app={self.state['last_app']}")
        print(f"[CONTEXT] {self.state}")

    def reset(self) -> None:
        for key in self.state:
            self.state[key] = None

    def _clean_app(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        cleaned = value.strip()
        if not cleaned:
            return None

        if cleaned.lower() in PRONOUN_TOKENS:
            return None

        return cleaned

    @property
    def last_app(self) -> str | None:
        return self.state["last_app"]


_context_manager = ContextManager()
context = _context_manager


def get_context_manager() -> ContextManager:
    return _context_manager


def reset_context_manager() -> None:
    _context_manager.reset()
