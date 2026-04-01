"""OpenApp skill - opens applications."""

import subprocess
import sys

from agent.core.context import ExecutionContext
from agent.core.intent import Intent
from agent.core.result import Result
from agent.skills.base import BaseSkill


class OpenAppSkill(BaseSkill):
    """Open an application by name."""

    NAME = "OPEN_APP"
    DESCRIPTION = "Open an application"
    CATEGORY = "system"
    COMPLEXITY = "simple"
    VOICE_PATTERNS = [
        r"open (?P<app>\w+)",
        r"launch (?P<app>\w+)",
        r"start (?P<app>\w+)",
    ]

    SUPPORTED_APPS = [
        "chrome",
        "firefox",
        "vscode",
        "notepad",
        "spotify",
        "slack",
        "teams",
        "discord",
    ]

    async def execute(self, intent: Intent, context: ExecutionContext) -> Result:
        """Open application."""
        app = intent.parameters.get("app")
        if not app:
            return Result(
                status="error",
                message="No app specified",
                error_code="MISSING_PARAMETER",
            )

        app = app.lower().strip()

        # Check if in supported list (optional in Phase 0, can be permissive)
        # For now, warn but allow
        if app not in self.SUPPORTED_APPS:
            self.logger.warning(f"App '{app}' not in known list, will attempt anyway")

        try:
            # Open app using platform adapter
            await self.adapter.open_app(app)

            return Result(
                status="success",
                message=f"{app.capitalize()} opened",
                feedback={"type": "haptic", "pattern": "success"},
            )
        except Exception as e:
            self.logger.error(f"Failed to open {app}: {e}")
            return Result(
                status="error",
                message=f"Failed to open {app}",
                error_code="APP_LAUNCH_FAILED",
            )

    def validate_parameters(self, intent: Intent) -> bool:
        """Validate parameters."""
        return "app" in intent.parameters

    def get_help(self) -> str:
        """Get help text."""
        return f"Open an app. Usage: 'open [app_name]'. Supported: {', '.join(self.SUPPORTED_APPS)}"
