"""Guarded pyautogui wrappers for deterministic desktop input."""

from __future__ import annotations

import time


def _get_pyautogui():
    import pyautogui

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    return pyautogui


def safe_hotkey(*keys: str) -> None:
    pyautogui = _get_pyautogui()
    time.sleep(0.3)
    try:
        pyautogui.hotkey(*keys)
    except Exception:
        time.sleep(0.5)
        pyautogui.hotkey(*keys)


def safe_write(text: str) -> None:
    pyautogui = _get_pyautogui()
    time.sleep(0.3)
    try:
        pyautogui.write(text, interval=0.03)
    except Exception:
        time.sleep(0.5)
        pyautogui.write(text, interval=0.03)


def safe_press(key: str) -> None:
    pyautogui = _get_pyautogui()
    time.sleep(0.3)
    try:
        pyautogui.press(key)
    except Exception:
        time.sleep(0.5)
        pyautogui.press(key)
