"""Windows platform adapter."""

import subprocess

from agent.platform.adapter import PlatformAdapter
from agent.utils.logger import get_logger


logger = get_logger(__name__)


class WindowsAdapter(PlatformAdapter):
    """Windows-specific platform operations."""

    async def open_app(self, app_name: str) -> None:
        """Open application on Windows."""
        try:
            subprocess.Popen(f"start {app_name}", shell=True)
            logger.info(f"Launched app: {app_name}")
        except Exception as e:
            logger.error(f"Failed to open app {app_name}: {e}")
            raise

    async def type_text(self, text: str, delay: float = 0.05) -> None:
        """Type text on Windows (placeholder)."""
        logger.info(f"Type text (Windows): {text[:50]}...")
        # Implementation: use pyautogui or similar

    async def press_keys(self, keys: list) -> None:
        """Press keys on Windows (placeholder)."""
        logger.info(f"Press keys (Windows): {keys}")
        # Implementation: use pyautogui.hotkey()

    async def click(self, x: int, y: int, button: str = "left") -> None:
        """Click on Windows (placeholder)."""
        logger.info(f"Click (Windows) at ({x}, {y})")
        # Implementation: use pyautogui.click()

    async def scroll(self, direction: str, amount: int = 3) -> None:
        """Scroll on Windows (placeholder)."""
        logger.info(f"Scroll (Windows) {direction} {amount}")
        # Implementation: send scroll events

    async def screenshot(self) -> bytes:
        """Take screenshot on Windows (placeholder)."""
        logger.info("Screenshot (Windows)")
        # Implementation: PIL Image.screenshot()
        return b""

    async def get_focused_window(self) -> dict:
        """Get focused window on Windows (placeholder)."""
        logger.info("Get focused window (Windows)")
        # Implementation: win32gui functions
        return {}
