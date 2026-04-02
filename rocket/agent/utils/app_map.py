"""Cross-platform app normalization for Stage 1 execution safety."""

from __future__ import annotations

import sys


CANONICAL_APP_MAP = {
    "calculator": "calculator",
    "calc": "calculator",
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "spotify": "spotify",
    "terminal": "terminal",
    "cmd": "terminal",
    "command prompt": "terminal",
    "powershell": "terminal",
    "wt": "terminal",
    "vscode": "vscode",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "code": "vscode",
}

APP_MAP = {
    "calculator": "gnome-calculator",
    "chrome": "google-chrome-stable",
    "google chrome": "google-chrome-stable",
    "spotify": "spotify-launcher",
    "firefox": "firefox",
    "terminal": "x-terminal-emulator",
    "vscode": "code",
}

WINDOWS_APP_MAP = {
    "calculator": "calc",
    "chrome": "chrome",
    "google chrome": "chrome",
    "spotify": "spotify",
    "firefox": "firefox",
    "terminal": "wt",
    "vscode": "code",
}

MACOS_APP_MAP = {
    "calculator": "Calculator",
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "spotify": "Spotify",
    "firefox": "Firefox",
    "terminal": "Terminal",
    "vscode": "Visual Studio Code",
}


def normalize_app_name(name: str, platform_type: str = "auto") -> str:
    """Normalize a user-facing app name to a platform-appropriate executable name."""
    normalized = canonicalize_app_name(name)
    mapping = _mapping_for_platform(platform_type)
    return mapping.get(normalized, normalized)


def normalize_app(name: str, platform_type: str = "auto") -> str:
    """Compatibility wrapper for the Stage 1 requested function name."""
    return normalize_app_name(name, platform_type=platform_type)


def canonicalize_app_name(name: str) -> str:
    """Map user-facing app aliases to a canonical app identifier."""
    normalized = name.strip().lower()
    return CANONICAL_APP_MAP.get(normalized, normalized)


def _mapping_for_platform(platform_type: str) -> dict[str, str]:
    if platform_type == "auto":
        platform_type = sys.platform

    if platform_type in {"win32", "windows"}:
        return WINDOWS_APP_MAP
    if platform_type in {"darwin", "macos"}:
        return MACOS_APP_MAP
    return APP_MAP
