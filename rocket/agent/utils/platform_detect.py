"""Runtime display-environment detection helpers."""

from __future__ import annotations

import os


def detect_environment() -> str:
    """Detect the current Linux display environment."""
    if "HYPRLAND_INSTANCE_SIGNATURE" in os.environ:
        return "hyprland"
    if "WAYLAND_DISPLAY" in os.environ:
        return "wayland"
    if "DISPLAY" in os.environ:
        return "x11"
    return "unknown"
