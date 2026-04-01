"""Linux platform adapter."""

import subprocess

from agent.platform.adapter import PlatformAdapter
from agent.utils.logger import get_logger


logger = get_logger(__name__)


class LinuxAdapter(PlatformAdapter):
    """Linux-specific platform operations."""

    async def open_app(self, app_name: str) -> None:
        """Open application on Linux."""
        try:
            subprocess.Popen([app_name])
            logger.info(f"Launched app: {app_name}")
        except Exception as e:
            logger.error(f"Failed to open app {app_name}: {e}")
            raise

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

    async def screenshot(self) -> bytes:
        """Take screenshot on Linux (placeholder)."""
        logger.info("Screenshot (Linux)")
        # Implementation: PIL or scrot
        return b""

    async def get_focused_window(self) -> dict:
        """Get focused window on Linux (placeholder)."""
        logger.info("Get focused window (Linux)")
        # Implementation: xdotool getactivewindow
        return {}
