"""Linux platform adapter."""

from __future__ import annotations

import subprocess
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
import shutil

from agent.platform.adapter import PlatformAdapter
from agent.utils import dependency_check
from agent.utils.logger import get_logger


logger = get_logger(__name__)


class LinuxAdapter(PlatformAdapter):
    """Linux-specific platform operations."""

    APP_ALIASES = {
        "chrome": [
            "google-chrome",
            "google-chrome-stable",
            "chromium-browser",
            "chromium",
        ],
        "browser": [
            "google-chrome",
            "google-chrome-stable",
            "chromium-browser",
            "chromium",
            "firefox",
        ],
        "firefox": ["firefox"],
        "code": ["code", "codium"],
        "vscode": ["code", "codium"],
        "settings": ["gnome-control-center", "systemsettings", "kcmshell6"],
    }

    async def open_app(self, app_name: str) -> None:
        """Open application on Linux."""
        command = self._resolve_app_command(app_name)
        if command is None:
            raise RuntimeError(f"Could not find an executable for '{app_name}'")

        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"Launched app: {command[0]}")

    async def type_text(self, text: str, delay: float = 0.05) -> None:
        """Type text on Linux (placeholder)."""
        logger.info(f"Type text (Linux): {text[:50]}...")
        # Implementation: use xdotool or pyautogui

    async def press_keys(self, keys: list) -> None:
        """Press keys on Linux (placeholder)."""
        logger.info(f"Press keys (Linux): {keys}")
        # Implementation: use xdotool

    async def click(self, x: int, y: int, button: str = "left") -> None:
        """Click on Linux (placeholder)."""
        logger.info(f"Click (Linux) at ({x}, {y})")
        # Implementation: use xdotool or similar

    async def scroll(self, direction: str, amount: int = 3) -> None:
        """Scroll on Linux (placeholder)."""
        logger.info(f"Scroll (Linux) {direction} {amount}")
        # Implementation: xdotool key Page_Up/Page_Down

    async def screenshot(self, output_dir: Path) -> Path:
        """Take screenshot on Linux and save it to disk."""
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"screenshot_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}.png"

        if dependency_check.HAS_SCROT:
            subprocess.run(["scrot", str(output_path)], check=True)
            return output_path

        try:
            from PIL import ImageGrab
        except ImportError as exc:  # pragma: no cover - depends on local setup
            raise RuntimeError("Install scrot or Pillow to enable screenshots") from exc

        image = ImageGrab.grab()
        image.save(output_path)
        return output_path

    async def get_focused_window(self) -> dict:
        """Get focused window on Linux (placeholder)."""
        logger.info("Get focused window (Linux)")
        # Implementation: xdotool getactivewindow
        return {}

    async def close_app(
        self, app_name: str | None = None, target: str = "focused"
    ) -> None:
        """Close a named app or the focused window."""
        if app_name:
            self._run_pkill(app_name)
            return

        if dependency_check.HAS_WMCTRL:
            self._run_wmctrl(["wmctrl", "-c", ":ACTIVE:"])
            return

        logger.warning("wmctrl unavailable -> close fallback requires an explicit app name")
        raise RuntimeError("wmctrl unavailable and no app name provided for close fallback")

    async def minimize(
        self, app_name: str | None = None, target: str = "focused"
    ) -> None:
        """Minimize the active window or a named window."""
        if not dependency_check.HAS_WMCTRL:
            if app_name:
                logger.warning(f"wmctrl unavailable -> using pkill STOP fallback for {app_name}")
                self._run_pkill(app_name, signal_name="STOP")
                return
            logger.warning("wmctrl unavailable -> minimize fallback requires an explicit app name")
            raise RuntimeError("wmctrl unavailable and no app name provided for minimize fallback")

        window_target = app_name or ":ACTIVE:"
        self._run_wmctrl(["wmctrl", "-r", window_target, "-b", "add,hidden"])

    async def maximize(
        self, app_name: str | None = None, target: str = "focused"
    ) -> None:
        """Maximize the active window or a named window."""
        if not dependency_check.HAS_WMCTRL:
            if app_name:
                logger.warning(f"wmctrl unavailable -> using pkill CONT fallback for {app_name}")
                self._run_pkill(app_name, signal_name="CONT")
                return
            logger.warning("wmctrl unavailable -> maximize fallback requires an explicit app name")
            raise RuntimeError("wmctrl unavailable and no app name provided for maximize fallback")

        window_target = app_name or ":ACTIVE:"
        self._run_wmctrl(
            ["wmctrl", "-r", window_target, "-b", "add,maximized_vert,maximized_horz"]
        )

    async def open_url(self, url: str) -> None:
        """Open a URL in the default browser."""
        if dependency_check.HAS_XDG_OPEN:
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return

        logger.warning("xdg-open unavailable -> using Python webbrowser fallback")
        if not webbrowser.open(url):
            raise RuntimeError("No URL opener available")

    def _resolve_app_command(self, app_name: str) -> list[str] | None:
        normalized = app_name.lower().strip()
        candidates = self.APP_ALIASES.get(normalized, [normalized])

        for candidate in candidates:
            executable = shutil.which(candidate)
            if executable:
                return [executable]

        return None

    def _resolve_process_names(self, app_name: str) -> list[str]:
        normalized = app_name.lower().strip()
        return self.APP_ALIASES.get(normalized, [normalized])

    def _run_wmctrl(self, command: list[str]) -> None:
        if not dependency_check.HAS_WMCTRL:
            raise RuntimeError("wmctrl is required for window management commands")

        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _run_pkill(self, app_name: str, signal_name: str = "TERM") -> None:
        for candidate in self._resolve_process_names(app_name):
            completed = subprocess.run(
                ["pkill", f"-{signal_name}", "-f", candidate],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if completed.returncode == 0:
                return

        raise RuntimeError(f"No running process matched '{app_name}'")
