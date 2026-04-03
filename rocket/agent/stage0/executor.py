"""Execution routing for Stage 0 validated intents - REAL EXECUTION (No DRY RUN)."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable

from agent.core.intent import Intent
from agent.core.result import Result
from agent.platform.adapter import PlatformAdapter
from agent.utils.app_map import normalize_app
from agent.utils.logger import get_logger


logger = get_logger(__name__)


class ActionExecutor:
    """Dispatches validated intents to the desktop platform adapter - REAL EXECUTION."""

    def __init__(
        self,
        platform: PlatformAdapter,
        artifacts_dir: Path,
        debug_mode: bool = False,  # Changed default to False for REAL execution
        platform_type: str = "auto",
        availability_checker: Callable[[str, str], bool] | None = None,
    ):
        self.platform = platform
        self.artifacts_dir = artifacts_dir
        self.debug_mode = debug_mode
        self.platform_type = platform_type
        self.availability_checker = availability_checker or is_available
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, intent: Intent) -> Result:
        """Execute intent - REAL EXECUTION (DRY RUN REMOVED)."""
        print(f"\n========== [EXECUTOR START] ==========")
        print(f"[INTENT] {intent.action}")
        print(f"[PARAMETERS] {intent.parameters}")
        print(f"[DEBUG MODE] {self.debug_mode}")

        normalized_parameters = dict(intent.parameters)
        if "app" in normalized_parameters and isinstance(normalized_parameters["app"], str):
            normalized_parameters["app"] = normalize_app(
                normalized_parameters["app"],
                platform_type=self.platform_type,
            )
        intent.parameters = normalized_parameters

        print(f"[NORMALIZED PARAMETERS] {intent.parameters}")

        # DRY RUN REMOVED - Always execute for real
        # if self.debug_mode:
        #     logger.info("[DRY RUN]")
        #     ...

        try:
            if intent.action == "OPEN_APP":
                app = intent.parameters["app"]
                print(f"[EXECUTING] OPEN_APP: {app}")
                if not self.availability_checker(app, self.platform_type):
                    print(f"[WARNING] App availability check failed, attempting anyway...")
                await self.platform.open_app(app)
                print(f"[EXECUTION RESULT] SUCCESS - Opened {app}")
                return Result(status="success", message=f"Opened {app.title()}")

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
                url = intent.parameters["url"]
                print(f"[EXECUTING] OPEN_URL: {url}")
                await self.platform.open_url(url)
                print(f"[EXECUTION RESULT] SUCCESS - Opened {url}")
                return Result(status="success", message=f"Opened {url}")

            if intent.action == "SEARCH_WEB":
                query = intent.parameters.get("query", "")
                search_url = f"https://www.google.com/search?q={query}"
                print(f"[EXECUTING] SEARCH_WEB: {query}")
                await self.platform.open_url(search_url)
                print(f"[EXECUTION RESULT] SUCCESS - Searched: {query}")
                return Result(status="success", message=f"Searched: {query}")

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
        result = subprocess.run(
            ["where", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            shell=False,
        )
        return result.returncode == 0

    return shutil.which(cmd) is not None
