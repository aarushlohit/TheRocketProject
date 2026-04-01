"""Intent data structure - represents parsed user intention."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Intent:
    """Parsed user intent ready for execution.
    
    Attributes:
        action: Action to perform (e.g., "OPEN_APP", "TYPE_TEXT")
        parameters: Action-specific parameters
        confidence: Confidence score (0-1)
        context: Execution context
        metadata: Timing, source, etc.
    """

    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def validate(self) -> bool:
        """Validate intent is well-formed."""
        assert self.action, "Intent must have action"
        assert isinstance(self.action, str), "Action must be string"
        assert 0 <= self.confidence <= 1, "Confidence must be 0-1"
        assert isinstance(self.parameters, dict), "Parameters must be dict"
        return True

    def __str__(self) -> str:
        """String representation."""
        return f'Intent(action="{self.action}", parameters={self.parameters}, confidence={self.confidence:.2f})'

    def __repr__(self) -> str:
        """Detailed representation."""
        return self.__str__()
