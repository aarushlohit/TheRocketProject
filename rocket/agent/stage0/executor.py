"""Execution routing for Stage 1.5 — Safety + Multi-Step + Accessibility."""

from __future__ import annotations

import asyncio
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Optional

from agent.core.intent import Intent
from agent.core.result import Result
from agent.core.safety import full_validation, validate_intent, requires_confirmation
from agent.platform.adapter import PlatformAdapter
from agent.utils.logger import get_logger


logger = get_logger(__name__)


class ActionExecutor:
    """
    Dispatches validated intents to the desktop platform adapter.
    
    Stage 1.5 Features:
    - Safety validation (confidence + dangerous patterns)
    - Multi-step execution support
    - Accessibility confirmation hooks
    """

    def __init__(
        self,
        platform: PlatformAdapter,
        artifacts_dir: Path,
        debug_mode: bool = False,
        platform_type: str = "auto",
        availability_checker: Callable[[str, str], bool] | None = None,
    ):
        self.platform = platform
        self.artifacts_dir = artifacts_dir
        self.debug_mode = debug_mode
        self.platform_type = platform_type
        self.availability_checker = availability_checker or is_available
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    async def execute_with_validation(
        self,
        parsed_json: dict,
        confirmation_callback: Optional[Callable] = None,
    ) -> Result:
        """
        Execute with full validation pipeline:
        0. Hard failure guard (model unavailable)
        1. Confidence check
        2. Safety check
        3. Confirmation (if required)
        4. Execute
        """
        print(f"\n========== [EXECUTE WITH VALIDATION] ==========")
        
        # Step 0: HARD FAILURE GUARD — Stop immediately if both models failed
        if parsed_json.get("status") == "error":
            reason = parsed_json.get("reason", "unknown_error")
            print(f"[HARD FAILURE GUARD] Model error: {reason}")
            return Result(
                status="error",
                message=parsed_json.get("message", "Model call failed"),
                error_code=reason,
                data={
                    "retryable": parsed_json.get("retryable", True),
                    "_model_used": parsed_json.get("_model_used", "none"),
                },
            )
        
        if parsed_json.get("_model_used") == "none":
            print(f"[HARD FAILURE GUARD] No model available")
            return Result(
                status="error",
                message="Both models failed - cannot process request",
                error_code="model_unavailable",
                data={"retryable": True},
            )
        
        # Step 1 & 2: Full validation
        is_valid, reason, details = full_validation(parsed_json)
        
        if not is_valid:
            print(f"[VALIDATION FAILED] {reason}")
            return Result(
                status="error",
                message=f"Validation failed: {reason}",
                error_code=reason,
                data=details,
            )
        
        # Step 3: Check if confirmation required
        if requires_confirmation(parsed_json):
            print(f"[CONFIRMATION REQUIRED]")
            if confirmation_callback:
                confirmed = await confirmation_callback(parsed_json)
                if not confirmed:
                    print(f"[CONFIRMATION DENIED]")
                    return Result(
                        status="error",
                        message="User cancelled action",
                        error_code="USER_CANCELLED",
                    )
            else:
                # No callback, but confirmation required → block
                print(f"[CONFIRMATION BLOCKED] No callback available")
                return Result(
                    status="error",
                    message="Dangerous action requires confirmation",
                    error_code="CONFIRMATION_REQUIRED",
                )
        
        # Step 4: Build Intent and execute
        intent = self._build_intent_from_json(parsed_json)
        return await self.execute(intent)

    def _build_intent_from_json(self, parsed_json: dict) -> Intent:
        """Build Intent from parsed JSON."""
        intent_type = parsed_json.get("intent", "UNKNOWN")
        slots = parsed_json.get("slots", {})
        if intent_type == "MULTI_STEP" and isinstance(parsed_json.get("steps"), list):
            slots = dict(slots)
            slots["steps"] = parsed_json.get("steps", [])
        confidence = parsed_json.get("confidence", 0.0)
        normalized_text = parsed_json.get("normalized_text", "")
        
        return Intent(
            action=intent_type,
            parameters=slots,
            confidence=confidence,
            metadata={"normalized_text": normalized_text},
        )

    async def execute(self, intent: Intent) -> Result:
        """Execute a validated intent."""
        print(f"\n========== [EXECUTOR START] ==========")
        print(f"[INTENT] {intent.action}")
        print(f"[PARAMETERS] {intent.parameters}")
        print(f"[CONFIDENCE] {intent.confidence}")

        try:
            if self.debug_mode:
                print(f"[EXECUTION RESULT] DEBUG - Dry run only")
                return Result(
                    status="debug",
                    message="Dry run executed",
                    data={
                        "intent": intent.action,
                        "slots": dict(intent.parameters),
                    },
                )

            action = intent.action
            params = dict(intent.parameters or {})

            if action == "CONFIRMATION_REQUIRED":
                return Result(
                    status="error",
                    message="Confirmation required before execution",
                    error_code="CONFIRMATION_REQUIRED",
                    data=params,
                )

            # MULTI_STEP executes sequentially with stop-on-failure behavior.
            if action == "MULTI_STEP":
                return await self._execute_multi_step(intent)

            if action == "OPEN_APP":
                app = str(params.get("app", "")).strip()
                if not app:
                    return Result(status="error", message="Missing app name", error_code="MISSING_APP")
                print(f"[EXECUTING] OPEN_APP: {app}")
                result = await self.platform.open_app(app)
                if isinstance(result, dict) and result.get("status") == "error":
                    # Self-correction retry once.
                    print("[RETRY] OPEN_APP initial attempt failed, retrying once")
                    result = await self.platform.open_app(app)
                status = result.get("status", "success") if isinstance(result, dict) else "success"
                if status == "error":
                    return Result(status="error", message=f"Failed to open {app}", error_code="OPEN_APP_FAILED", data=result)
                return Result(status="success", message=f"Opened {app}", data=result if isinstance(result, dict) else None)

            if action == "CLOSE_APP":
                app = params.get("app")
                target = params.get("target", "focused")
                await self.platform.close_app(app_name=app, target=target)
                return Result(status="success", message=f"Closed {app or 'focused window'}")

            if action in {"MINIMIZE", "MINIMIZE_APP"}:
                await self.platform.minimize(app_name=params.get("app"), target=params.get("target", "focused"))
                return Result(status="success", message="Window minimized")

            if action in {"MAXIMIZE", "MAXIMIZE_APP"}:
                await self.platform.maximize(app_name=params.get("app"), target=params.get("target", "focused"))
                return Result(status="success", message="Window maximized")

            if action == "SCREENSHOT":
                screenshot_path = await self.platform.screenshot(self.artifacts_dir)
                return Result(
                    status="success",
                    message=f"Saved screenshot to {screenshot_path}",
                    data={"screenshot_path": str(screenshot_path)},
                )

            if action == "SWITCH_APP":
                await self.platform.press_keys("alt+tab")
                return Result(status="success", message="Switched app")

            if action == "FOCUS_WINDOW":
                target_app = str(params.get("window") or params.get("app") or "").strip()
                if target_app:
                    result = await self.platform.open_app(target_app)
                    if isinstance(result, dict) and result.get("status") == "error":
                        await self.platform.press_keys("alt+tab")
                    return Result(status="success", message=f"Focused {target_app}")
                await self.platform.press_keys("alt+tab")
                return Result(status="success", message="Focused next window")

            if action == "OPEN_URL":
                url = str(params.get("url", "")).strip()
                await self.platform.open_url(url)
                return Result(status="success", message=f"Opened {url}")

            if action == "SEARCH_WEB":
                query = str(params.get("query", "")).strip()
                await self.platform.search_web(query)
                return Result(status="success", message=f"Searched: {query}")

            if action == "NEW_TAB":
                await self.platform.press_keys("ctrl+t")
                return Result(status="success", message="Opened new tab")

            if action == "CLOSE_TAB":
                await self.platform.press_keys("ctrl+w")
                return Result(status="success", message="Closed current tab")

            if action == "SWITCH_TAB":
                tab_index = params.get("tab_index")
                if isinstance(tab_index, int) and 1 <= tab_index <= 9:
                    await self.platform.press_keys(f"ctrl+{tab_index}")
                else:
                    await self.platform.press_keys("ctrl+tab")
                return Result(status="success", message="Switched tab")

            if action == "REFRESH_PAGE":
                await self.platform.press_keys("f5")
                return Result(status="success", message="Page refreshed")

            if action == "SCROLL_UP":
                await self.platform.scroll("up", int(params.get("amount", 5)))
                return Result(status="success", message="Scrolled up")

            if action == "SCROLL_DOWN":
                await self.platform.scroll("down", int(params.get("amount", 5)))
                return Result(status="success", message="Scrolled down")

            if action == "TYPE_TEXT":
                text = str(params.get("text", ""))
                result = await self.platform.type_text(text)
                status = result.get("status", "success") if isinstance(result, dict) else "success"
                if status == "error":
                    return Result(status="error", message="Failed to type text", error_code="TYPE_TEXT_FAILED", data=result)
                return Result(status="success", message=f"Typed {len(text)} characters")

            if action == "CLEAR_TEXT":
                await self.platform.press_keys("ctrl+a")
                await self.platform.press_keys("backspace")
                return Result(status="success", message="Cleared text")

            if action == "SELECT_TEXT":
                await self.platform.press_keys("ctrl+a")
                return Result(status="success", message="Selected text")

            if action == "COPY":
                await self.platform.press_keys("ctrl+c")
                return Result(status="success", message="Copied selection")

            if action == "PASTE":
                await self.platform.press_keys("ctrl+v")
                return Result(status="success", message="Pasted clipboard")

            if action == "CUT":
                await self.platform.press_keys("ctrl+x")
                return Result(status="success", message="Cut selection")

            if action == "PRESS_KEYS":
                keys = params.get("keys", "")
                if isinstance(keys, list):
                    keys = "+".join(str(k) for k in keys if k)
                keys = str(keys)
                result = await self.platform.press_keys(keys)
                status = result.get("status", "success") if isinstance(result, dict) else "success"
                if status == "error":
                    return Result(status="error", message=f"Failed to press keys: {keys}", error_code="PRESS_KEYS_FAILED", data=result)
                return Result(status="success", message=f"Pressed keys: {keys}")

            if action == "LOCK_SCREEN":
                await self.platform.press_keys("win+l")
                return Result(status="success", message="Screen locked")

            if action == "VOLUME_UP":
                await self.platform.press_keys("volumeup")
                return Result(status="success", message="Volume increased")

            if action == "VOLUME_DOWN":
                await self.platform.press_keys("volumedown")
                return Result(status="success", message="Volume decreased")

            if action == "MUTE":
                await self.platform.press_keys("volumemute")
                return Result(status="success", message="Mute toggled")

            if action == "BRIGHTNESS_UP":
                await self.platform.press_keys("brightnessup")
                return Result(status="success", message="Brightness increased")

            if action == "BRIGHTNESS_DOWN":
                await self.platform.press_keys("brightnessdown")
                return Result(status="success", message="Brightness decreased")

            if action == "OPEN_FILE":
                file_path = Path(str(params.get("path", "")).strip())
                if not file_path:
                    return Result(status="error", message="Missing file path", error_code="MISSING_PATH")
                subprocess.Popen(["cmd", "/c", "start", "", str(file_path)], shell=False)
                return Result(status="success", message=f"Opened file: {file_path}")

            if action == "DELETE_FILE":
                file_path = Path(str(params.get("path", "")).strip())
                if not file_path.exists():
                    return Result(status="error", message=f"File not found: {file_path}", error_code="FILE_NOT_FOUND")
                file_path.unlink()
                return Result(status="success", message=f"Deleted file: {file_path}")

            if action == "CREATE_FILE":
                file_path = Path(str(params.get("path", "")).strip())
                file_path.parent.mkdir(parents=True, exist_ok=True)
                content = str(params.get("content", ""))
                file_path.write_text(content, encoding="utf-8")
                return Result(status="success", message=f"Created file: {file_path}")

            if action == "MOVE_FILE":
                source = Path(str(params.get("source", "")).strip())
                destination = Path(str(params.get("destination", "")).strip())
                if not source.exists():
                    return Result(status="error", message=f"Source not found: {source}", error_code="FILE_NOT_FOUND")
                destination.parent.mkdir(parents=True, exist_ok=True)
                source.replace(destination)
                return Result(status="success", message=f"Moved file to: {destination}")

            if action == "RENAME_FILE":
                source = Path(str(params.get("path", "")).strip())
                new_name = str(params.get("new_name", "")).strip()
                if not source.exists():
                    return Result(status="error", message=f"File not found: {source}", error_code="FILE_NOT_FOUND")
                if not new_name:
                    return Result(status="error", message="Missing new file name", error_code="MISSING_NEW_NAME")
                destination = source.with_name(new_name)
                source.replace(destination)
                return Result(status="success", message=f"Renamed file to: {destination.name}")

            if action == "CLICK_ELEMENT":
                x_raw = params.get("x")
                y_raw = params.get("y")

                if x_raw is None or y_raw is None:
                    return Result(
                        status="error",
                        message="CLICK_ELEMENT requires numeric x and y coordinates",
                        error_code="MISSING_COORDINATES",
                        data={"slots": params},
                    )

                try:
                    x = int(float(x_raw))
                    y = int(float(y_raw))
                except (TypeError, ValueError):
                    return Result(
                        status="error",
                        message="CLICK_ELEMENT coordinates must be numbers",
                        error_code="INVALID_COORDINATES",
                        data={"slots": params},
                    )

                button = str(params.get("button", "left")).lower().strip() or "left"
                click_result = await self.platform.click(x, y, button=button)
                status = click_result.get("status", "success") if isinstance(click_result, dict) else "success"
                if status != "success":
                    return Result(
                        status="error",
                        message="Failed to click element",
                        error_code="CLICK_ELEMENT_FAILED",
                        data=click_result if isinstance(click_result, dict) else {"x": x, "y": y, "button": button},
                    )

                return Result(
                    status="success",
                    message=f"Clicked at ({x}, {y})",
                    data=click_result if isinstance(click_result, dict) else {"x": x, "y": y, "button": button},
                )

            if action == "SCROLL":
                direction = str(params.get("direction", "down")).lower()
                amount = int(params.get("amount", 5))
                scroll_result = await self.platform.scroll(direction, amount)
                status = scroll_result.get("status", "success") if isinstance(scroll_result, dict) else "success"
                if status != "success":
                    return Result(
                        status="error",
                        message=f"Failed to scroll {direction}",
                        error_code="SCROLL_FAILED",
                        data=scroll_result if isinstance(scroll_result, dict) else {"direction": direction, "amount": amount},
                    )
                return Result(
                    status="success",
                    message=f"Scrolled {direction}",
                    data=scroll_result if isinstance(scroll_result, dict) else {"direction": direction, "amount": amount},
                )

            if action == "WAIT":
                seconds = float(params.get("seconds", 1.0))
                seconds = max(0.0, min(seconds, 10.0))
                await asyncio.sleep(seconds)
                return Result(status="success", message=f"Waited {seconds:.1f}s")

            if action == "CONDITIONAL":
                then_step = params.get("then")
                else_step = params.get("else")
                condition_met = bool(params.get("condition_met", True))
                selected_step = then_step if condition_met else else_step
                if isinstance(selected_step, dict):
                    step_intent = self._build_intent_from_json(selected_step)
                    return await self.execute(step_intent)
                return Result(status="success", message="Conditional evaluated; no executable branch")

            if action == "UNKNOWN":
                return Result(
                    status="error",
                    message="Unknown intent",
                    error_code="UNKNOWN_INTENT",
                )

            print(f"[EXECUTION RESULT] ERROR - Unsupported intent: {action}")
            return Result(
                status="error",
                message=f"Unsupported intent: {action}",
                error_code="UNSUPPORTED_INTENT",
            )
            
        except Exception as exc:
            print(f"[EXECUTION ERROR] {exc}")
            logger.error("[EXECUTION ERROR]")
            logger.error(str(exc))
            return Result(
                status="error",
                message=str(exc),
                error_code="EXECUTION_ERROR",
            )

    async def _execute_multi_step(self, intent: Intent) -> Result:
        """
        Execute multi-step intent (Stage 2 support).
        
        Example:
        {
            "intent": "MULTI_STEP",
            "steps": [
                {"intent": "OPEN_APP", "slots": {"app": "notepad"}},
                {"intent": "TYPE_TEXT", "slots": {"text": "Hello"}}
            ]
        }
        """
        steps = intent.parameters.get("steps", [])
        print(f"\n========== [MULTI-STEP EXECUTION] ==========")
        print(f"[STEPS] {len(steps)} steps")
        
        results = []
        for i, step in enumerate(steps):
            print(f"\n[STEP {i+1}/{len(steps)}]")
            step_intent = self._build_intent_from_json(step)
            result = await self.execute(step_intent)
            results.append(result)
            
            if result.status == "error":
                print(f"[MULTI-STEP ABORTED] Step {i+1} failed")
                return Result(
                    status="error",
                    message=f"Multi-step failed at step {i+1}: {result.message}",
                    data={"step": i+1, "results": [r.__dict__ for r in results]},
                )
        
        print(f"\n[MULTI-STEP COMPLETE] All {len(steps)} steps succeeded")
        return Result(
            status="success",
            message=f"Completed {len(steps)} steps",
            data={"results": [r.__dict__ for r in results]},
        )


def is_available(cmd: str, platform_type: str = "auto") -> bool:
    """Best-effort cross-platform app availability check."""
    resolved_platform = platform_type
    if resolved_platform == "auto":
        resolved_platform = sys.platform

    if resolved_platform in {"darwin", "macos"}:
        if shutil.which(cmd):
            return True
        result = subprocess.run(
            ["open", "-Ra", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0

    if resolved_platform in {"win32", "windows"}:
        if shutil.which(cmd):
            return True
        # With hybrid execution, we don't need strict availability check
        # Windows Search fallback will find the app
        return True  # Always return True for Windows

    return shutil.which(cmd) is not None
