"""Execution routing for Stage 1.5 — Safety + Multi-Step + Accessibility."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Optional

from agent.core.intent import Intent
from agent.core.result import Result
from agent.core.safety import full_validation, validate_intent, requires_confirmation
from agent.platform.adapter import PlatformAdapter
from agent.utils.app_map import normalize_app
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
                status="rejected",
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
                        status="cancelled",
                        message="User cancelled action",
                        error_code="USER_CANCELLED",
                    )
            else:
                # No callback, but confirmation required → block
                print(f"[CONFIRMATION BLOCKED] No callback available")
                return Result(
                    status="blocked",
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

        # Normalize app names
        normalized_parameters = dict(intent.parameters)
        if "app" in normalized_parameters and isinstance(normalized_parameters["app"], str):
            normalized_parameters["app"] = normalize_app(
                normalized_parameters["app"],
                platform_type=self.platform_type,
            )
        intent.parameters = normalized_parameters

        print(f"[NORMALIZED PARAMETERS] {intent.parameters}")

        try:
            # MULTI_STEP support (Stage 2)
            if intent.action == "MULTI_STEP":
                return await self._execute_multi_step(intent)

            if intent.action == "OPEN_APP":
                app = intent.parameters.get("app", "")
                print(f"[EXECUTING] OPEN_APP: {app}")
                result = await self.platform.open_app(app)
                method = result.get("method", "unknown") if isinstance(result, dict) else "unknown"
                print(f"[EXECUTION RESULT] SUCCESS - Opened {app} via {method}")
                return Result(
                    status="success",
                    message=f"Opened {app.title()}",
                    data={"method": method},
                )

            if intent.action == "CLOSE_APP":
                app = intent.parameters.get("app")
                target = intent.parameters.get("target", "focused")
                print(f"[EXECUTING] CLOSE_APP: {app or 'focused'}")
                await self.platform.close_app(app_name=app, target=target)
                label = app.title() if app else "active window"
                print(f"[EXECUTION RESULT] SUCCESS - Closed {label}")
                return Result(status="success", message=f"Closed {label}")

            if intent.action == "MINIMIZE":
                app = intent.parameters.get("app")
                target = intent.parameters.get("target", "focused")
                print(f"[EXECUTING] MINIMIZE: {app or 'focused'}")
                await self.platform.minimize(app_name=app, target=target)
                label = app.title() if app else "active window"
                print(f"[EXECUTION RESULT] SUCCESS - Minimized {label}")
                return Result(status="success", message=f"Minimized {label}")

            if intent.action == "MAXIMIZE":
                app = intent.parameters.get("app")
                target = intent.parameters.get("target", "focused")
                print(f"[EXECUTING] MAXIMIZE: {app or 'focused'}")
                await self.platform.maximize(app_name=app, target=target)
                label = app.title() if app else "active window"
                print(f"[EXECUTION RESULT] SUCCESS - Maximized {label}")
                return Result(status="success", message=f"Maximized {label}")

            if intent.action == "SCREENSHOT":
                print(f"[EXECUTING] SCREENSHOT")
                screenshot_path = await self.platform.screenshot(self.artifacts_dir)
                print(f"[EXECUTION RESULT] SUCCESS - Screenshot at {screenshot_path}")
                return Result(
                    status="success",
                    message=f"Saved screenshot to {screenshot_path}",
                    data={"screenshot_path": str(screenshot_path)},
                )

            if intent.action == "OPEN_URL":
                url = intent.parameters.get("url", "")
                print(f"[EXECUTING] OPEN_URL: {url}")
                await self.platform.open_url(url)
                print(f"[EXECUTION RESULT] SUCCESS - Opened {url}")
                return Result(status="success", message=f"Opened {url}")

            if intent.action == "SEARCH_WEB":
                query = intent.parameters.get("query", "")
                print(f"[EXECUTING] SEARCH_WEB: {query}")
                result = await self.platform.search_web(query)
                print(f"[EXECUTION RESULT] SUCCESS - Searched: {query}")
                return Result(status="success", message=f"Searched: {query}")

            if intent.action == "TYPE_TEXT":
                text = intent.parameters.get("text", "")
                print(f"[EXECUTING] TYPE_TEXT: {text[:30]}...")
                result = await self.platform.type_text(text)
                print(f"[EXECUTION RESULT] {result}")
                return Result(
                    status=result.get("status", "success"),
                    message=f"Typed {len(text)} characters",
                )

            if intent.action == "PRESS_KEYS":
                keys = intent.parameters.get("keys", "")
                print(f"[EXECUTING] PRESS_KEYS: {keys}")
                result = await self.platform.press_keys(keys)
                print(f"[EXECUTION RESULT] {result}")
                return Result(
                    status=result.get("status", "success"),
                    message=f"Pressed keys: {keys}",
                )

            print(f"[EXECUTION RESULT] ERROR - Unsupported intent: {intent.action}")
            return Result(
                status="error",
                message=f"Unsupported intent: {intent.action}",
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
