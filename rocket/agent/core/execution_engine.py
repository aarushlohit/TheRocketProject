"""Unified Execution Engine — Production-Grade AI Operator (DEPRECATED).

⚠️  UNIFIED ARCHITECTURE NOTICE:
    This module is DEPRECATED for new code. All execution should go through:
    
    IntelligentPipeline.process() in intelligent_pipeline.py
    
    The IntelligentPipeline provides the complete Stage 3 intelligence layer:
    - Intent refinement
    - Execution planning  
    - Guardrails validation
    - Self-correction
    - Context awareness
    
    This ExecutionEngine remains for backward compatibility only.
    
    MIGRATION GUIDE:
    OLD: engine.execute_intent(intent_data)
    NEW: pipeline.process(intent_data)

LEGACY FUNCTIONALITY (still available):
This is the SINGLE ENTRY POINT for all intent execution.

PATCHED VERSION:
- Integrated FeedbackManager
- Integrated ConfirmationManager
- Integrated ExecutionVerifier
- All WebSocket communication
- NO CLI, NO fake success

Pipeline:
    Intent → Safety → Confirmation → Execution → Verification → Feedback
"""

from __future__ import annotations

import asyncio
import ctypes
import time
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple

from agent.core.safety import (
    CONFIDENCE_THRESHOLD,
    full_validation,
    is_dangerous_text,
    is_dangerous_keys,
    requires_confirmation,
)
from agent.core.user_profile import UserProfile, get_or_create_profile
from agent.core.feedback_manager import (
    FeedbackManager,
    get_feedback_manager,
    init_feedback_manager,
    EventType,
    Priority,
)
from agent.core.confirmation_system import (
    ConfirmationManager,
    get_confirmation_manager,
    init_confirmation_manager,
)
from agent.core.execution_verifier import verify_execution
from agent.platform.audio_control import mute as mute_system_audio, unmute as unmute_system_audio
from agent.platform.window_control import maximize_all_windows
from agent.platform.adapter import PlatformAdapter
from agent.utils.logger import get_logger


logger = get_logger(__name__)


def minimize_all_windows() -> None:
    """Show the desktop on Windows without relying on pyautogui."""
    user32 = ctypes.windll.user32
    user32.keybd_event(0x5B, 0, 0, 0)
    user32.keybd_event(0x44, 0, 0, 0)
    user32.keybd_event(0x44, 0, 2, 0)
    user32.keybd_event(0x5B, 0, 2, 0)


# =============================================================================
# EXECUTION RESULT
# =============================================================================

@dataclass
class ExecutionResult:
    """
    Standardized execution result.
    
    ALWAYS return this format - never raw strings.
    """
    status: str  # success | failed | blocked | confirmation_required
    message: str
    intent: str
    confidence: float
    
    # Optional details
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    requires_confirmation: bool = False
    verified: bool = False  # NEW: Verification status
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "status": self.status,
            "message": self.message,
            "intent": self.intent,
            "confidence": self.confidence,
            "verified": self.verified,
        }
        if self.data:
            result["data"] = self.data
        if self.error_code:
            result["error_code"] = self.error_code
        if self.requires_confirmation:
            result["requires_confirmation"] = True
        return result
    
    def to_websocket_message(self) -> dict:
        """Convert to WebSocket result message."""
        return {
            "type": "result",
            **self.to_dict(),
        }


# =============================================================================
# EXECUTION ENGINE (PATCHED)
# =============================================================================

