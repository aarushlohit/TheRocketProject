"""
Stage 3 — Smart Delays Module.

Provides adaptive delay management for execution:
- App launch delays
- Typing speed adjustment
- Exponential backoff for retries
- Platform-specific timing
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Optional

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# DELAY TYPES
# =============================================================================

class DelayType(Enum):
    """Types of execution delays."""
    APP_LAUNCH = "app_launch"
    BROWSER_LAUNCH = "browser_launch"
    URL_LOAD = "url_load"
    SEARCH_LOAD = "search_load"
    TYPING = "typing"
    KEY_PRESS = "key_press"
    BETWEEN_STEPS = "between_steps"
    RETRY = "retry"
    VERIFICATION = "verification"


# =============================================================================
# DEFAULT DELAYS (in seconds)
# =============================================================================

DEFAULT_DELAYS = {
    DelayType.APP_LAUNCH: 2.0,          # Wait for app to launch
    DelayType.BROWSER_LAUNCH: 3.0,       # Browsers take longer
    DelayType.URL_LOAD: 2.0,            # Wait for URL to load
    DelayType.SEARCH_LOAD: 1.5,         # Wait for search page
    DelayType.TYPING: 0.05,             # Delay between characters
    DelayType.KEY_PRESS: 0.1,           # Delay between key presses
    DelayType.BETWEEN_STEPS: 0.5,       # Between plan steps
    DelayType.RETRY: 1.0,               # Base retry delay
    DelayType.VERIFICATION: 1.5,        # Wait before verification
}

# Heavy apps that need longer delays
HEAVY_APPS = {
    "vscode", "code", "visual studio code",
    "chrome", "firefox", "edge",
    "word", "excel", "powerpoint",
    "photoshop", "illustrator",
    "android studio", "intellij", "pycharm",
    "teams", "slack", "discord", "zoom",
}

# App-specific launch delays
APP_LAUNCH_DELAYS = {
    "chrome": 3.0,
    "firefox": 3.0,
    "edge": 2.5,
    "vscode": 4.0,
    "code": 4.0,
    "word": 3.5,
    "excel": 3.5,
    "spotify": 3.0,
    "teams": 4.0,
    "slack": 3.5,
    "discord": 3.0,
    "zoom": 3.5,
    "calculator": 1.0,
    "notepad": 1.0,
    "terminal": 1.5,
}


# =============================================================================
# SMART DELAYS CLASS
# =============================================================================

class SmartDelays:
    """
    Manages adaptive delays for execution.
    
    Features:
    - App-specific launch delays
    - Dynamic typing speed
    - Exponential backoff for retries
    - Platform-aware timing
    """
    
    def __init__(self, platform: str = "windows"):
        self.platform = platform
        self.delays = DEFAULT_DELAYS.copy()
        self.app_delays = APP_LAUNCH_DELAYS.copy()
        
        # Adaptive state
        self.retry_multiplier = 1.0
        self.consecutive_failures = 0
        
        # Performance tracking
        self.average_app_launch_time: float = 2.0
        self.app_launch_samples: int = 0
    
    def get_delay(self, delay_type: DelayType, context: Optional[dict] = None) -> float:
        """
        Get appropriate delay for a delay type.
        
        Args:
            delay_type: Type of delay needed
            context: Optional context (app name, retry count, etc.)
            
        Returns:
            Delay in seconds
        """
        context = context or {}
        base_delay = self.delays.get(delay_type, 1.0)
        
        # Apply context-specific adjustments
        if delay_type == DelayType.APP_LAUNCH:
            return self._get_app_launch_delay(context)
        
        elif delay_type == DelayType.RETRY:
            return self._get_retry_delay(context)
        
        elif delay_type == DelayType.TYPING:
            return self._get_typing_delay(context)
        
        return base_delay
    
    def _get_app_launch_delay(self, context: dict) -> float:
        """Get delay for app launch."""
        app = context.get("app", "").lower()
        
        # Check app-specific delay
        if app in self.app_delays:
            delay = self.app_delays[app]
            print(f"[DELAY] App '{app}' → {delay}s (specific)")
            return delay
        
        # Check if heavy app
        if app in HEAVY_APPS:
            delay = 3.5
            print(f"[DELAY] App '{app}' → {delay}s (heavy)")
            return delay
        
        # Use adaptive average
        delay = self.delays[DelayType.APP_LAUNCH]
        print(f"[DELAY] App '{app}' → {delay}s (default)")
        return delay
    
    def _get_retry_delay(self, context: dict) -> float:
        """
        Get delay for retry with exponential backoff.
        
        Formula: base_delay * 2^(retry_count)
        Max: 16 seconds
        """
        retry_count = context.get("retry_count", 0)
        base_delay = self.delays[DelayType.RETRY]
        
        # Exponential backoff
        delay = base_delay * (2 ** retry_count)
        
        # Cap at 16 seconds
        delay = min(delay, 16.0)
        
        print(f"[DELAY] Retry #{retry_count} → {delay}s (exponential backoff)")
        logger.debug(f"[DELAY] Exponential backoff: retry={retry_count}, delay={delay}s")
        
        return delay
    
    def _get_typing_delay(self, context: dict) -> float:
        """
        Get delay for typing.
        
        Slower for:
        - Longer texts
        - After recent failures
        """
        text_length = context.get("text_length", 0)
        slow_mode = context.get("slow_mode", False)
        
        base_delay = self.delays[DelayType.TYPING]
        
        if slow_mode:
            # Double the delay for slow mode
            return base_delay * 2
        
        # Slightly faster for short texts
        if text_length < 20:
            return base_delay * 0.8
        
        return base_delay
    
    def wait(self, delay_type: DelayType, context: Optional[dict] = None):
        """
        Wait for the appropriate delay.
        
        Args:
            delay_type: Type of delay
            context: Optional context
        """
        delay = self.get_delay(delay_type, context)
        
        if delay > 0:
            print(f"[WAIT] {delay_type.value}: {delay:.2f}s")
            time.sleep(delay)
    
    async def async_wait(self, delay_type: DelayType, context: Optional[dict] = None):
        """
        Async wait for the appropriate delay.
        
        Args:
            delay_type: Type of delay
            context: Optional context
        """
        import asyncio
        
        delay = self.get_delay(delay_type, context)
        
        if delay > 0:
            print(f"[ASYNC WAIT] {delay_type.value}: {delay:.2f}s")
            await asyncio.sleep(delay)
    
    def record_success(self, delay_type: DelayType, actual_time: float):
        """
        Record successful operation time for adaptation.
        
        Args:
            delay_type: Type of delay
            actual_time: Actual time the operation took
        """
        if delay_type == DelayType.APP_LAUNCH:
            # Update running average
            self.app_launch_samples += 1
            alpha = 1.0 / self.app_launch_samples
            self.average_app_launch_time = (
                alpha * actual_time + (1 - alpha) * self.average_app_launch_time
            )
        
        # Reset failure tracking
        self.consecutive_failures = 0
        self.retry_multiplier = 1.0
    
    def record_failure(self, delay_type: DelayType):
        """
        Record failed operation for delay adjustment.
        
        Args:
            delay_type: Type of delay
        """
        self.consecutive_failures += 1
        
        # Increase delays after consecutive failures
        if self.consecutive_failures >= 2:
            self.retry_multiplier = min(self.retry_multiplier * 1.5, 4.0)
            print(f"[DELAY] Increased retry multiplier to {self.retry_multiplier}")
    
    def update_app_delay(self, app: str, delay: float):
        """
        Update app-specific delay based on observations.
        
        Args:
            app: App name
            delay: Observed successful delay
        """
        app_lower = app.lower()
        current = self.app_delays.get(app_lower, 2.0)
        
        # Smooth update
        new_delay = (current + delay) / 2
        self.app_delays[app_lower] = new_delay
        
        print(f"[DELAY] Updated '{app}' delay: {current:.1f}s → {new_delay:.1f}s")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_smart_delays_instance: Optional[SmartDelays] = None


def get_smart_delays(platform: str = "windows") -> SmartDelays:
    """Get singleton SmartDelays instance."""
    global _smart_delays_instance
    if _smart_delays_instance is None:
        _smart_delays_instance = SmartDelays(platform)
    return _smart_delays_instance


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def wait_for_app(app: str = ""):
    """Wait for app to launch."""
    get_smart_delays().wait(DelayType.APP_LAUNCH, {"app": app})


def wait_for_browser(browser: str = "chrome"):
    """Wait for browser to launch."""
    get_smart_delays().wait(DelayType.BROWSER_LAUNCH, {"app": browser})


def wait_for_retry(retry_count: int):
    """Wait before retry with exponential backoff."""
    get_smart_delays().wait(DelayType.RETRY, {"retry_count": retry_count})


async def async_wait_for_app(app: str = ""):
    """Async wait for app to launch."""
    await get_smart_delays().async_wait(DelayType.APP_LAUNCH, {"app": app})


async def async_wait_for_retry(retry_count: int):
    """Async wait before retry with exponential backoff."""
    await get_smart_delays().async_wait(DelayType.RETRY, {"retry_count": retry_count})


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "DelayType",
    "SmartDelays",
    "get_smart_delays",
    "wait_for_app",
    "wait_for_browser",
    "wait_for_retry",
    "async_wait_for_app",
    "async_wait_for_retry",
    "DEFAULT_DELAYS",
    "APP_LAUNCH_DELAYS",
]
