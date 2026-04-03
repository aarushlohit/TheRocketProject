"""Linux platform adapter."""

from __future__ import annotations

import json
import subprocess
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
import shutil

from agent.platform.adapter import PlatformAdapter
from agent.utils import dependency_check
from agent.utils.logger import get_logger
from agent.utils.platform_detect import detect_environment


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

    def __init__(self):
        self.env = detect_environment()
        logger.info("[ENV DETECTED]")
        logger.info(self.env)

    async def open_app(self, app_name: str) -> None:
        """Open application on Linux."""
        try:
            self._spawn_command([app_name])
            return
        except Exception as primary_error:
            logger.warning(f"Direct launch failed for {app_name}: {primary_error}")

        self._spawn_command(["gtk-launch", app_name])

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
        output_path = output_dir / f"screenshot_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.png"

        if self.env in {"hyprland", "wayland"} and dependency_check.HAS_GRIM:
            self._run_command(["grim", str(output_path)])
            return output_path

        if dependency_check.HAS_SCROT:
            self._run_command(["scrot", str(output_path)])
            return output_path

        try:
            from PIL import ImageGrab
        except ImportError as exc:  # pragma: no cover - depends on local setup
            raise RuntimeError("Install grim, scrot, or Pillow to enable screenshots") from exc

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
        if self.env == "hyprland":
            closed = self._close_hyprland_window(app_name)
            if closed:
                return
            logger.warning("hyprctl close failed -> falling back to pkill")
            if app_name:
                self._run_pkill(app_name)
                return
            raise RuntimeError("Hyprland close failed and no app name was provided for pkill fallback")

        if self.env == "x11" and dependency_check.HAS_WMCTRL:
            self._run_wmctrl(["wmctrl", "-c", app_name or ":ACTIVE:"])
            return

        if app_name:
            self._run_pkill(app_name)
            return

        logger.warning("close fallback requires an explicit app name")
        raise RuntimeError("Unable to close focused window in this environment")

    async def minimize(
        self, app_name: str | None = None, target: str = "focused"
    ) -> None:
        """Minimize the active window or a named window."""
        if self.env == "hyprland":
            raise RuntimeError("not supported on hyprland")

        if self.env != "x11" or not dependency_check.HAS_WMCTRL:
            if app_name:
                logger.warning(f"wmctrl unavailable -> using pkill STOP fallback for {app_name}")
                self._run_pkill(app_name, signal_name="STOP")
                return
            logger.warning("wmctrl unavailable -> minimize fallback requires an explicit app name")
            raise RuntimeError("Unable to minimize focused window in this environment")

        window_target = app_name or ":ACTIVE:"
        self._run_wmctrl(["wmctrl", "-r", window_target, "-b", "add,hidden"])

    async def maximize(
        self, app_name: str | None = None, target: str = "focused"
    ) -> None:
        """Maximize the active window or a named window."""
        if self.env == "hyprland":
            self._run_hyprctl(["hyprctl", "dispatch", "fullscreen", "1"])
            return

        if self.env != "x11" or not dependency_check.HAS_WMCTRL:
            if app_name:
                logger.warning(f"wmctrl unavailable -> using pkill CONT fallback for {app_name}")
                self._run_pkill(app_name, signal_name="CONT")
                return
            logger.warning("wmctrl unavailable -> maximize fallback requires an explicit app name")
            raise RuntimeError("Unable to maximize focused window in this environment")

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

        self._run_command(command)

    def _run_hyprctl(self, command: list[str]) -> None:
        if not dependency_check.HAS_HYPRCTL:
            raise RuntimeError("hyprctl is required for Hyprland window management")

        self._run_command(command)

    def _run_pkill(self, app_name: str, signal_name: str = "TERM") -> None:
        for candidate in self._resolve_process_names(app_name):
            completed = self._run_command(
                ["pkill", f"-{signal_name}", "-f", candidate],
                check=False,
            )
            if completed.returncode == 0:
                return

        raise RuntimeError(f"No running process matched '{app_name}'")

    def _close_hyprland_window(self, app_name: str | None) -> bool:
        if not dependency_check.HAS_HYPRCTL:
            return False

        result = self._run_command(["hyprctl", "-j", "clients"])
        clients = json.loads(result.stdout or "[]")

        address = None
        for client in clients:
            if not isinstance(client, dict):
                continue

            if app_name is None:
                address = client.get("address")
                if address:
                    break
                continue

            class_name = str(client.get("class", "")).lower()
            initial_class = str(client.get("initialClass", "")).lower()
            app_name_lower = app_name.lower()
            if app_name_lower in class_name or app_name_lower in initial_class:
                address = client.get("address")
                if address:
                    break

        if not address:
            return False

        self._run_hyprctl(
            ["hyprctl", "dispatch", "closewindow", f"address:{address}"]
        )
        return True

    def _spawn_command(self, command: list[str]) -> None:
        logger.info("[ENV]")
        logger.info(self.env)
        logger.info("[COMMAND]")
        logger.info(" ".join(command))
        try:
            subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("[RESULT]")
            logger.info("success")
        except Exception:
            logger.info("[RESULT]")
            logger.info("error")
            raise

    def _run_command(
        self,
        command: list[str],
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        logger.info("[ENV]")
        logger.info(self.env)
        logger.info("[COMMAND]")
        logger.info(" ".join(command))
        try:
            result = subprocess.run(
                command,
                check=check,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.info("[RESULT]")
            logger.info("success")
            return result
        except Exception:
            logger.info("[RESULT]")
            logger.info("error")
            raise
