"""Platform adapter - abstracts OS-specific operations."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from pathlib import Path

from agent.utils.logger import get_logger


logger = get_logger(__name__)


class PlatformAdapter(ABC):
    """Abstract interface for OS-specific operations."""

    @abstractmethod
    async def open_app(self, app_name: str) -> None:
        """Open application.
        
        Args:
            app_name: Name of application to open
        """
        pass

    @abstractmethod
    async def type_text(self, text: str, delay: float = 0.05) -> None:
        """Type text into focused window.
        
        Args:
            text: Text to type
            delay: Delay between characters (seconds)
        """
        pass

    @abstractmethod
    async def press_keys(self, keys: list) -> None:
        """Press keyboard keys.
        
        Args:
            keys: List of key names
        """
        pass

    @abstractmethod
    async def click(self, x: int, y: int, button: str = "left") -> None:
        """Click at coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button (left, right, middle)
        """
        pass

    @abstractmethod
    async def scroll(self, direction: str, amount: int = 3) -> None:
        """Scroll in direction.
        
        Args:
            direction: Direction (up, down, left, right)
            amount: Number of lines to scroll
        """
        pass

    @abstractmethod
    async def get_focused_window(self) -> dict:
        """Get currently focused window.
        
        Returns:
            Window info dict
        """
        pass

    @abstractmethod
    async def close_app(
        self, app_name: str | None = None, target: str = "focused"
    ) -> None:
        """Close an application or the focused window."""
        pass

    @abstractmethod
    async def minimize(
        self, app_name: str | None = None, target: str = "focused"
    ) -> None:
        """Minimize an application window."""
        pass

    @abstractmethod
    async def maximize(
        self, app_name: str | None = None, target: str = "focused"
    ) -> None:
        """Maximize an application window."""
        pass

    async def restore(
        self, app_name: str | None = None, target: str = "focused"
    ) -> dict:
        """Restore an application window when supported."""
        return {"status": "error", "reason": "restore_not_supported"}

    @abstractmethod
    async def open_url(self, url: str) -> None:
        """Open a URL in the system browser."""
        pass

    @abstractmethod
    async def screenshot(self, output_dir: Path) -> Path:
        """Capture a screenshot and return the saved path."""
        pass

    async def search_web(self, query: str) -> dict:
        """Search the web using default browser.
        
        Default implementation opens Google search URL.
        Subclasses can override for platform-specific behavior.
        """
        import webbrowser
        search_url = f"https://www.google.com/search?q={query}"
        webbrowser.open(search_url)
        return {"status": "success", "query": query}


def get_platform_adapter(platform_type: str = "auto") -> PlatformAdapter:
    """Get platform-specific adapter.
    
    Args:
        platform_type: "auto", "windows", "macos", or "linux"
        
    Returns:
        PlatformAdapter instance
    """
    if platform_type == "auto":
        platform_type = sys.platform

    if platform_type in ("win32", "windows"):
        from agent.platform.windows import WindowsAdapter
        logger.info("Using Windows platform adapter")
        return WindowsAdapter()
    elif platform_type in ("darwin", "macos"):
        from agent.platform.macos import MacOSAdapter
        logger.info("Using macOS platform adapter")
        return MacOSAdapter()
    elif platform_type in ("linux", "linux2"):
        from agent.platform.linux import LinuxAdapter
        logger.info("Using Linux platform adapter")
        return LinuxAdapter()
    else:
        raise ValueError(f"Unsupported platform: {platform_type}")
