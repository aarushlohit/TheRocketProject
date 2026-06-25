"""Browser runtime ownership for Rocket.

Rocket owns the real Chrome window. OpenCode/Playwright execute inside it, but
Rocket is responsible for there being exactly one browser, that it reuses the
default profile (cookies/sessions), and that it is never hidden, minimized, or
behind another window when a browser task runs.

As with the verifier, OS control is isolated in an injectable
:class:`BrowserController` so the ownership logic is fully testable and fails
safe. A real :class:`WindowsBrowserController` drives pywinauto when available.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class BrowserRuntimeState:
    """Live ownership state for the single Rocket-controlled browser."""

    browser_pid: Optional[int] = None
    window_handle: Optional[int] = None
    playwright_connected: bool = False
    is_foreground: bool = False
    is_maximized: bool = False
    last_focus_time: float = 0.0
    last_known_bounds: Optional[tuple[int, int, int, int]] = None
    profile_path: str = ""
    browser_channel: str = "chrome"

    @property
    def is_running(self) -> bool:
        return self.browser_pid is not None and self.window_handle is not None


@dataclass(frozen=True)
class BrowserWindow:
    """A snapshot of an observed browser window."""

    pid: int
    handle: int
    title: str = ""
    is_minimized: bool = False
    is_foreground: bool = False
    is_maximized: bool = False
    bounds: Optional[tuple[int, int, int, int]] = None


class BrowserController:
    """OS-facing browser control. Override for tests.

    Every method returns observed facts or ``None``/``False`` when an action
    could not be confirmed. Unknown is never treated as success.
    """

    channel = "chrome"

    def find_window(self) -> BrowserWindow | None:
        return None

    def launch(self, profile_path: str) -> BrowserWindow | None:
        return None

    def query(self, handle: int) -> BrowserWindow | None:
        return None

    def set_foreground(self, handle: int) -> bool:
        return False

    def maximize(self, handle: int) -> bool:
        return False

    def restore(self, handle: int) -> bool:
        return False

    def close(self, pid: int) -> bool:
        return False


class BrowserRuntime:
    """Owns the single Rocket browser and enforces window policy."""

    def __init__(
        self,
        controller: BrowserController | None = None,
        *,
        profile_path: str = "",
        channel: str = "chrome",
        clock=time.time,
    ) -> None:
        self.controller = controller or WindowsBrowserController(channel=channel)
        self.state = BrowserRuntimeState(profile_path=profile_path, browser_channel=channel)
        self._clock = clock

    # -- discovery / launch -------------------------------------------------

    def reuse_browser(self) -> bool:
        """Adopt an already-running browser. Never launches a new one."""

        window = self.controller.find_window()
        if window is None:
            return False
        self._adopt(window)
        return True

    def ensure_browser(self) -> bool:
        """Guarantee exactly one browser. Reuse if present, else launch once."""

        if self.reuse_browser():
            return True
        window = self.controller.launch(self.state.profile_path)
        if window is None:
            return False
        self._adopt(window)
        return True

    # -- window policy ------------------------------------------------------

    def ensure_not_minimized(self) -> bool:
        if not self._ensure_handle():
            return False
        window = self.controller.query(self.state.window_handle)  # type: ignore[arg-type]
        if window is None:
            return False
        if window.is_minimized:
            if not self.controller.restore(self.state.window_handle):  # type: ignore[arg-type]
                return False
            window = self.controller.query(self.state.window_handle) or window  # type: ignore[arg-type]
            if window.is_minimized:
                return False
        self._sync(window)
        return True

    def restore_browser(self) -> bool:
        return self.ensure_not_minimized()

    def ensure_foreground(self) -> bool:
        if not self.ensure_not_minimized():
            return False
        if not self.controller.set_foreground(self.state.window_handle):  # type: ignore[arg-type]
            return False
        window = self.controller.query(self.state.window_handle)  # type: ignore[arg-type]
        if window is None or not window.is_foreground:
            return False
        self._sync(window)
        self.state.last_focus_time = self._clock()
        return True

    def focus_browser(self) -> bool:
        return self.ensure_foreground()

    def ensure_maximized(self) -> bool:
        if not self.ensure_not_minimized():
            return False
        if not self.controller.maximize(self.state.window_handle):  # type: ignore[arg-type]
            return False
        window = self.controller.query(self.state.window_handle)  # type: ignore[arg-type]
        if window is None or not window.is_maximized:
            return False
        self._sync(window)
        return True

    def ensure_visible_focused(self) -> bool:
        """Reuse/launch, un-minimize, foreground, and maximize in one call."""

        if not self.ensure_browser():
            return False
        return self.ensure_foreground() and self.ensure_maximized()

    # -- playwright ownership ----------------------------------------------

    def connect_playwright(self) -> bool:
        """Mark the single Playwright connection. Idempotent (no duplicates)."""

        if self.state.playwright_connected:
            return True
        if not self.state.is_running:
            return False
        self.state.playwright_connected = True
        return True

    def cleanup_browser(self) -> bool:
        """Close the owned browser and reset ownership state."""

        pid = self.state.browser_pid
        closed = self.controller.close(pid) if pid is not None else True
        self.state = BrowserRuntimeState(
            profile_path=self.state.profile_path,
            browser_channel=self.state.browser_channel,
        )
        return closed

    # -- internals ----------------------------------------------------------

    def _ensure_handle(self) -> bool:
        if self.state.window_handle is not None:
            return True
        return self.ensure_browser()

    def _adopt(self, window: BrowserWindow) -> None:
        self.state.browser_pid = window.pid
        self.state.window_handle = window.handle
        self._sync(window)

    def _sync(self, window: BrowserWindow) -> None:
        self.state.is_foreground = window.is_foreground
        self.state.is_maximized = window.is_maximized
        if window.bounds is not None:
            self.state.last_known_bounds = window.bounds


# Module-level singleton so the whole process shares one owned browser.
_RUNTIME: BrowserRuntime | None = None


def get_browser_runtime(
    controller: BrowserController | None = None,
    *,
    profile_path: str = "",
    channel: str = "chrome",
) -> BrowserRuntime:
    """Return the shared browser runtime, creating it once."""

    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = BrowserRuntime(controller, profile_path=profile_path, channel=channel)
    return _RUNTIME


def reset_browser_runtime() -> None:
    """Drop the singleton (used by tests)."""

    global _RUNTIME
    _RUNTIME = None


class WindowsBrowserController(BrowserController):
    """Best-effort Windows browser control via pywinauto. Unknown -> safe."""

    _CHROME_TITLE = "chrome"

    def __init__(self, channel: str = "chrome") -> None:
        self.channel = channel

    def _desktop(self):
        try:
            from pywinauto import Desktop
        except Exception:
            return None
        try:
            return Desktop(backend="uia")
        except Exception:
            return None

    def _snapshot(self, window) -> BrowserWindow | None:
        try:
            handle = int(window.handle)
            pid = int(window.process_id())
            title = window.window_text() or ""
            is_min = bool(window.is_minimized())
            is_max = bool(window.is_maximized())
            try:
                is_fg = bool(window.has_focus())
            except Exception:
                is_fg = False
            rect = window.rectangle()
            bounds = (rect.left, rect.top, rect.right, rect.bottom)
        except Exception:
            return None
        return BrowserWindow(
            pid=pid,
            handle=handle,
            title=title,
            is_minimized=is_min,
            is_foreground=is_fg,
            is_maximized=is_max,
            bounds=bounds,
        )

    def _window_by_handle(self, handle: int):
        desktop = self._desktop()
        if desktop is None:
            return None
        try:
            for window in desktop.windows():
                if int(getattr(window, "handle", 0)) == handle:
                    return window
        except Exception:
            return None
        return None

    def find_window(self) -> BrowserWindow | None:
        desktop = self._desktop()
        if desktop is None:
            return None
        try:
            candidates = desktop.windows(title_re=f".*{self._CHROME_TITLE}.*")
        except Exception:
            return None
        for window in candidates:
            snapshot = self._snapshot(window)
            if snapshot and "chrome" in snapshot.title.lower():
                return snapshot
        return None

    def launch(self, profile_path: str) -> BrowserWindow | None:
        command = ["cmd", "/c", "start", "", "chrome"]
        if profile_path:
            command.extend([f"--user-data-dir={profile_path}"])
        try:
            subprocess.Popen(command, shell=False)
        except Exception:
            return None
        deadline = time.time() + 12
        while time.time() < deadline:
            window = self.find_window()
            if window is not None:
                return window
            time.sleep(0.4)
        return None

    def query(self, handle: int) -> BrowserWindow | None:
        window = self._window_by_handle(handle)
        if window is None:
            return None
        return self._snapshot(window)

    def set_foreground(self, handle: int) -> bool:
        window = self._window_by_handle(handle)
        if window is None:
            return False
        try:
            window.set_focus()
            return True
        except Exception:
            return False

    def maximize(self, handle: int) -> bool:
        window = self._window_by_handle(handle)
        if window is None:
            return False
        try:
            window.maximize()
            return True
        except Exception:
            return False

    def restore(self, handle: int) -> bool:
        window = self._window_by_handle(handle)
        if window is None:
            return False
        try:
            window.restore()
            return True
        except Exception:
            return False

    def close(self, pid: int) -> bool:
        try:
            completed = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception:
            return False
        return completed.returncode == 0
