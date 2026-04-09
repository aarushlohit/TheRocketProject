"""UI Automation helpers for Windows app and dialog control."""

from __future__ import annotations

import sys
import time
from typing import Any

import psutil


def _require_windows() -> None:
    if sys.platform not in ("win32", "windows"):
        raise RuntimeError("Windows UI automation is only supported on Windows")


def _normalize_process_name(app_name: str) -> str:
    normalized = str(app_name or "").strip().lower()
    if normalized.endswith(".exe"):
        return normalized
    return f"{normalized}.exe"


def _resolve_process_id(app_name: str) -> int | None:
    target = _normalize_process_name(app_name)
    target_base = target.removesuffix(".exe")

    for process in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            name = (process.info.get("name") or "").lower()
            exe = (process.info.get("exe") or "").lower()
            cmdline = " ".join(process.info.get("cmdline") or []).lower()
            if (
                name == target
                or name == target_base
                or target in exe
                or target_base in exe
                or target in cmdline
                or target_base in cmdline
            ):
                return int(process.info["pid"])
        except Exception:
            continue
    return None


def connect_to_app(app_name: str):
    """Connect to a running application using UIA automation."""
    _require_windows()
    print("[UI MODE] Using pywinauto")

    try:
        from pywinauto import Application
    except ImportError as exc:
        print(f"[UI CONNECT ERROR] pywinauto not installed: {exc}")
        return None

    normalized = _normalize_process_name(app_name)
    try:
        return Application(backend="uia").connect(path=normalized)
    except Exception as path_error:
        pid = _resolve_process_id(app_name)
        if pid is not None:
            try:
                return Application(backend="uia").connect(process=pid)
            except Exception as process_error:
                print(f"[UI CONNECT ERROR] path={path_error}; process={process_error}")
                return None

        print(f"[UI CONNECT ERROR] {path_error}")
        return None


def _wait_for_dialog(title_patterns: list[str], timeout: float = 5.0):
    from pywinauto import Desktop

    deadline = time.time() + timeout
    while time.time() < deadline:
        for pattern in title_patterns:
            try:
                dialog = Desktop(backend="uia").window(title_re=pattern, visible_only=True)
                dialog.wait("visible", timeout=0.5)
                return dialog
            except Exception:
                continue
        time.sleep(0.2)
    raise RuntimeError("Save dialog not found")


def _first_existing(*wrappers: Any):
    for wrapper in wrappers:
        try:
            if wrapper.exists():
                return wrapper
        except Exception:
            continue
    return None


def save_file_ui(app_name: str, filename: str | None = None) -> dict:
    app = connect_to_app(app_name)
    if not app:
        raise RuntimeError("App not found")

    try:
        dialog = app.top_window()
        dialog.set_focus()
        dialog.type_keys("^s")

        save_dialog = _wait_for_dialog(
            [
                ".*Save As.*",
                ".*Save.*",
                ".*Save as.*",
            ],
            timeout=5.0,
        )

        normalized_filename = filename.strip() if isinstance(filename, str) else ""
        final_filename = normalized_filename or None

        if final_filename:
            edit = _first_existing(
                save_dialog.child_window(auto_id="1001", control_type="Edit"),
                save_dialog.child_window(control_type="Edit"),
            )
            if edit is None:
                raise RuntimeError("Save dialog filename field not found")
            edit.set_focus()
            edit.set_edit_text(final_filename)

        save_button = _first_existing(
            save_dialog.child_window(title="Save", control_type="Button"),
            save_dialog.child_window(title_re="^&?Save$", control_type="Button"),
        )
        if save_button is None:
            raise RuntimeError("Save button not found")

        save_button.click_input()
        print("[SAVE SUCCESS]")
        return {"status": "success", "filename": final_filename, "app": app_name, "method": "ui"}
    except Exception as exc:
        print(f"[SAVE ERROR] {exc}")
        raise


def maximize_app(app_name: str) -> dict:
    app = connect_to_app(app_name)
    if not app:
        raise RuntimeError("App not found")
    app.top_window().maximize()
    return {"status": "success", "app": app_name, "method": "ui"}


def minimize_app(app_name: str) -> dict:
    app = connect_to_app(app_name)
    if not app:
        raise RuntimeError("App not found")
    app.top_window().minimize()
    return {"status": "success", "app": app_name, "method": "ui"}


def restore_app(app_name: str) -> dict:
    app = connect_to_app(app_name)
    if not app:
        raise RuntimeError("App not found")
    app.top_window().restore()
    return {"status": "success", "app": app_name, "method": "ui"}


def close_app(app_name: str) -> dict:
    app = connect_to_app(app_name)
    if not app:
        raise RuntimeError("App not found")
    app.top_window().close()
    return {"status": "success", "app": app_name, "method": "ui"}
