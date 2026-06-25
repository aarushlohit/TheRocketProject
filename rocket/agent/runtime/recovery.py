"""Recovery decision engine for Rocket.

When a task hangs, times out, the browser/Playwright is busy, a tool throws, or
a session is lost, Rocket decides how to heal: retry, reuse/restore the browser,
reconnect Playwright/OpenCode, reuse the session, switch MCP/strategy, or fall
back to vision. Asking the user is always the last resort.

This module only *decides*. The actual OS/tool actions are performed by the
runtime. Keeping the decision pure makes the policy fully testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    REUSE_BROWSER = "reuse_browser"
    RESTORE_BROWSER = "restore_browser"
    RECONNECT_PLAYWRIGHT = "reconnect_playwright"
    RECONNECT_OPENCODE = "reconnect_opencode"
    REUSE_SESSION = "reuse_session"
    ALTERNATIVE_MCP = "alternative_mcp"
    VISION_FALLBACK = "vision_fallback"
    ALTERNATIVE_STRATEGY = "alternative_strategy"
    ASK_USER = "ask_user"


# Failure reasons.
TIMEOUT = "timeout"
PLAYWRIGHT_BUSY = "playwright_busy"
BROWSER_IN_USE = "browser_in_use"
TOOL_EXCEPTION = "tool_exception"
LOST_SESSION = "lost_session"
VERIFIER_FAILED = "verifier_failed"
UNKNOWN = "unknown"


# Ordered recovery plans per reason. ASK_USER is always last.
_PLANS: dict[str, list[RecoveryStrategy]] = {
    TIMEOUT: [
        RecoveryStrategy.RETRY,
        RecoveryStrategy.RECONNECT_OPENCODE,
        RecoveryStrategy.ALTERNATIVE_STRATEGY,
        RecoveryStrategy.ASK_USER,
    ],
    PLAYWRIGHT_BUSY: [
        RecoveryStrategy.RECONNECT_PLAYWRIGHT,
        RecoveryStrategy.REUSE_BROWSER,
        RecoveryStrategy.RESTORE_BROWSER,
        RecoveryStrategy.ALTERNATIVE_MCP,
        RecoveryStrategy.ASK_USER,
    ],
    BROWSER_IN_USE: [
        RecoveryStrategy.REUSE_BROWSER,
        RecoveryStrategy.RESTORE_BROWSER,
        RecoveryStrategy.RECONNECT_PLAYWRIGHT,
        RecoveryStrategy.ASK_USER,
    ],
    TOOL_EXCEPTION: [
        RecoveryStrategy.RETRY,
        RecoveryStrategy.ALTERNATIVE_MCP,
        RecoveryStrategy.VISION_FALLBACK,
        RecoveryStrategy.ALTERNATIVE_STRATEGY,
        RecoveryStrategy.ASK_USER,
    ],
    LOST_SESSION: [
        RecoveryStrategy.REUSE_SESSION,
        RecoveryStrategy.RECONNECT_OPENCODE,
        RecoveryStrategy.RETRY,
        RecoveryStrategy.ASK_USER,
    ],
    VERIFIER_FAILED: [
        RecoveryStrategy.RETRY,
        RecoveryStrategy.VISION_FALLBACK,
        RecoveryStrategy.ALTERNATIVE_STRATEGY,
        RecoveryStrategy.ASK_USER,
    ],
    UNKNOWN: [
        RecoveryStrategy.RETRY,
        RecoveryStrategy.ALTERNATIVE_STRATEGY,
        RecoveryStrategy.ASK_USER,
    ],
}

_REASON_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (PLAYWRIGHT_BUSY, ("playwright already in use", "playwright busy", "browser is already in use by playwright")),
    (BROWSER_IN_USE, ("chrome already in use", "browser already in use", "profile is already in use", "user data directory")),
    (LOST_SESSION, ("lost session", "session not found", "session expired", "no session", "session id")),
    (TIMEOUT, ("timed out", "timeout", "deadline exceeded", "hang", "hung")),
    (TOOL_EXCEPTION, ("exception", "traceback", "error:", "tool failed", "stream error", "crash")),
    (VERIFIER_FAILED, ("could not verify", "not visible", "verifier", "not installed", "still off", "not connected")),
)


def classify_failure(message: str) -> str:
    """Map a failure message to a recovery reason."""

    lower = (message or "").lower()
    for reason, markers in _REASON_MARKERS:
        if any(marker in lower for marker in markers):
            return reason
    return UNKNOWN


def recovery_plan(reason: str) -> list[RecoveryStrategy]:
    """Ordered strategies for a reason. ASK_USER is always last."""

    return list(_PLANS.get(reason, _PLANS[UNKNOWN]))


@dataclass
class RecoveryMetrics:
    attempts: int = 0
    recovery_count: int = 0
    recovery_reason: str = ""
    recovery_success: bool = False
    history: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "attempts": self.attempts,
            "recovery_count": self.recovery_count,
            "recovery_reason": self.recovery_reason,
            "recovery_success": self.recovery_success,
            "history": list(self.history),
        }


class RecoveryEngine:
    """Stateful recovery decider. One engine per task execution."""

    def __init__(self, max_attempts: int = 4) -> None:
        self.max_attempts = max(1, max_attempts)
        self.metrics = RecoveryMetrics()
        self._plan: list[RecoveryStrategy] = []
        self._cursor = 0

    def begin(self, message: str) -> str:
        """Record a failure and lock in the recovery plan for its reason."""

        reason = classify_failure(message)
        self.metrics.recovery_reason = reason
        self._plan = recovery_plan(reason)
        self._cursor = 0
        return reason

    def next_strategy(self) -> RecoveryStrategy:
        """Advance to the next recovery strategy.

        Returns ASK_USER once non-user strategies are exhausted or the attempt
        budget is spent. Never returns ASK_USER before trying real strategies.
        """

        if not self._plan:
            self._plan = recovery_plan(UNKNOWN)
            self._cursor = 0

        self.metrics.attempts += 1
        non_user = [s for s in self._plan if s is not RecoveryStrategy.ASK_USER]

        if self._cursor >= len(non_user) or self.metrics.attempts > self.max_attempts:
            self.metrics.history.append(RecoveryStrategy.ASK_USER.value)
            return RecoveryStrategy.ASK_USER

        strategy = non_user[self._cursor]
        self._cursor += 1
        self.metrics.recovery_count += 1
        self.metrics.history.append(strategy.value)
        return strategy

    def record_success(self) -> None:
        self.metrics.recovery_success = True

    def should_ask_user(self) -> bool:
        return bool(self.metrics.history) and self.metrics.history[-1] == RecoveryStrategy.ASK_USER.value
