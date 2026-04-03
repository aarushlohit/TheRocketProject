"""
Stage 3 — Self-Correction Engine Module.

Handles execution failures with intelligent recovery:
- App not found → try alternatives
- Search fail → retry with delays
- Type fail → slow down typing
- Max 2 retries per step
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from agent.core.smart_delays import (
    SmartDelays,
    get_smart_delays,
    DelayType,
)
from agent.core.intent_refiner import APP_ALIASES
from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# ERROR TYPES
# =============================================================================

class ErrorType(Enum):
    """Types of execution errors."""
    APP_NOT_FOUND = "app_not_found"
    APP_LAUNCH_FAILED = "app_launch_failed"
    SEARCH_FAILED = "search_failed"
    TYPE_FAILED = "type_failed"
    URL_FAILED = "url_failed"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"


# =============================================================================
# CORRECTION STRATEGY
# =============================================================================

class CorrectionStrategy(Enum):
    """Strategies for self-correction."""
    RETRY_SAME = "retry_same"           # Retry with same parameters
    RETRY_MODIFIED = "retry_modified"   # Retry with modified parameters
    ALTERNATIVE = "alternative"         # Try alternative approach
    SKIP = "skip"                       # Skip this step
    ABORT = "abort"                     # Abort entire plan


# =============================================================================
# CORRECTION RESULT
# =============================================================================

class CorrectionResult:
    """Result of self-correction attempt."""
    
    def __init__(
        self,
        strategy: CorrectionStrategy,
        modified_step: Optional[Dict[str, Any]] = None,
        delay: float = 0.0,
        message: str = "",
        can_retry: bool = True,
    ):
        self.strategy = strategy
        self.modified_step = modified_step
        self.delay = delay
        self.message = message
        self.can_retry = can_retry
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "modified_step": self.modified_step,
            "delay": self.delay,
            "message": self.message,
            "can_retry": self.can_retry,
        }


# =============================================================================
# APP NAME ALTERNATIVES
# =============================================================================

APP_ALTERNATIVES: Dict[str, List[str]] = {
    "chrome": ["google chrome", "chromium", "browser"],
    "firefox": ["mozilla firefox", "mozilla", "browser"],
    "edge": ["microsoft edge", "msedge", "browser"],
    "terminal": ["cmd", "command prompt", "powershell", "wt", "windows terminal"],
    "calculator": ["calc", "gnome-calculator"],
    "notepad": ["notepad++", "gedit", "texteditor"],
    "vscode": ["code", "visual studio code", "vs code"],
    "spotify": ["spotify.exe"],
}


# =============================================================================
# SELF-CORRECTION ENGINE
# =============================================================================

class SelfCorrection:
    """
    Self-correction engine for execution failures.
    
    Features:
    - Intelligent error classification
    - App name alternatives
    - Retry with modifications
    - Progressive delays
    - Max retry limits
    """
    
    MAX_RETRIES = 2
    
    def __init__(self, smart_delays: Optional[SmartDelays] = None):
        self.delays = smart_delays or get_smart_delays()
        self.retry_counts: Dict[int, int] = {}  # step_index -> retry count
    
    def correct(
        self,
        step: Dict[str, Any],
        error: str,
        step_index: int = 0,
    ) -> CorrectionResult:
        """
        Attempt to correct an execution failure.
        
        Args:
            step: The failed step (intent + slots)
            error: Error message from execution
            step_index: Index of step in plan
            
        Returns:
            CorrectionResult with strategy and modifications
        """
        print(f"\n========== [SELF-CORRECTION] ==========")
        print(f"[STEP] {step.get('intent')}: {step.get('slots')}")
        print(f"[ERROR] {error}")
        
        # Check retry limit
        current_retries = self.retry_counts.get(step_index, 0)
        if current_retries >= self.MAX_RETRIES:
            print(f"[CORRECTION] Max retries reached ({self.MAX_RETRIES})")
            return CorrectionResult(
                strategy=CorrectionStrategy.ABORT,
                message=f"Max retries ({self.MAX_RETRIES}) exceeded",
                can_retry=False,
            )
        
        # Classify error
        error_type = self._classify_error(error, step.get("intent", ""))
        print(f"[ERROR TYPE] {error_type.value}")
        
        # Get correction strategy
        result = self._get_correction(step, error_type, current_retries)
        
        # Update retry count
        if result.can_retry:
            self.retry_counts[step_index] = current_retries + 1
            print(f"[RETRY COUNT] {current_retries + 1}/{self.MAX_RETRIES}")
        
        logger.info(f"[SELF-CORRECT] {error_type.value} → {result.strategy.value}")
        
        return result
    
    def _classify_error(self, error: str, intent: str) -> ErrorType:
        """Classify error message into error type."""
        error_lower = error.lower()
        
        # App-related errors
        if any(x in error_lower for x in ["not found", "no such", "doesn't exist", "not installed"]):
            return ErrorType.APP_NOT_FOUND
        
        if any(x in error_lower for x in ["failed to launch", "could not start", "launch failed"]):
            return ErrorType.APP_LAUNCH_FAILED
        
        # Search errors
        if any(x in error_lower for x in ["search failed", "no results", "search error"]):
            return ErrorType.SEARCH_FAILED
        
        # Type errors
        if any(x in error_lower for x in ["type failed", "typing error", "input failed"]):
            return ErrorType.TYPE_FAILED
        
        # URL errors
        if any(x in error_lower for x in ["url failed", "page not found", "connection refused"]):
            return ErrorType.URL_FAILED
        
        # Timeout
        if any(x in error_lower for x in ["timeout", "timed out", "took too long"]):
            return ErrorType.TIMEOUT
        
        # Permission
        if any(x in error_lower for x in ["permission", "access denied", "unauthorized"]):
            return ErrorType.PERMISSION_DENIED
        
        return ErrorType.UNKNOWN
    
    def _get_correction(
        self,
        step: Dict[str, Any],
        error_type: ErrorType,
        retry_count: int,
    ) -> CorrectionResult:
        """Get correction strategy based on error type."""
        intent = step.get("intent", "")
        slots = step.get("slots", {})
        
        # APP_NOT_FOUND - try alternatives
        if error_type == ErrorType.APP_NOT_FOUND:
            return self._correct_app_not_found(step, retry_count)
        
        # APP_LAUNCH_FAILED - retry with delay
        if error_type == ErrorType.APP_LAUNCH_FAILED:
            return self._correct_app_launch_failed(step, retry_count)
        
        # SEARCH_FAILED - retry with browser reopen
        if error_type == ErrorType.SEARCH_FAILED:
            return self._correct_search_failed(step, retry_count)
        
        # TYPE_FAILED - retry slower
        if error_type == ErrorType.TYPE_FAILED:
            return self._correct_type_failed(step, retry_count)
        
        # URL_FAILED - retry with delay
        if error_type == ErrorType.URL_FAILED:
            return self._correct_url_failed(step, retry_count)
        
        # TIMEOUT - increase delay and retry
        if error_type == ErrorType.TIMEOUT:
            delay = self.delays.get_delay(DelayType.RETRY, {"retry_count": retry_count + 1})
            return CorrectionResult(
                strategy=CorrectionStrategy.RETRY_SAME,
                delay=delay,
                message=f"Retrying after {delay}s delay (timeout recovery)",
            )
        
        # PERMISSION_DENIED - abort (can't fix)
        if error_type == ErrorType.PERMISSION_DENIED:
            return CorrectionResult(
                strategy=CorrectionStrategy.ABORT,
                message="Permission denied - cannot proceed",
                can_retry=False,
            )
        
        # UNKNOWN - simple retry with delay
        delay = self.delays.get_delay(DelayType.RETRY, {"retry_count": retry_count})
        return CorrectionResult(
            strategy=CorrectionStrategy.RETRY_SAME,
            delay=delay,
            message=f"Unknown error - retrying with {delay}s delay",
        )
    
    def _correct_app_not_found(
        self,
        step: Dict[str, Any],
        retry_count: int,
    ) -> CorrectionResult:
        """Correct APP_NOT_FOUND error."""
        slots = step.get("slots", {})
        app = slots.get("app", "").lower()
        
        print(f"[CORRECTION] Trying alternatives for '{app}'")
        
        # Strategy 1: Try lowercase
        if retry_count == 0 and app != app.lower():
            modified = step.copy()
            modified["slots"] = slots.copy()
            modified["slots"]["app"] = app.lower()
            
            return CorrectionResult(
                strategy=CorrectionStrategy.RETRY_MODIFIED,
                modified_step=modified,
                message=f"Trying lowercase: {app.lower()}",
            )
        
        # Strategy 2: Try alternatives
        alternatives = self._get_app_alternatives(app)
        if alternatives and retry_count < len(alternatives):
            alt = alternatives[retry_count]
            
            modified = step.copy()
            modified["slots"] = slots.copy()
            modified["slots"]["app"] = alt
            modified["slots"]["_original_app"] = app
            
            return CorrectionResult(
                strategy=CorrectionStrategy.ALTERNATIVE,
                modified_step=modified,
                message=f"Trying alternative: {alt}",
            )
        
        # Strategy 3: Try Windows search
        if retry_count == self.MAX_RETRIES - 1:
            modified = step.copy()
            modified["slots"] = slots.copy()
            modified["slots"]["_use_windows_search"] = True
            
            return CorrectionResult(
                strategy=CorrectionStrategy.RETRY_MODIFIED,
                modified_step=modified,
                delay=0.5,
                message=f"Trying Windows search for '{app}'",
            )
        
        return CorrectionResult(
            strategy=CorrectionStrategy.ABORT,
            message=f"Could not find app: {app}",
            can_retry=False,
        )
    
    def _correct_app_launch_failed(
        self,
        step: Dict[str, Any],
        retry_count: int,
    ) -> CorrectionResult:
        """Correct APP_LAUNCH_FAILED error."""
        delay = self.delays.get_delay(DelayType.RETRY, {"retry_count": retry_count})
        
        return CorrectionResult(
            strategy=CorrectionStrategy.RETRY_SAME,
            delay=delay * 1.5,  # Extra delay for launch
            message=f"Retrying app launch after {delay * 1.5}s",
        )
    
    def _correct_search_failed(
        self,
        step: Dict[str, Any],
        retry_count: int,
    ) -> CorrectionResult:
        """Correct SEARCH_FAILED error."""
        # First retry: just retry with delay
        if retry_count == 0:
            delay = self.delays.get_delay(DelayType.SEARCH_LOAD) * 2
            return CorrectionResult(
                strategy=CorrectionStrategy.RETRY_SAME,
                delay=delay,
                message=f"Retrying search after {delay}s",
            )
        
        # Second retry: flag to reopen browser
        modified = step.copy()
        modified["_reopen_browser"] = True
        
        return CorrectionResult(
            strategy=CorrectionStrategy.RETRY_MODIFIED,
            modified_step=modified,
            delay=1.0,
            message="Reopening browser and retrying search",
        )
    
    def _correct_type_failed(
        self,
        step: Dict[str, Any],
        retry_count: int,
    ) -> CorrectionResult:
        """Correct TYPE_FAILED error."""
        modified = step.copy()
        modified["slots"] = step.get("slots", {}).copy()
        
        # Add slow mode flag
        modified["slots"]["_slow_mode"] = True
        
        # Increase typing delay
        typing_delay = self.delays.get_delay(
            DelayType.TYPING, 
            {"slow_mode": True, "text_length": len(modified["slots"].get("text", ""))}
        )
        
        return CorrectionResult(
            strategy=CorrectionStrategy.RETRY_MODIFIED,
            modified_step=modified,
            delay=0.5,
            message=f"Retrying typing in slow mode (delay: {typing_delay}s)",
        )
    
    def _correct_url_failed(
        self,
        step: Dict[str, Any],
        retry_count: int,
    ) -> CorrectionResult:
        """Correct URL_FAILED error."""
        delay = self.delays.get_delay(DelayType.RETRY, {"retry_count": retry_count})
        
        return CorrectionResult(
            strategy=CorrectionStrategy.RETRY_SAME,
            delay=delay,
            message=f"Retrying URL open after {delay}s",
        )
    
    def _get_app_alternatives(self, app: str) -> List[str]:
        """Get alternative names for an app."""
        app_lower = app.lower()
        
        # Direct alternatives
        if app_lower in APP_ALTERNATIVES:
            return APP_ALTERNATIVES[app_lower]
        
        # Check reverse aliases
        alternatives = []
        for alias, canonical in APP_ALIASES.items():
            if canonical == app_lower and alias != app_lower:
                alternatives.append(alias)
        
        return alternatives
    
    def reset_retry_counts(self):
        """Reset all retry counts (for new plan)."""
        self.retry_counts.clear()
    
    def get_retry_count(self, step_index: int) -> int:
        """Get current retry count for a step."""
        return self.retry_counts.get(step_index, 0)


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_self_correction_instance: Optional[SelfCorrection] = None


def get_self_correction() -> SelfCorrection:
    """Get singleton SelfCorrection instance."""
    global _self_correction_instance
    if _self_correction_instance is None:
        _self_correction_instance = SelfCorrection()
    return _self_correction_instance


def self_correct(
    step: Dict[str, Any],
    error: str,
    step_index: int = 0,
) -> CorrectionResult:
    """
    Convenience function to attempt self-correction.
    
    Args:
        step: The failed step
        error: Error message
        step_index: Index of step in plan
        
    Returns:
        CorrectionResult
    """
    return get_self_correction().correct(step, error, step_index)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ErrorType",
    "CorrectionStrategy",
    "CorrectionResult",
    "SelfCorrection",
    "get_self_correction",
    "self_correct",
    "APP_ALTERNATIVES",
]
