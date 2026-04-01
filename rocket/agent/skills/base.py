"""Base skill class - all skills inherit from this."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from agent.core.context import ExecutionContext
from agent.core.intent import Intent
from agent.core.result import Result
from agent.utils.logger import get_logger


class BaseSkill(ABC):
    """Base class for all skills.
    
    Every skill must:
    1. Inherit from BaseSkill
    2. Implement execute() method
    3. Define metadata (NAME, DESCRIPTION, etc.)
    """

    # Metadata - override in subclass
    NAME: str = "UNKNOWN"
    DESCRIPTION: str = "No description provided"
    CATEGORY: str = "general"  # productivity, browser, system, etc.
    COMPLEXITY: str = "moderate"  # simple, moderate, advanced
    REQUIRES_PERMISSIONS: list = []
    VOICE_PATTERNS: list = []
    GESTURE_PATTERNS: list = []

    def __init__(self, adapter):
        """Initialize skill.
        
        Args:
            adapter: Platform adapter instance
        """
        self.adapter = adapter
        self.logger = get_logger(self.NAME)

    @abstractmethod
    async def execute(
        self, intent: Intent, context: ExecutionContext
    ) -> Result:
        """Execute the skill.
        
        Args:
            intent: Parsed intent to execute
            context: Execution context
            
        Returns:
            Result of execution
        """
        pass

    def validate_parameters(self, intent: Intent) -> bool:
        """Validate that intent has required parameters.
        
        Args:
            intent: Intent to validate
            
        Returns:
            True if valid, False otherwise
        """
        return True

    def get_help(self) -> str:
        """Get usage help text.
        
        Returns:
            Help string
        """
        return f"{self.NAME}: {self.DESCRIPTION}"

    def __str__(self) -> str:
        """String representation."""
        return f"{self.NAME} skill"

    def __repr__(self) -> str:
        """Detailed representation."""
        return self.__str__()
