"""Guarded Windows save-file controls."""

from __future__ import annotations

import sys
import time

from agent.platform.input_safe import safe_hotkey, safe_press, safe_write
from agent.platform.windows_ui import save_file_ui


def _require_windows() -> None:
    if sys.platform not in ("win32", "windows"):
        raise RuntimeError("SAVE_FILE is only supported on Windows")


def focus_app(app_name: str) -> bool:
    """Focus a visible application window by partial title match."""
    _require_windows()

    target = str(app_name or "").strip()
    if not target:
        print("[FOCUS] fail")
        return False

    try:
        import pygetwindow as gw
    except ImportError:
        print("[FOCUS] fail")
        return False

    try:
        windows = gw.getWindowsWithTitle(target)
        for window in windows:
            try:
                window.activate()
                time.sleep(0.5)
                print("[FOCUS] success")
                return True
            except Exception:
                continue
        print("[FOCUS] fail")
        return False
    except Exception:
        print("[FOCUS] fail")
        return False


def _save_file_keyboard_fallback(app_name: str, filename: str | None = None) -> dict:
    normalized_app = str(app_name or "").strip()
    if not normalized_app:
        raise RuntimeError("No target app resolved")

    normalized_filename = filename.strip() if isinstance(filename, str) else ""
    final_filename = normalized_filename or None

    print(f"[SAVE_FILE] filename={final_filename}")
    print(f"[SAVE_FILE] app={normalized_app}")
    print("[SAVE_FILE] falling back to keyboard control")

    if not focus_app(normalized_app):
        raise RuntimeError("Failed to focus target app")

    try:
        safe_hotkey("ctrl", "s")
    except Exception:
        print("[WARNING] Try running as administrator")
        raise

    print("[SAVE_FILE] Ctrl+S sent")
    time.sleep(1.2)

    if final_filename:
        safe_write(final_filename)
        print("[SAVE_FILE] filename typed")
        safe_press("enter")
        print("[SAVE_FILE] fallback confirm sent")

    print("[SAVE_FILE] completed")
    return {"status": "success", "filename": final_filename, "app": normalized_app, "method": "keyboard_fallback"}


def save_file_via_os(app_name: str, filename: str | None = None) -> dict:
    _require_windows()

    try:
        return save_file_ui(app_name, filename)
    except Exception as exc:
        print(f"[SAVE_FILE] UI automation failed: {exc}")

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return _save_file_keyboard_fallback(app_name, filename)
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1.0)
                continue
            raise

    raise RuntimeError(str(last_error) if last_error else "SAVE_FILE failed")
