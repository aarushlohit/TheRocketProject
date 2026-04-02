"""Execution routing for the Stage 0 validated intents."""

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
    """Dispatches validated intents to the desktop platform adapter."""

    def __init__(
        self,
        platform: PlatformAdapter,
        artifacts_dir: Path,
        debug_mode: bool = True,
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
        normalized_parameters = dict(intent.parameters)
        if "app" in normalized_parameters and isinstance(normalized_parameters["app"], str):
            normalized_parameters["app"] = normalize_app(
                normalized_parameters["app"],
                platform_type=self.platform_type,
            )
        intent.parameters = normalized_parameters

        if self.debug_mode:
            logger.info("[DRY RUN]")
            logger.info(
                f"Would execute: {intent.action} with {intent.parameters}"
            )
            return Result(
                status="debug",
                message="Dry run executed",
                data={"intent": intent.action, "slots": intent.parameters},
            )

        try:
            if intent.action == "OPEN_APP":
                app = intent.parameters["app"]
                if not self.availability_checker(app, self.platform_type):
                    return Result(
                        status="error",
                        message="App not installed",
                        error_code="APP_NOT_INSTALLED",
                    )
                await self.platform.open_app(app)
                return Result(status="success", message=f"Opened {app.title()}")

            if intent.action == "CLOSE_APP":
                app = intent.parameters.get("app")
                target = intent.parameters.get("target", "focused")
                await self.platform.close_app(app_name=app, target=target)
                label = app.title() if app else "active window"
                return Result(status="success", message=f"Closed {label}")

            if intent.action == "MINIMIZE":
                app = intent.parameters.get("app")
                target = intent.parameters.get("target", "focused")
                await self.platform.minimize(app_name=app, target=target)
                label = app.title() if app else "active window"
                return Result(status="success", message=f"Minimized {label}")

            if intent.action == "MAXIMIZE":
                app = intent.parameters.get("app")
                target = intent.parameters.get("target", "focused")
                await self.platform.maximize(app_name=app, target=target)
                label = app.title() if app else "active window"
                return Result(status="success", message=f"Maximized {label}")

            if intent.action == "SCREENSHOT":
                screenshot_path = await self.platform.screenshot(self.artifacts_dir)
                return Result(
                    status="success",
                    message=f"Saved screenshot to {screenshot_path}",
                    data={"screenshot_path": str(screenshot_path)},
                )

            if intent.action == "OPEN_URL":
                url = intent.parameters["url"]
                await self.platform.open_url(url)
                return Result(status="success", message=f"Opened {url}")

            return Result(
                status="error",
                message=f"Unsupported intent: {intent.action}",
                error_code="UNSUPPORTED_INTENT",
            )
        except Exception as exc:
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
