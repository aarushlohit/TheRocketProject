"""Rocket Windows desktop automation MCP server.

This server exposes semantic Windows actions to OpenCode. It favors UIA names,
control labels, and application aliases over pixel coordinates.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

try:
    from pywinauto import Desktop
    from pywinauto.keyboard import send_keys
except Exception:  # pragma: no cover - reported through tool results.
    Desktop = None  # type: ignore[assignment]
    send_keys = None  # type: ignore[assignment]


APP_ALIASES = {
    "chrome": ["chrome.exe", "Google Chrome"],
    "google chrome": ["chrome.exe", "Google Chrome"],
    "edge": ["msedge.exe", "Microsoft Edge"],
    "microsoft edge": ["msedge.exe", "Microsoft Edge"],
    "youtube": ["https://www.youtube.com"],
    "whatsapp": ["whatsapp:"],
    "settings": ["ms-settings:"],
    "windows settings": ["ms-settings:"],
    "vscode": ["code.cmd", "code.exe"],
    "visual studio code": ["code.cmd", "code.exe"],
    "explorer": ["explorer.exe"],
    "file explorer": ["explorer.exe"],
    "notepad": ["notepad.exe"],
    "spotify": ["spotify:"],
}


def main() -> None:
    for line in sys.stdin:
        line = line.lstrip("\ufeff")
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = _handle(request)
        except Exception as error:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(error)}}
        sys.stdout.write(json.dumps(response, ensure_ascii=True) + "\n")
        sys.stdout.flush()


def _handle(request: dict[str, Any]) -> dict[str, Any]:
    method = request.get("method")
    request_id = request.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "rocket-windows", "version": "0.1.0"},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": _tools()}}
    if method == "tools/call":
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        return _tool_call(request_id, params)
    return {"jsonrpc": "2.0", "id": request_id, "result": {}}


def _tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "rocket_open_app",
            "description": "Open an installed Windows app or trusted app URI by semantic name.",
            "inputSchema": {
                "type": "object",
                "properties": {"app": {"type": "string"}},
                "required": ["app"],
            },
        },
        {
            "name": "rocket_list_windows",
            "description": "List visible desktop windows with UIA names.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "rocket_click_by_name",
            "description": "Click a UIA control by visible/accessibility name inside a named window.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "window": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["window", "name"],
            },
        },
        {
            "name": "rocket_type_text",
            "description": "Type text into the focused semantic control or active window.",
            "inputSchema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
        {
            "name": "rocket_press_keys",
            "description": "Send a pywinauto key chord such as ENTER, TAB, or ^l.",
            "inputSchema": {
                "type": "object",
                "properties": {"keys": {"type": "string"}},
                "required": ["keys"],
            },
        },
    ]


def _tool_call(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
    if name == "rocket_open_app":
        text = _open_app(str(arguments.get("app", "")))
    elif name == "rocket_list_windows":
        text = _list_windows()
    elif name == "rocket_click_by_name":
        text = _click_by_name(str(arguments.get("window", "")), str(arguments.get("name", "")))
    elif name == "rocket_type_text":
        text = _type_text(str(arguments.get("text", "")))
    elif name == "rocket_press_keys":
        text = _press_keys(str(arguments.get("keys", "")))
    else:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Unknown tool"}}

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {"content": [{"type": "text", "text": text}]},
    }


def _open_app(app: str) -> str:
    app_key = app.strip().lower()
    start_app = _open_start_app(app)
    if start_app:
        return start_app
    candidates = APP_ALIASES.get(app_key, [app.strip()])
    errors: list[str] = []
    for candidate in candidates:
        try:
            if candidate.endswith(":") or candidate.startswith(("http://", "https://")):
                os.startfile(candidate)  # type: ignore[attr-defined]
            else:
                subprocess.Popen([candidate], shell=False)
            return f"opened {app}"
        except Exception as error:
            errors.append(f"{candidate}: {error}")
    return f"failed to open {app}: {'; '.join(errors)}"


def _open_start_app(app: str) -> str:
    app = app.strip()
    if not app:
        return ""
    escaped = app.replace("'", "''")
    script = (
        f"$name = '{escaped}'; "
        "$app = Get-StartApps | Where-Object { $_.Name -like \"*$name*\" } | Select-Object -First 1; "
        "if ($null -eq $app) { exit 2 }; "
        "Start-Process (\"shell:AppsFolder\\\" + $app.AppID); "
        "Write-Output (\"opened \" + $app.Name)"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return ""
    if completed.returncode == 0:
        return completed.stdout.strip() or f"opened {app}"
    return ""


def _list_windows() -> str:
    if Desktop is None:
        return _list_windows_powershell()
    windows = []
    for window in Desktop(backend="uia").windows():
        title = window.window_text().strip()
        if title:
            windows.append(title)
    return json.dumps(windows[:50], ensure_ascii=True)


def _list_windows_powershell() -> str:
    script = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "Get-Process | "
        "Where-Object { $_.MainWindowTitle } | "
        "Select-Object -ExpandProperty MainWindowTitle -First 50 | "
        "ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception as error:
        return f"failed to list windows: {error}"
    if completed.returncode != 0:
        return completed.stderr.strip() or "failed to list windows"
    return completed.stdout.strip() or "[]"


def _click_by_name(window: str, name: str) -> str:
    if Desktop is None:
        return "pywinauto unavailable"
    target = Desktop(backend="uia").window(title_re=f".*{_escape_re(window)}.*")
    control = target.child_window(title_re=f".*{_escape_re(name)}.*")
    control.wait("visible", timeout=10)
    control.click_input()
    return f"clicked {name}"


def _type_text(text: str) -> str:
    if send_keys is None:
        return "pywinauto unavailable"
    send_keys(text, with_spaces=True, pause=0.01)
    return "typed text"


def _press_keys(keys: str) -> str:
    if send_keys is None:
        return "pywinauto unavailable"
    send_keys(keys)
    return f"pressed {keys}"


def _escape_re(value: str) -> str:
    return "".join(f"\\{char}" if char in r"\.^$*+?{}[]|()" else char for char in value)


if __name__ == "__main__":
    main()
