"""Blind-first phone speech sanitiser.

The phone must only ever speak natural language. It must never read JSON,
key=value diagnostics, stack traces, file paths, model ids, ANSI codes, or raw
OpenCode output. This module converts any runtime message into safe speech and
provides natural phase phrases.
"""

from __future__ import annotations

import re

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_DIAG_KEYS = re.compile(
    r"\b(returncode|model|agent|dir|session_id|sessionID|stderr|attached_server|"
    r"verifier|verifier_passed|opencode_reported_success|recovery_attempts|"
    r"recovery_count|recovery_reason|recovery_success|desktop_verification|server_error)\s*=",
    re.IGNORECASE,
)
_TECHNICAL_MARKERS = (
    "traceback",
    "opencode exited",
    "providermodelnotfound",
    "stream error",
    "stack trace",
    'error.error=',
    "opencode/",
)
_PATH = re.compile(r"[A-Za-z]:\\[^\s]+|/[^\s]+/[^\s]+")


def _strip_ansi(text: str) -> str:
    return _ANSI.sub("", text)


def _looks_technical(text: str) -> bool:
    lowered = text.lower()
    if "{" in text and "}" in text:
        return True
    if '":' in text:
        return True
    if _DIAG_KEYS.search(text):
        return True
    if _PATH.search(text):
        return True
    return any(marker in lowered for marker in _TECHNICAL_MARKERS)


def _fallback(success: bool | None, phase: str) -> str:
    phase = (phase or "").strip().lower()
    if phase == "starting":
        return "Starting now."
    if phase == "working":
        return "Working on it."
    if success is True:
        return "Task completed."
    if success is False:
        return "I could not complete that."
    return "Working on it."


def to_phone_speech(message: str | None, *, success: bool | None = None, phase: str = "") -> str:
    """Return safe, natural speech for the phone. Never JSON or internals."""

    text = _strip_ansi(message or "").strip()
    # Trim any diagnostic key=value tail (e.g. "Bluetooth is on. returncode=0 ...").
    cut = _DIAG_KEYS.search(text)
    if cut:
        text = text[: cut.start()].rstrip(" .;,") + ("." if text[: cut.start()].strip() else "")
        text = text.strip()
    if not text or _looks_technical(text):
        return _fallback(success, phase)
    text = " ".join(text.split())
    if len(text) > 240:
        text = text[:237].rstrip() + "..."
    return text or _fallback(success, phase)
