"""Result data structure - represents skill execution outcome."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Result:
    """Skill execution result.
    
    Attributes:
        status: "success", "error", "executing", "clarification_needed"
        message: User-facing message
        data: Execution-specific data
        duration_ms: Execution time in milliseconds
        feedback: Haptic/audio feedback to provide
    """

    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    duration_ms: float = 0.0
    feedback: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None

    def __post_init__(self):
        """Validate result."""
        assert self.status in [
            "success",
            "error",
            "executing",
            "clarification_needed",
        ], f"Invalid status: {self.status}"
        assert isinstance(self.message, str), "Message must be string"
        assert self.duration_ms >= 0, "Duration must be non-negative"

    def __str__(self) -> str:
        """String representation."""
        return f'Result(status="{self.status}", message="{self.message}", duration_ms={self.duration_ms:.0f})'

    def __repr__(self) -> str:
        """Detailed representation."""
        return self.__str__()

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == "success"

    def is_error(self) -> bool:
        """Check if execution resulted in error."""
        return self.status == "error"
