"""Quality gate for generated Rocket tasks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent.runtime.browser_state import parse_mission


@dataclass(frozen=True)
class TaskQuality:
    accepted: bool
    message: str = ""


_BAD_PHRASES = (
    "unknown",
    "unclear",
    "try_again",
    "try again",
    "input_unclear",
    "inaudible",
    "illegible",
    "unreadable",
    "ambiguous",
    "random scribble",
    "scribble",
    "blank drawing",
    "no readable",
    "no reliable drawn",
    "draw or write",
    "no reliable spoken command",
    "repeat the command",
    "ask the user to repeat",
    "not sure",
    "can't tell",
    "cannot tell",
    "could not understand",
    "i do not know",
    "i don't know",
    "maybe open something",
    "no task",
    "empty",
)

_ACTION_WORDS = (
    "open",
    "launch",
    "start",
    "search",
    "find",
    "go",
    "navigate",
    "visit",
    "play",
    "click",
    "type",
    "write",
    "read",
    "create",
    "save",
    "install",
    "close",
    "maximize",
    "minimize",
    "send",
    "call",
    "message",
    "calc",
    "calculate",
    "calculator",
)


def assess_task_quality(task: str) -> TaskQuality:
    """Reject vague parser output before it can trigger desktop automation."""

    compact = " ".join(task.strip().split())
    mission = parse_mission(compact)
    if mission is not None:
        intent = str(mission.get("intent", "")).strip().lower()
        context = str(mission.get("context", "")).strip().lower()
        mission_text = str(mission.get("mission", "")).strip()
        combined = " ".join(
            [
                intent,
                context,
                mission_text,
                " ".join(str(item) for item in mission.get("success_criteria", [])),
            ]
        ).lower()
        if any(phrase in combined for phrase in _BAD_PHRASES):
            return _try_again("I could not understand the command clearly. Please try again.")
        if _looks_like_parser_garbage(mission_text):
            return _try_again("I could not understand the drawing clearly. Please try again.")
        if mission_text:
            return TaskQuality(True)
        return _try_again("I could not understand. Please try again.")
    lower = compact.lower()
    if not compact:
        return _try_again("I could not understand. Please try again.")
    if len(compact) < 4:
        return _try_again("That command was too short. Please try again.")
    if any(phrase in lower for phrase in _BAD_PHRASES):
        return _try_again("I could not understand the command clearly. Please try again.")
    if _looks_like_noise(compact):
        return _try_again("That input did not look like a command. Please try again.")
    if _looks_like_parser_garbage(compact):
        return _try_again("I could not understand the command clearly. Please try again.")
    if _is_bare_action(lower):
        return _try_again("Please say what you want me to act on.")
    if not any(re.search(rf"\b{re.escape(word)}\b", lower) for word in _ACTION_WORDS):
        return _try_again("Please give me a clear action to perform.")
    return TaskQuality(True)


def _try_again(message: str) -> TaskQuality:
    return TaskQuality(False, message)


def _looks_like_noise(value: str) -> bool:
    letters = re.findall(r"[A-Za-z]", value)
    if not letters:
        return True
    words = re.findall(r"[A-Za-z0-9]+", value)
    if len(words) == 1 and len(words[0]) <= 2:
        return True
    unique_chars = set(value.lower().replace(" ", ""))
    return len(unique_chars) <= 2 and len(value) > 3


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


def _is_bare_action(value: str) -> bool:
    words = re.findall(r"[a-z0-9]+", value)
    return len(words) == 1 and words[0] in _ACTION_WORDS
