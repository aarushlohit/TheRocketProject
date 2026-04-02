"""Execution routing for the Stage 0 validated intents."""

from __future__ import annotations

from pathlib import Path

from agent.core.intent import Intent
from agent.core.result import Result
from agent.platform.adapter import PlatformAdapter


class ActionExecutor:
    """Dispatches validated intents to the desktop platform adapter."""

    def __init__(self, platform: PlatformAdapter, artifacts_dir: Path):
        self.platform = platform
        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, intent: Intent) -> Result:
        if intent.action == "OPEN_APP":
            app = intent.parameters["app"]
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
