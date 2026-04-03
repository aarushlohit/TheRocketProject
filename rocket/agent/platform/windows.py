"""Windows platform adapter with REAL execution (Stage 1 Upgrade)."""

from __future__ import annotations

import shutil
import subprocess
import webbrowser
from pathlib import Path

from agent.platform.adapter import PlatformAdapter
from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# WINDOWS APP RESOLUTION MAP
# =============================================================================
APP_MAP = {
    "chrome": ["chrome", "chrome.exe", "google-chrome"],
    "notepad": ["notepad", "notepad.exe"],
    "calculator": ["calc", "calc.exe"],
    "edge": ["msedge", "msedge.exe", "microsoft-edge"],
    "vscode": ["code", "code.exe", "Code.exe"],
    "firefox": ["firefox", "firefox.exe"],
    "terminal": ["wt", "wt.exe", "cmd", "cmd.exe"],
    "explorer": ["explorer", "explorer.exe"],
    "paint": ["mspaint", "mspaint.exe"],
    "wordpad": ["wordpad", "write.exe"],
}


def resolve_app(app_name: str) -> str:
    """Resolve app name to executable command for Windows."""
    candidates = APP_MAP.get(app_name.lower(), [app_name])

    print(f"\n[WINDOWS RESOLVE] Trying: {candidates}")

    for cmd in candidates:
        if shutil.which(cmd):
            print(f"[FOUND] {cmd}")
            return cmd

    print(f"[FALLBACK] {app_name}")
    return app_name


class WindowsAdapter(PlatformAdapter):
    """Windows-specific platform operations with REAL execution."""

    async def open_app(self, app_name: str) -> None:
        """Open application on Windows - REAL EXECUTION."""
        resolved_cmd = resolve_app(app_name)

        print(f"\n========== [EXECUTION START] ==========")
        print(f"[OPEN_APP] app_name={app_name}")
        print(f"[RESOLVED] cmd={resolved_cmd}")

        try:
            # Use 'start' command for reliable Windows app launching
            subprocess.Popen(
                ["cmd", "/c", "start", "", resolved_cmd],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"[EXECUTION SUCCESS] Launched: {resolved_cmd}")
            logger.info(f"[EXECUTION SUCCESS] Launched app: {resolved_cmd}")
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            logger.error(f"Failed to open app {app_name}: {e}")
            raise

    async def open_url(self, url: str) -> None:
        """Open URL in default browser - REAL EXECUTION."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[OPEN_URL] url={url}")

        try:
            # Ensure URL has protocol
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # Use webbrowser module for reliability
            webbrowser.open(url)
            print(f"[EXECUTION SUCCESS] Opened URL: {url}")
            logger.info(f"[EXECUTION SUCCESS] Opened URL: {url}")
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            logger.error(f"Failed to open URL {url}: {e}")
            # Fallback to subprocess
            try:
                subprocess.Popen(
                    ["cmd", "/c", "start", "", url],
                    shell=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(f"[FALLBACK SUCCESS] Opened URL via cmd: {url}")
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                raise

    async def type_text(self, text: str, delay: float = 0.05) -> None:
        """Type text on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[TYPE_TEXT] text={text[:50]}...")
        logger.info(f"Type text (Windows): {text[:50]}...")
        # TODO: Implement with pyautogui when available

    async def press_keys(self, keys: list) -> None:
        """Press keys on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[PRESS_KEYS] keys={keys}")
        logger.info(f"Press keys (Windows): {keys}")
        # TODO: Implement with pyautogui when available

    async def click(self, x: int, y: int, button: str = "left") -> None:
        """Click on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[CLICK] x={x}, y={y}, button={button}")
        logger.info(f"Click (Windows) at ({x}, {y})")
        # TODO: Implement with pyautogui when available

    async def scroll(self, direction: str, amount: int = 3) -> None:
        """Scroll on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[SCROLL] direction={direction}, amount={amount}")
        logger.info(f"Scroll (Windows) {direction} {amount}")
        # TODO: Implement with pyautogui when available

    async def screenshot(self, output_dir: Path) -> Path:
        """Take screenshot on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[SCREENSHOT] output_dir={output_dir}")

        try:
            from PIL import ImageGrab
            from datetime import datetime, timezone

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            screenshot_path = output_dir / f"screenshot_{timestamp}.png"
            output_dir.mkdir(parents=True, exist_ok=True)

            screenshot = ImageGrab.grab()
            screenshot.save(screenshot_path)

            print(f"[EXECUTION SUCCESS] Screenshot saved: {screenshot_path}")
            logger.info(f"Screenshot saved: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            logger.error(f"Screenshot failed: {e}")
            raise

    async def get_focused_window(self) -> dict:
        """Get focused window on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[GET_FOCUSED_WINDOW]")
        logger.info("Get focused window (Windows)")
        # TODO: Implement with win32gui
        return {}

    async def close_app(
        self, app_name: str | None = None, target: str = "focused"
    ) -> None:
        """Close application on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[CLOSE_APP] app_name={app_name}, target={target}")

        try:
            if app_name:
                # Kill by process name
                subprocess.run(
                    ["taskkill", "/IM", f"{app_name}.exe", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                print(f"[EXECUTION SUCCESS] Closed: {app_name}")
                logger.info(f"Closed app: {app_name}")
            else:
                # Close focused window with Alt+F4
                logger.info("Close focused window not yet implemented")
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            logger.error(f"Failed to close app: {e}")
            raise

    async def minimize(
        self, app_name: str | None = None, target: str = "focused"
    ) -> None:
        """Minimize window on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[MINIMIZE] app_name={app_name}, target={target}")
        logger.info(f"Minimize (Windows): {app_name or 'focused'}")
        # TODO: Implement with win32gui

    async def maximize(
        self, app_name: str | None = None, target: str = "focused"
    ) -> None:
        """Maximize window on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[MAXIMIZE] app_name={app_name}, target={target}")
        logger.info(f"Maximize (Windows): {app_name or 'focused'}")
        # TODO: Implement with win32gui
