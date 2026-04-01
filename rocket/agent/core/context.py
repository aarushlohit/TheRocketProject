"""Execution context - tracks state during automation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from agent.core.intent import Intent
from agent.core.result import Result


@dataclass
class ExecutionContext:
    """Track state during automation execution.
    
    Provides context for intents (previous actions, current focus, etc.)
    """

    foreground_app: Optional[str] = None
    action_history: List[Tuple[Intent, Result]] = field(default_factory=list)
    clipboard_content: Optional[str] = None
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    session_state: Dict[str, Any] = field(default_factory=dict)

    def record_action(self, intent: Intent, result: Result) -> None:
        """Record an action for context awareness."""
        self.action_history.append((intent, result))

    def get_last_action(self) -> Optional[Intent]:
        """Get previous action for context."""
        return self.action_history[-1][0] if self.action_history else None

    def get_last_result(self) -> Optional[Result]:
        """Get result of previous action."""
        return self.action_history[-1][1] if self.action_history else None

    def get_action_history(self, limit: int = 10) -> List[Tuple[Intent, Result]]:
        """Get recent action history."""
        return self.action_history[-limit:]

    def clear_history(self) -> None:
        """Clear action history (for new session)."""
        self.action_history.clear()