class ExecutionEngine:
    """
    Unified execution engine for all intents.
    
    SINGLE ENTRY POINT: execute_intent()
    
    PATCHED Pipeline:
    1. Validate input
    2. Safety check
    3. Confirmation (REAL WebSocket loop)
    4. Notify execution start
    5. Execute action
    6. VERIFY execution
    7. Notify result
    8. Return JSON
    """
    
    def __init__(
        self,
        platform: PlatformAdapter,
        user_profile: Optional[UserProfile] = None,
        websocket_callback: Optional[Callable[[dict], Any]] = None,
    ):
        self.platform = platform
        self.profile = user_profile or get_or_create_profile()
        self.websocket_callback = websocket_callback
        
        # Initialize feedback manager
        self.feedback = init_feedback_manager(
            profile=self.profile,
            websocket_callback=websocket_callback,
        )
        
        # Initialize confirmation manager
        self.confirmation = init_confirmation_manager(
            websocket_callback=websocket_callback,
        )
    
    def set_websocket_callback(self, callback: Callable[[dict], Any]):
        """Set WebSocket callback for all managers."""
        self.websocket_callback = callback
        self.feedback.set_websocket_callback(callback)
        self.confirmation.set_websocket_callback(callback)
    
    # -------------------------------------------------------------------------
    # MAIN ENTRY POINT
    # -------------------------------------------------------------------------
    
    async def execute_intent(
        self,
        intent_data: dict,
        skip_confirmation: bool = False,
    ) -> ExecutionResult:
        """
        SINGLE ENTRY POINT for all intent execution.
        
        PATCHED PIPELINE:
        1. Validate input
        2. Hard failure guard
        3. Safety check
        4. Confirmation (REAL WebSocket loop)
        5. Notify execution start
        6. Execute action
        7. VERIFY execution
        8. Notify result
        9. Return JSON
        
        Args:
            intent_data: Parsed intent from model
            skip_confirmation: If True, skip confirmation for dangerous actions
        
        Returns:
            ExecutionResult with status, message, verified flag
        """
        print(f"\n{'='*60}")
        print(f"========== [EXECUTION ENGINE] ==========")
        print(f"{'='*60}")
        
        intent_type = intent_data.get("intent", "UNKNOWN")
        confidence = intent_data.get("confidence", 0.0)
        slots = intent_data.get("slots", {})
        
        # =====================================================================
        # STEP 1: LOG INPUT
        # =====================================================================
        print(f"\n[EXECUTION START]")
        print(f"[INTENT] {intent_type}")
        print(f"[PARAMETERS] {slots}")
        print(f"[CONFIDENCE] {confidence}")
        print(f"[ACCESSIBILITY MODE] {self.profile.get_feedback_mode()}")
        
        await self.feedback.input_received("intent")
        
        # =====================================================================
        # STEP 2: HARD FAILURE GUARD
        # =====================================================================
        if intent_data.get("status") == "error":
            await self.feedback.model_failure(intent_data.get("message", "Model error"))
            return await self._handle_model_error(intent_data)
        
        if intent_data.get("_model_used") == "none":
            await self.feedback.model_failure("Both models failed")
            
            # Send error via WebSocket
            await self._send_websocket({
                "type": "error",
                "message": "AI model unavailable - cannot process request",
                "retryable": True,
            })
            
            return ExecutionResult(
                status="failed",
                message="Model unavailable - cannot process request",
                intent=intent_type,
                confidence=confidence,
                error_code="MODEL_UNAVAILABLE",
            )
        
        # =====================================================================
        # STEP 3: SAFETY CHECK
        # =====================================================================
        print(f"\n[SAFETY CHECK]")
        await self.feedback.notify(EventType.SAFETY_CHECK, "Checking safety")
        
        safety_result = await self._safety_check(intent_data)
        if safety_result is not None:
            return safety_result
        
        await self.feedback.notify(EventType.SAFETY_PASSED, "Safety check passed")
        
        # =====================================================================
        # STEP 4: CONFIRMATION CHECK (REAL WebSocket Loop)
        # =====================================================================
        if not skip_confirmation and requires_confirmation(intent_data):
            print(f"\n[CONFIRMATION REQUIRED]")
            await self.feedback.danger_detected(intent_type)
            
            # Request confirmation via WebSocket and WAIT
            action_desc = f"{intent_type}: {slots}"
            confirmed = await self.confirmation.request_confirmation(
                action=action_desc,
                intent_data=intent_data,
                timeout=30.0,
            )
            
            if not confirmed:
                await self.feedback.notify(
                    EventType.CONFIRMATION_TIMEOUT,
                    "Confirmation denied or timed out",
                    Priority.HIGH,
                )
                return ExecutionResult(
                    status="blocked",
                    message="Confirmation denied or timed out",
                    intent=intent_type,
                    confidence=confidence,
                    error_code="CONFIRMATION_DENIED",
                )
            
            await self.feedback.notify(
                EventType.CONFIRMATION_RECEIVED,
                "Confirmation received - proceeding",
            )
        
        # =====================================================================
        # STEP 5: NOTIFY EXECUTION START
        # =====================================================================
        print(f"\n[ACTION] Executing {intent_type}")
        await self.feedback.execution_start(f"{intent_type}: {slots.get('app', slots.get('text', '')[:20])}")
        
        try:
            # =====================================================================
            # STEP 6: EXECUTE
            # =====================================================================
            result = await self._dispatch_intent(intent_type, slots, confidence)
            
            # =====================================================================
            # STEP 7: VERIFY EXECUTION
            # =====================================================================
            if result.status == "success":
                print(f"\n[EXECUTION VERIFY]")
                verified, verify_msg = verify_execution(intent_type, slots, wait_time=2.0)
                result.verified = verified
                
                if verified:
                    await self.feedback.execution_verified(intent_type)
                else:
                    # Execution reported success but verification failed
                    await self.feedback.notify(
                        EventType.EXECUTION_FAILURE,
                        f"Verification failed: {verify_msg}",
                        Priority.HIGH,
                    )
                    result.status = "failed"
                    result.message = f"Verification failed: {verify_msg}"
                    result.error_code = "VERIFICATION_FAILED"
            
            # =====================================================================
            # STEP 8: NOTIFY RESULT
            # =====================================================================
            if result.status == "success":
                await self.feedback.execution_success(result.message)
            elif result.status == "failed":
                await self.feedback.execution_failure(intent_type, result.message)
            
            # Send result via WebSocket
            await self._send_websocket(result.to_websocket_message())
            
            print(f"\n[RESULT] {result.status}: {result.message} (verified={result.verified})")
            return result
            
        except Exception as e:
            logger.error(f"Execution error: {e}")
            await self.feedback.execution_failure(intent_type, str(e))
            
            error_result = ExecutionResult(
                status="failed",
                message=str(e),
                intent=intent_type,
                confidence=confidence,
                error_code="EXECUTION_ERROR",
            )
            
            await self._send_websocket(error_result.to_websocket_message())
            return error_result
    
    async def _send_websocket(self, message: dict):
        """Send message via WebSocket."""
        print(f"[WS SEND] {message.get('type')}: {message.get('message', message.get('text', ''))[:50]}")
        
        if self.websocket_callback:
            if asyncio.iscoroutinefunction(self.websocket_callback):
                await self.websocket_callback(message)
            else:
                self.websocket_callback(message)
    
    def handle_confirmation_response(self, confirmation_id: str, confirmed: bool) -> bool:
        """
        Handle confirmation response from mobile app.
        
        Called by WebSocket handler when confirmation message received.
        """
        return self.confirmation.handle_response(confirmation_id, confirmed)
    
    # -------------------------------------------------------------------------
    # SAFETY CHECK
    # -------------------------------------------------------------------------
    
    async def _safety_check(self, intent_data: dict) -> Optional[ExecutionResult]:
        """
        Perform safety validation.
        
        Returns ExecutionResult if blocked, None if safe.
        """
        intent_type = intent_data.get("intent", "UNKNOWN")
        confidence = intent_data.get("confidence", 0.0)
        slots = intent_data.get("slots", {})
        
        # 1. UNKNOWN intent → ignore safely
        if intent_type == "UNKNOWN":
            print(f"[SAFETY] UNKNOWN intent - ignoring safely")
            return ExecutionResult(
                status="blocked",
                message="Could not understand the command",
                intent=intent_type,
                confidence=confidence,
                error_code="UNKNOWN_INTENT",
            )
        
        # 2. Confidence gate
        if confidence < CONFIDENCE_THRESHOLD:
            print(f"[SAFETY] Confidence {confidence} < {CONFIDENCE_THRESHOLD} - BLOCKED")
            await self.feedback.notify(
                EventType.SAFETY_BLOCKED,
                f"Low confidence: {confidence:.0%}",
                Priority.HIGH,
            )
            return ExecutionResult(
                status="blocked",
                message=f"Confidence too low: {confidence:.2f}",
                intent=intent_type,
                confidence=confidence,
                error_code="LOW_CONFIDENCE",
                data={"threshold": CONFIDENCE_THRESHOLD},
            )
        
        # 3. Dangerous command detection - just log, confirmation is handled in step 4
        if intent_type == "TYPE_TEXT":
            text = slots.get("text", "")
            if is_dangerous_text(text):
                print(f"[SAFETY] Dangerous text detected - will require confirmation")
        
        if intent_type == "PRESS_KEYS":
            keys = slots.get("keys", "")
            if is_dangerous_keys(keys):
                print(f"[SAFETY] Dangerous keys detected - will require confirmation")
        
        print(f"[SAFETY] PASSED ✓")
        return None  # Safe to proceed
    
    # -------------------------------------------------------------------------
    # INTENT DISPATCHER
    # -------------------------------------------------------------------------
    
    async def _dispatch_intent(
        self,
        intent_type: str,
        slots: dict,
        confidence: float,
    ) -> ExecutionResult:
        """Dispatch intent to appropriate handler."""
        
        # MULTI_STEP handling
        if intent_type == "MULTI_STEP":
            return await self._execute_multi_step(slots, confidence)
        
        # Single intent handlers
        handlers = {
            "OPEN_APP": self._execute_open_app,
            "FOCUS_APP": self._execute_focus_app,
            "OPEN_URL": self._execute_open_url,
            "SEARCH_WEB": self._execute_search_web,
            "TYPE_TEXT": self._execute_type_text,
            "PRESS_KEYS": self._execute_press_keys,
            "SCREENSHOT": self._execute_screenshot,
            "CLOSE_APP": self._execute_close_app,
            "MINIMIZE": self._execute_minimize,
            "MAXIMIZE": self._execute_maximize,
            "MINIMIZE_APP": self._execute_minimize_app,
            "MAXIMIZE_APP": self._execute_maximize_app,
            "RESTORE_APP": self._execute_restore_app,
            "LOCK_SCREEN": self._execute_lock_screen,
            "MINIMIZE_ALL": self._execute_minimize_all,
            "MAXIMIZE_ALL": self._execute_maximize_all,
            "SHOW_DESKTOP": self._execute_show_desktop,
            "VOLUME_UP": self._execute_volume_up,
            "VOLUME_DOWN": self._execute_volume_down,
            "MUTE": self._execute_mute,
            "UNMUTE": self._execute_unmute,
            "UNDO": self._execute_undo,
            "REDO": self._execute_redo,
        }
        
        handler = handlers.get(intent_type)
        if handler is None:
            return ExecutionResult(
                status="failed",
                message=f"Unsupported intent: {intent_type}",
                intent=intent_type,
                confidence=confidence,
                error_code="UNSUPPORTED_INTENT",
            )
        
        return await handler(slots, confidence)
    
    # -------------------------------------------------------------------------
    # INTENT HANDLERS
    # -------------------------------------------------------------------------
    
    async def _execute_open_app(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute OPEN_APP intent."""
        app = slots.get("app", "")
        
        if not app:
            return ExecutionResult(
                status="failed",
                message="No app specified",
                intent="OPEN_APP",
                confidence=confidence,
                error_code="MISSING_APP",
            )

        result = await self.platform.open_app(app)

        if result.get("status") == "success":
            return ExecutionResult(
                status="success",
                message=f"Opened {app}",
                intent="OPEN_APP",
                confidence=confidence,
                data={"app": app, "method": result.get("method")},
            )
        else:
            return ExecutionResult(
                status="failed",
                message=f"Failed to open {app}",
                intent="OPEN_APP",
                confidence=confidence,
                error_code="OPEN_FAILED",
            )

    async def _execute_focus_app(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute FOCUS_APP intent by opening or foregrounding the target app."""
        app = slots.get("app", "")
        if not app:
            return ExecutionResult(
                status="failed",
                message="No app specified",
                intent="FOCUS_APP",
                confidence=confidence,
                error_code="MISSING_APP",
            )

        result = await self.platform.open_app(app)
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message=f"Focused {app}" if result.get("status") == "success" else f"Failed to focus {app}",
            intent="FOCUS_APP",
            confidence=confidence,
            data={"app": app},
        )
    
    async def _execute_open_url(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute OPEN_URL intent."""
        url = slots.get("url", "")
        
        if not url:
            return ExecutionResult(
                status="failed",
                message="No URL specified",
                intent="OPEN_URL",
                confidence=confidence,
                error_code="MISSING_URL",
            )
        
        result = await self.platform.open_url(url)
        
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message=f"Opened {url}" if result.get("status") == "success" else f"Failed to open {url}",
            intent="OPEN_URL",
            confidence=confidence,
            data={"url": url},
        )
    
    async def _execute_search_web(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute SEARCH_WEB intent."""
        query = slots.get("query", "")
        
        if not query:
            return ExecutionResult(
                status="failed",
                message="No search query specified",
                intent="SEARCH_WEB",
                confidence=confidence,
                error_code="MISSING_QUERY",
            )
        
        result = await self.platform.search_web(query)
        
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message=f"Searched: {query}" if result.get("status") == "success" else f"Search failed",
            intent="SEARCH_WEB",
            confidence=confidence,
            data={"query": query},
        )
    
    async def _execute_type_text(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute TYPE_TEXT intent."""
        text = slots.get("text", "")
        
        if not text:
            return ExecutionResult(
                status="failed",
                message="No text specified",
                intent="TYPE_TEXT",
                confidence=confidence,
                error_code="MISSING_TEXT",
            )
        
        result = await self.platform.type_text(text)
        
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message=f"Typed {len(text)} characters",
            intent="TYPE_TEXT",
            confidence=confidence,
            data={"chars": len(text)},
        )
    
    async def _execute_press_keys(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute PRESS_KEYS intent."""
        keys = slots.get("keys", "")
        
        if not keys:
            return ExecutionResult(
                status="failed",
                message="No keys specified",
                intent="PRESS_KEYS",
                confidence=confidence,
                error_code="MISSING_KEYS",
            )

        if "volume" in keys.lower():
            print("[BLOCKED] volume via press_keys disabled")
            return ExecutionResult(
                status="failed",
                message="Volume via PRESS_KEYS disabled",
                intent="PRESS_KEYS",
                confidence=confidence,
                error_code="VOLUME_PRESS_KEYS_DISABLED",
            )
        
        result = await self.platform.press_keys(keys)
        
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message=f"Pressed: {keys}",
            intent="PRESS_KEYS",
            confidence=confidence,
            data={"keys": keys},
        )
    
    async def _execute_screenshot(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute SCREENSHOT intent."""
        from pathlib import Path
        output_dir = Path.home() / ".rocket" / "screenshots"
        
        try:
            screenshot_path = await self.platform.screenshot(output_dir)
            return ExecutionResult(
                status="success",
                message=f"Screenshot saved",
                intent="SCREENSHOT",
                confidence=confidence,
                data={"path": str(screenshot_path)},
            )
        except Exception as e:
            return ExecutionResult(
                status="failed",
                message=f"Screenshot failed: {e}",
                intent="SCREENSHOT",
                confidence=confidence,
                error_code="SCREENSHOT_FAILED",
            )
    
    async def _execute_close_app(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute CLOSE_APP intent."""
        app = slots.get("app")
        target = slots.get("target", "focused")
        
        result = await self.platform.close_app(app_name=app, target=target)
        
        label = app if app else "focused window"
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message=f"Closed {label}",
            intent="CLOSE_APP",
            confidence=confidence,
        )

    async def _execute_minimize_app(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute MINIMIZE_APP intent."""
        app = slots.get("app")
        print(f"[WINDOW CONTROL] MINIMIZE_APP -> {slots}")
        result = await self.platform.minimize(app_name=app, target="focused")
        label = app if app else "focused window"
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message=f"Minimized {label}",
            intent="MINIMIZE_APP",
            confidence=confidence,
        )

    async def _execute_maximize_app(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute MAXIMIZE_APP intent."""
        app = slots.get("app")
        print(f"[WINDOW CONTROL] MAXIMIZE_APP -> {slots}")
        result = await self.platform.maximize(app_name=app, target="focused")
        label = app if app else "focused window"
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message=f"Maximized {label}",
            intent="MAXIMIZE_APP",
            confidence=confidence,
        )

    async def _execute_restore_app(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute RESTORE_APP intent."""
        app = slots.get("app")
        print(f"[WINDOW CONTROL] RESTORE_APP -> {slots}")
        result = await self.platform.restore(app_name=app, target="focused")
        label = app if app else "focused window"
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message=f"Restored {label}",
            intent="RESTORE_APP",
            confidence=confidence,
        )

    async def _execute_minimize(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute MINIMIZE intent."""
        result = await self.platform.minimize()
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message="Minimized window",
            intent="MINIMIZE",
            confidence=confidence,
        )
    
    async def _execute_maximize(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute MAXIMIZE intent."""
        result = await self.platform.maximize()
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message="Maximized window",
            intent="MAXIMIZE",
            confidence=confidence,
        )

    async def _execute_lock_screen(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute LOCK_SCREEN intent."""
        result = await self.platform.lock_screen()
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message="Locked screen" if result.get("status") == "success" else "Failed to lock screen",
            intent="LOCK_SCREEN",
            confidence=confidence,
        )

    async def _execute_minimize_all(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute MINIMIZE_ALL intent."""
        try:
            minimize_all_windows()
            return ExecutionResult(
                status="success",
                message="All windows minimized",
                intent="MINIMIZE_ALL",
                confidence=confidence,
            )
        except Exception as e:
            return ExecutionResult(
                status="failed",
                message=f"Failed to minimize all windows: {e}",
                intent="MINIMIZE_ALL",
                confidence=confidence,
                error_code="MINIMIZE_ALL_FAILED",
            )

    async def _execute_show_desktop(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute SHOW_DESKTOP intent."""
        try:
            minimize_all_windows()
            return ExecutionResult(
                status="success",
                message="Showed desktop",
                intent="SHOW_DESKTOP",
                confidence=confidence,
            )
        except Exception as e:
            return ExecutionResult(
                status="failed",
                message=f"Failed to show desktop: {e}",
                intent="SHOW_DESKTOP",
                confidence=confidence,
                error_code="SHOW_DESKTOP_FAILED",
            )

    async def _execute_maximize_all(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute MAXIMIZE_ALL intent."""
        try:
            print("[WINDOW CONTROL] MAXIMIZE ALL")
            affected = maximize_all_windows()
            if affected <= 0:
                return ExecutionResult(
                    status="failed",
                    message="No visible windows maximized",
                    intent="MAXIMIZE_ALL",
                    confidence=confidence,
                    error_code="MAXIMIZE_ALL_FAILED",
                )
            return ExecutionResult(
                status="success",
                message="All windows maximized",
                intent="MAXIMIZE_ALL",
                confidence=confidence,
                data={"affected_windows": affected},
            )
        except Exception as e:
            return ExecutionResult(
                status="failed",
                message=f"Failed to maximize all windows: {e}",
                intent="MAXIMIZE_ALL",
                confidence=confidence,
                error_code="MAXIMIZE_ALL_FAILED",
            )

    async def _execute_volume_up(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute VOLUME_UP intent."""
        value = max(0, min(100, int(slots.get("value", 5) or 5)))
        print(f"[VOLUME ACTION] value={value}")
        print(f"[VOLUME] UP by {abs(value)}%")
        amount = value / 100.0
        result = await self.platform.volume_up(amount)
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message="Volume increased" if result.get("status") == "success" else "Failed to increase volume",
            intent="VOLUME_UP",
            confidence=confidence,
            data={"value": value},
        )

    async def _execute_volume_down(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute VOLUME_DOWN intent."""
        value = max(0, min(100, int(slots.get("value", 5) or 5)))
        print(f"[VOLUME ACTION] value={value}")
        print(f"[VOLUME] DOWN by {abs(value)}%")
        amount = value / 100.0
        result = await self.platform.volume_down(amount)
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message="Volume decreased" if result.get("status") == "success" else "Failed to decrease volume",
            intent="VOLUME_DOWN",
            confidence=confidence,
            data={"value": value},
        )

    async def _execute_mute(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute MUTE intent."""
        try:
            mute_system_audio()
            return ExecutionResult(
                status="success",
                message="Muted",
                intent="MUTE",
                confidence=confidence,
            )
        except Exception as e:
            return ExecutionResult(
                status="failed",
                message=f"Failed to mute audio: {e}",
                intent="MUTE",
                confidence=confidence,
                error_code="MUTE_FAILED",
            )

    async def _execute_unmute(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute UNMUTE intent."""
        try:
            unmute_system_audio()
            return ExecutionResult(
                status="success",
                message="Unmuted",
                intent="UNMUTE",
                confidence=confidence,
            )
        except Exception as e:
            return ExecutionResult(
                status="failed",
                message=f"Failed to unmute audio: {e}",
                intent="UNMUTE",
                confidence=confidence,
                error_code="UNMUTE_FAILED",
            )

    async def _execute_undo(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute UNDO intent."""
        result = await self.platform.press_keys("ctrl+z")
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message="Undo executed" if result.get("status") == "success" else "Failed to execute undo",
            intent="UNDO",
            confidence=confidence,
        )

    async def _execute_redo(self, slots: dict, confidence: float) -> ExecutionResult:
        """Execute REDO intent."""
        result = await self.platform.press_keys("ctrl+y")
        return ExecutionResult(
            status="success" if result.get("status") == "success" else "failed",
            message="Redo executed" if result.get("status") == "success" else "Failed to execute redo",
            intent="REDO",
            confidence=confidence,
        )
    
    # -------------------------------------------------------------------------
    # MULTI-STEP EXECUTION
    # -------------------------------------------------------------------------
    
    async def _execute_multi_step(self, slots: dict, confidence: float) -> ExecutionResult:
        """
        Execute multi-step intent.
        
        Executes steps sequentially. Stops on first failure.
        Notifies user of each step.
        """
        steps = slots.get("steps", [])
        
        if not steps:
            return ExecutionResult(
                status="failed",
                message="No steps provided",
                intent="MULTI_STEP",
                confidence=confidence,
                error_code="NO_STEPS",
            )
        
        print(f"\n========== [MULTI-STEP EXECUTION] ==========")
        print(f"[STEPS] {len(steps)} steps to execute")
        
        await self.feedback.multi_step_start(len(steps))
        
        results = []
        
        for i, step in enumerate(steps):
            print(f"\n[STEP {i+1}/{len(steps)}]")
            await self.feedback.step_progress(i + 1, len(steps))
            
            # Execute step
            result = await self.execute_intent(step, skip_confirmation=True)
            results.append(result.to_dict())
            
            # Stop on failure
            if result.status == "failed":
                await self.feedback.execution_failure(
                    "MULTI_STEP",
                    f"Step {i+1} failed: {result.message}",
                )
                return ExecutionResult(
                    status="failed",
                    message=f"Multi-step failed at step {i+1}: {result.message}",
                    intent="MULTI_STEP",
                    confidence=confidence,
                    error_code="STEP_FAILED",
                    data={"failed_step": i+1, "results": results},
                )
            
            # Brief pause between steps
            await asyncio.sleep(0.5)
        
        print(f"\n[MULTI-STEP COMPLETE] All {len(steps)} steps succeeded")
        await self.feedback.multi_step_complete(len(steps))
        
        return ExecutionResult(
            status="success",
            message=f"Completed {len(steps)} steps",
            intent="MULTI_STEP",
            confidence=confidence,
            data={"results": results},
            verified=True,  # Multi-step verifies each step
        )
    
    # -------------------------------------------------------------------------
    # ERROR HANDLING
    # -------------------------------------------------------------------------
    
    async def _handle_model_error(self, intent_data: dict) -> ExecutionResult:
        """Handle model-level errors."""
        reason = intent_data.get("reason", "unknown_error")
        message = intent_data.get("message", "Model error")
        retryable = intent_data.get("retryable", True)
        
        # Send error via WebSocket
        await self._send_websocket({
            "type": "error",
            "message": message,
            "reason": reason,
            "retryable": retryable,
        })
        
        return ExecutionResult(
            status="failed",
            message=message,
            intent="UNKNOWN",
            confidence=0.0,
            error_code=reason,
            data={"retryable": retryable},
        )


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

async def execute_intent(
    intent_data: dict,
    platform: PlatformAdapter,
    user_profile: Optional[UserProfile] = None,
    websocket_callback: Optional[Callable[[dict], Any]] = None,
) -> ExecutionResult:
    """
    Convenience function for one-off execution.
    
    Creates engine instance and executes.
    """
    engine = ExecutionEngine(platform, user_profile, websocket_callback)
    return await engine.execute_intent(intent_data)


# =============================================================================
# STAGE 3 INTELLIGENT PIPELINE INTEGRATION
# =============================================================================

async def execute_intent_intelligent(
    intent_data: dict,
    platform: PlatformAdapter,
    user_profile: Optional[UserProfile] = None,
    websocket_callback: Optional[Callable[[dict], Any]] = None,
) -> ExecutionResult:
    """
    Execute intent using Stage 3 Intelligent Pipeline.
    
    This is the NEW recommended entry point that provides:
    - Intent refinement (spelling correction, normalization)
    - Execution planning (multi-step expansion)
    - Context memory (session awareness)
    - Self-correction (automatic retry with modifications)
    - Smart delays (adaptive timing)
    - Guardrails (safety validation)
    
    Args:
        intent_data: Parsed intent from model
        platform: Platform adapter for execution
        user_profile: User accessibility profile
        websocket_callback: WebSocket notification callback
        
    Returns:
        ExecutionResult compatible with existing pipeline
    """
    from agent.core.intelligent_pipeline import IntelligentPipeline
    
    # Create intelligent pipeline
    pipeline = IntelligentPipeline(
        platform=platform,
        websocket_callback=websocket_callback,
        user_profile=user_profile,
    )
    
    # Execute through intelligent pipeline
    result = await pipeline.process(intent_data)
    
    # Convert to ExecutionResult for compatibility
    if result.plan_result:
        return ExecutionResult(
            status=result.status,
            message=result.message,
            intent=result.original_intent.get("intent", "UNKNOWN") if result.original_intent else "UNKNOWN",
            confidence=result.original_intent.get("confidence", 0.0) if result.original_intent else 0.0,
            data={
                "completed_steps": result.plan_result.completed_steps,
                "total_steps": result.plan_result.total_steps,
                "execution_time": result.execution_time,
                "step_results": result.plan_result.results,
            },
            error_code=result.plan_result.failed_reason if result.status == "failed" else None,
            verified=result.status == "success",
        )
    else:
        return ExecutionResult(
            status=result.status,
            message=result.message,
            intent=result.original_intent.get("intent", "UNKNOWN") if result.original_intent else "UNKNOWN",
            confidence=0.0,
            error_code=result.message if result.status == "failed" else None,
        )


class IntelligentExecutionEngine(ExecutionEngine):
    """
    Enhanced ExecutionEngine with Stage 3 Intelligence Layer.
    
    Drop-in replacement for ExecutionEngine that adds:
    - Intent refinement
    - Execution planning
    - Context memory
    - Self-correction
    - Smart delays
    
    Usage:
        engine = IntelligentExecutionEngine(platform, profile, websocket_callback)
        result = await engine.execute_intent(intent_data)
    """
    
    def __init__(
        self,
        platform: PlatformAdapter,
        user_profile: Optional[UserProfile] = None,
        websocket_callback: Optional[Callable[[dict], Any]] = None,
        use_intelligence: bool = True,
    ):
        super().__init__(platform, user_profile, websocket_callback)
        self.use_intelligence = use_intelligence
        
        if use_intelligence:
            from agent.core.intelligent_pipeline import IntelligentPipeline
            self.intelligent_pipeline = IntelligentPipeline(
                platform=platform,
                websocket_callback=websocket_callback,
                user_profile=user_profile,
            )
        else:
            self.intelligent_pipeline = None
    
    async def execute_intent(
        self,
        intent_data: dict,
        skip_confirmation: bool = False,
        use_intelligent: bool = None,
    ) -> ExecutionResult:
        """
        Execute intent with optional intelligent pipeline.
        
        Args:
            intent_data: Parsed intent from model
            skip_confirmation: Skip dangerous action confirmation
            use_intelligent: Override default intelligence setting
            
        Returns:
            ExecutionResult
        """
        # Determine whether to use intelligent pipeline
        should_use_intelligent = use_intelligent if use_intelligent is not None else self.use_intelligence
        
        if should_use_intelligent and self.intelligent_pipeline:
            print(f"\n[ENGINE MODE] Using Intelligent Pipeline (Stage 3)")
            result = await self.intelligent_pipeline.process(intent_data)
            
            # Convert PipelineResult to ExecutionResult
            if result.plan_result:
                return ExecutionResult(
                    status=result.status,
                    message=result.message,
                    intent=result.original_intent.get("intent", "UNKNOWN") if result.original_intent else "UNKNOWN",
                    confidence=result.original_intent.get("confidence", 0.0) if result.original_intent else 0.0,
                    data={
                        "completed_steps": result.plan_result.completed_steps,
                        "total_steps": result.plan_result.total_steps,
                        "execution_time": result.execution_time,
                    },
                    error_code=result.plan_result.failed_reason if result.status == "failed" else None,
                    verified=result.status == "success",
                )
            else:
                return ExecutionResult(
                    status=result.status,
                    message=result.message,
                    intent="UNKNOWN",
                    confidence=0.0,
                )
        else:
            print(f"\n[ENGINE MODE] Using Standard Pipeline")
            return await super().execute_intent(intent_data, skip_confirmation)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ExecutionEngine",
    "ExecutionResult",
    "execute_intent",
    # Stage 3 additions
    "IntelligentExecutionEngine",
    "execute_intent_intelligent",
]
