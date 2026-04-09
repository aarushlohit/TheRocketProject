from __future__ import annotations

import win32con
import win32gui
import win32process
import psutil


def get_hwnds_for_process(process_name: str) -> list[int]:
    hwnds: list[int] = []
    target = process_name.lower().strip()

    def callback(hwnd: int, _) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            process = psutil.Process(pid)
            if target in process.name().lower():
                hwnds.append(hwnd)
        except Exception:
            pass
        return True

    win32gui.EnumWindows(callback, None)
    return hwnds


def _resolve_hwnds(process_name: str | None = None) -> list[int]:
    if process_name:
        return get_hwnds_for_process(process_name)

    hwnd = win32gui.GetForegroundWindow()
    return [hwnd] if hwnd else []


def maximize_window(process_name: str | None = None) -> int:
    hwnds = _resolve_hwnds(process_name)
    for hwnd in hwnds:
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    return len(hwnds)


def maximize_all_windows() -> int:
    count = 0

    def callback(hwnd: int, _) -> bool:
        nonlocal count
        if not win32gui.IsWindowVisible(hwnd):
            return True

        title = win32gui.GetWindowText(hwnd)
        if not title or not title.strip():
            return True

        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            count += 1
        except Exception:
            pass

        return True

    win32gui.EnumWindows(callback, None)
    return count


def minimize_window(process_name: str | None = None) -> int:
    hwnds = _resolve_hwnds(process_name)
    for hwnd in hwnds:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    return len(hwnds)


def restore_window(process_name: str | None = None) -> int:
    hwnds = _resolve_hwnds(process_name)
    for hwnd in hwnds:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    return len(hwnds)
