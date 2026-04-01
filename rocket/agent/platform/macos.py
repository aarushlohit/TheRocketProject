"""macOS platform adapter."""

import subprocess

from agent.platform.adapter import PlatformAdapter
from agent.utils.logger import get_logger


logger = get_logger(__name__)


class MacOSAdapter(PlatformAdapter):
    """macOS-specific platform operations."""

    async def open_app(self, app_name: str) -> None:
        """Open application on macOS."""
        try:
            subprocess.Popen(["open", "-a", app_name])
            logger.info(f"Launched app: {app_name}")
        except Exception as e:
            logger.error(f"Failed to open app {app_name}: {e}")
            raise

    async def type_text(self, text: str, delay: float = 0.05) -> None:
        """Type text on macOS (placeholder)."""
        logger.info(f"Type text (macOS): {text[:50]}...")
        # Implementation: use PyObjC or pyautogui

    async def press_keys(self, keys: list) -> None:
        """Press keys on macOS (placeholder)."""
        logger.info(f"Press keys (macOS): {keys}")
        # Implementation: use PyObjC

    async def click(self, x: int, y: int, button: str = "left") -> None:
        """Click on macOS (placeholder)."""
        logger.info(f"Click (macOS) at ({x}, {y})")
        # Implementation: use Quartz

    async def scroll(self, direction: str, amount: int = 3) -> None:
        """Scroll on macOS (placeholder)."""
        logger.info(f"Scroll (macOS) {direction} {amount}")
        # Implementation: PyObjC scroll events

    async def screenshot(self) -> bytes:
        """Take screenshot on macOS (placeholder)."""
        logger.info("Screenshot (macOS)")
        # Implementation: PIL or screencapture
        return b""

    async def get_focused_window(self) -> dict:
        """Get focused window on macOS (placeholder)."""
        logger.info("Get focused window (macOS)")
        # Implementation: PyObjC window methods
        return {}
