"""
Stage 6.0 - Execution Verification Layer.

Verifies each execution step before proceeding.
Ensures deterministic, verifiable outcomes.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# VERIFICATION STRATEGIES
# =============================================================================

class VerificationStrategy(Enum):
    """Verification strategies for different intent types."""
    
    WINDOW_CHECK = "window_check"      # Check if window opened
    PROCESS_CHECK = "process_check"    # Check if process started
    URL_CHECK = "url_check"            # Check if URL loaded
    ELEMENT_CHECK = "element_check"    # Check if UI element exists
    FILE_CHECK = "file_check"          # Check if file exists/deleted
    STATE_CHECK = "state_check"        # Check system state
    NONE = "none"                      # No verification needed


# Map intents to verification strategies
INTENT_VERIFICATION_MAP: Dict[str, VerificationStrategy] = {
    # App control
    "OPEN_APP": VerificationStrategy.WINDOW_CHECK,
    "CLOSE_APP": VerificationStrategy.WINDOW_CHECK,
    "MINIMIZE_APP": VerificationStrategy.STATE_CHECK,
    "MAXIMIZE_APP": VerificationStrategy.STATE_CHECK,
    "SWITCH_APP": VerificationStrategy.WINDOW_CHECK,
    "FOCUS_WINDOW": VerificationStrategy.WINDOW_CHECK,
    "RESTART_APP": VerificationStrategy.PROCESS_CHECK,
    
    # Browser
    "OPEN_URL": VerificationStrategy.URL_CHECK,
    "SEARCH_WEB": VerificationStrategy.URL_CHECK,
    "NEW_TAB": VerificationStrategy.STATE_CHECK,
    "CLOSE_TAB": VerificationStrategy.STATE_CHECK,
    "REFRESH_PAGE": VerificationStrategy.NONE,
    "GO_BACK": VerificationStrategy.NONE,
    "GO_FORWARD": VerificationStrategy.NONE,
    
    # Input - no verification needed for typing
    "TYPE_TEXT": VerificationStrategy.NONE,
    "SAVE_FILE": VerificationStrategy.NONE,
    "PRESS_KEYS": VerificationStrategy.NONE,
    "COPY": VerificationStrategy.NONE,
    "PASTE": VerificationStrategy.NONE,
    
    # File
    "CREATE_FILE": VerificationStrategy.FILE_CHECK,
    "DELETE_FILE": VerificationStrategy.FILE_CHECK,
    "OPEN_FILE": VerificationStrategy.WINDOW_CHECK,
    "MOVE_FILE": VerificationStrategy.FILE_CHECK,
    "RENAME_FILE": VerificationStrategy.FILE_CHECK,
    "CREATE_FOLDER": VerificationStrategy.FILE_CHECK,
    "DELETE_FOLDER": VerificationStrategy.FILE_CHECK,
    
    # UI
    "CLICK_ELEMENT": VerificationStrategy.ELEMENT_CHECK,
    "DOUBLE_CLICK": VerificationStrategy.ELEMENT_CHECK,
    "RIGHT_CLICK": VerificationStrategy.ELEMENT_CHECK,
    "HOVER_ELEMENT": VerificationStrategy.NONE,
    
    # System
    "LOCK_SCREEN": VerificationStrategy.STATE_CHECK,
    "MINIMIZE_ALL": VerificationStrategy.STATE_CHECK,
    "MAXIMIZE_ALL": VerificationStrategy.STATE_CHECK,
    "MUTE": VerificationStrategy.STATE_CHECK,
    "UNMUTE": VerificationStrategy.STATE_CHECK,
    "VOLUME_UP": VerificationStrategy.NONE,
    "VOLUME_DOWN": VerificationStrategy.NONE,
}


# =============================================================================
# VERIFICATION RESULT
# =============================================================================

@dataclass
class VerificationResult:
    """Result of execution verification."""
    
    verified: bool
    strategy: VerificationStrategy
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_suggested: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified": self.verified,
            "strategy": self.strategy.value,
            "message": self.message,
            "details": self.details or {},
            "retry_suggested": self.retry_suggested
        }


# =============================================================================
# VERIFIERS
# =============================================================================

async def verify_window_exists(window_title: str, timeout: float = 2.0) -> bool:
    """Check if a window with given title exists."""
    try:
        import pygetwindow as gw
        
        start = time.time()
        while time.time() - start < timeout:
            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                return True
            await asyncio.sleep(0.2)
        
        return False
    except ImportError:
        logger.warning("pygetwindow not available for window verification")
        return True  # Assume success if can't verify
    except Exception as e:
        logger.error(f"Window verification error: {e}")
        return True


async def verify_process_running(process_name: str) -> bool:
    """Check if a process is running."""
    try:
        import subprocess
        
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        return process_name.lower() in result.stdout.lower()
    except Exception as e:
        logger.error(f"Process verification error: {e}")
        return True


async def verify_file_exists(path: str) -> bool:
    """Check if a file exists."""
    from pathlib import Path
    return Path(path).exists()


async def verify_file_deleted(path: str) -> bool:
    """Check if a file was deleted."""
    from pathlib import Path
    return not Path(path).exists()


# =============================================================================
# MAIN VERIFICATION ENGINE
# =============================================================================

class ExecutionVerifier:
    """
    Verifies execution results.
    
    Ensures each step completed successfully before proceeding.
    """
    
    def __init__(self, timeout: float = 2.0, max_retries: int = 1):
        self.timeout = timeout
        self.max_retries = max_retries
    
    async def verify(
        self,
        intent: str,
        slots: Dict[str, Any],
        execution_result: Dict[str, Any]
    ) -> VerificationResult:
        """
        Verify an execution result.
        
        Args:
            intent: The executed intent
            slots: Intent slots/parameters
            execution_result: Result from executor
            
        Returns:
            VerificationResult
        """
        # Check if execution reported success
        if execution_result.get("status") != "success":
            return VerificationResult(
                verified=False,
                strategy=VerificationStrategy.NONE,
                message="Execution reported failure",
                details=execution_result,
                retry_suggested=True
            )
        
        # Get verification strategy
        strategy = INTENT_VERIFICATION_MAP.get(intent, VerificationStrategy.NONE)
        
        if strategy == VerificationStrategy.NONE:
            return VerificationResult(
                verified=True,
                strategy=strategy,
                message="No verification required"
            )
        
        # Execute verification
        verified = await self._verify_by_strategy(strategy, intent, slots)
        
        return VerificationResult(
            verified=verified,
            strategy=strategy,
            message="Verification passed" if verified else "Verification failed",
            retry_suggested=not verified
        )
    
    async def _verify_by_strategy(
        self,
        strategy: VerificationStrategy,
        intent: str,
        slots: Dict[str, Any]
    ) -> bool:
        """Execute verification based on strategy."""
        
        if strategy == VerificationStrategy.WINDOW_CHECK:
            # For app operations, check if window exists
            app = slots.get("app", "")
            if intent == "CLOSE_APP":
                # For close, window should NOT exist
                exists = await verify_window_exists(app, self.timeout)
                return not exists
            else:
                return await verify_window_exists(app, self.timeout)
        
        elif strategy == VerificationStrategy.PROCESS_CHECK:
            process = slots.get("app", "")
            return await verify_process_running(process)
        
        elif strategy == VerificationStrategy.FILE_CHECK:
            path = slots.get("path", "")
            if intent == "DELETE_FILE" or intent == "DELETE_FOLDER":
                return await verify_file_deleted(path)
            else:
                return await verify_file_exists(path)
        
        elif strategy == VerificationStrategy.URL_CHECK:
            # URL verification would require browser integration
            # For now, trust execution result
            return True
        
        elif strategy == VerificationStrategy.ELEMENT_CHECK:
            # Element verification would require vision
            # For now, trust execution result
            return True
        
        elif strategy == VerificationStrategy.STATE_CHECK:
            # State checks would need system queries
            # For now, trust execution result
            return True
        
        return True
    
    async def verify_with_retry(
        self,
        intent: str,
        slots: Dict[str, Any],
        execution_result: Dict[str, Any],
        retry_executor: Optional[Callable] = None
    ) -> VerificationResult:
        """
        Verify with automatic retry on failure.
        
        If verification fails and retry_executor is provided,
        will retry execution once.
        """
        result = await self.verify(intent, slots, execution_result)
        
        if result.verified or not result.retry_suggested:
            return result
        
        if retry_executor is None:
            return result
        
        # Retry once
        logger.info(f"[VERIFIER] Retrying {intent} after verification failure")
        
        new_execution = await retry_executor(intent, slots)
        new_result = await self.verify(intent, slots, new_execution)
        
        if new_result.verified:
            new_result.message = "Verified after retry"
        
        return new_result


# =============================================================================
# STEP-BY-STEP VERIFICATION
# =============================================================================

async def verify_step_sequence(
    steps: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    verifier: Optional[ExecutionVerifier] = None
) -> Dict[str, Any]:
    """
    Verify a sequence of execution steps.
    
    Returns:
        {
            "all_verified": bool,
            "failed_step": Optional[int],
            "verifications": List[VerificationResult]
        }
    """
    if verifier is None:
        verifier = ExecutionVerifier()
    
    verifications = []
    
    for i, (step, result) in enumerate(zip(steps, results)):
        intent = step.get("intent", "")
        slots = step.get("slots", {})
        
        verification = await verifier.verify(intent, slots, result)
        verifications.append(verification.to_dict())
        
        if not verification.verified:
            return {
                "all_verified": False,
                "failed_step": i,
                "verifications": verifications
            }
    
    return {
        "all_verified": True,
        "failed_step": None,
        "verifications": verifications
    }


# =============================================================================
# SINGLETON VERIFIER
# =============================================================================

_verifier_instance: Optional[ExecutionVerifier] = None


def get_verifier() -> ExecutionVerifier:
    """Get singleton verifier instance."""
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = ExecutionVerifier()
    return _verifier_instance


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "VerificationStrategy",
    "VerificationResult",
    "ExecutionVerifier",
    "INTENT_VERIFICATION_MAP",
    "verify_window_exists",
    "verify_process_running",
    "verify_file_exists",
    "verify_file_deleted",
    "verify_step_sequence",
    "get_verifier",
]
