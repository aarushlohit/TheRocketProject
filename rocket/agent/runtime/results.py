"""Shared Rocket runtime result types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RocketExecutionResult:
    """Outcome of one Rocket task execution attempt."""

    task: str
    intent: str
    executor: str
    success: bool
    message: str
    details: list[str] = field(default_factory=list)
