"""Main Agent class - orchestrates skill execution."""

import time
from pathlib import Path
from typing import Optional

from agent.core.context import ExecutionContext
from agent.core.exceptions import (
    SkillNotFoundError,
    SkillExecutionError,
)
from agent.core.intent import Intent
from agent.core.result import Result
from agent.nlu.parser import NLUEngine
from agent.platform.adapter import get_platform_adapter
from agent.skills.registry import SkillRegistry
from agent.utils.config import Config
from agent.utils.logger import get_logger


logger = get_logger(__name__)


class Agent:
    """Main automation agent.
    
    Orchestrates:
    - Intent parsing (NLU)
    - Skill routing
    - Skill execution
    - Result feedback
    """

    def __init__(self, config: Config):
        """Initialize agent.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.context = ExecutionContext()
        
        # Initialize platform adapter
        self.platform = get_platform_adapter(config.platform_type)
        logger.info(f"Platform adapter initialized: {type(self.platform).__name__}")
        
        # Initialize NLU engine
        self.nlu = NLUEngine(self.platform)
        logger.info("NLU engine initialized")
        
        # Initialize skill registry and register all skills
        self.skill_registry = SkillRegistry(self.platform)
        self.skill_registry.auto_register()
        logger.info(f"Skills registered: {self.skill_registry.list_skills()}")

    async def handle_voice_input(self, text: str) -> Result:
        """Process voice transcription.
        
        Args:
            text: Transcribed text from voice input
            
        Returns:
            Result of execution
        """
        logger.info(f"Voice input received: {text}")
        
        # Parse text to intent
        intent = self.nlu.parse(text, context=self.context)
        logger.info(f"Parsed intent: {intent}")
        
        # Execute intent
        return await self.execute_intent(intent)

    async def handle_drawing_input(self, strokes: list) -> Result:
        """Process drawing gesture.
        
        Args:
            strokes: List of stroke data from drawing
            
        Returns:
            Result of execution
        """
        logger.debug(f"Drawing input received with {len(strokes)} strokes")
        
        # Recognize gesture
        intent = self.nlu.recognize_gesture(strokes)
        logger.info(f"Recognized gesture: {intent}")
        
        # Execute intent
        return await self.execute_intent(intent)

    async def execute_intent(self, intent: Intent) -> Result:
        """Route intent to appropriate skill and execute.
        
        Args:
            intent: Parsed intent to execute
            
        Returns:
            Result of skill execution
        """
        # Validate intent
        try:
            intent.validate()
        except AssertionError as e:
            logger.error(f"Invalid intent: {e}")
            return Result(
                status="error",
                message=f"Invalid intent: {e}",
                error_code="INVALID_INTENT",
            )

        # Get skill
        try:
            skill = self.skill_registry.get_skill(intent.action)
        except SkillNotFoundError as e:
            logger.warning(f"Skill not found: {intent.action}")
            return Result(
                status="error",
                message=f"I don't know how to '{intent.action}'. Please try something else.",
                error_code="SKILL_NOT_FOUND",
            )

        # Validate parameters
        if not skill.validate_parameters(intent):
            logger.warning(f"Invalid parameters for skill {intent.action}: {intent.parameters}")
            return Result(
                status="error",
                message=f"Invalid parameters for action. {skill.get_help()}",
                error_code="INVALID_PARAMETERS",
            )

        # Execute skill
        try:
            start_time = time.time()
            result = await skill.execute(intent, context=self.context)
            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms
            
            logger.info(f"Skill executed: {intent.action} -> {result.status} ({duration_ms:.0f}ms)")
            
            # Record in context
            self.context.record_action(intent, result)
            
            return result
        except SkillExecutionError as e:
            logger.error(f"Skill execution error: {e}")
            return Result(
                status="error",
                message=f"Failed to execute action: {str(e)}",
                error_code="SKILL_EXECUTION_ERROR",
            )
        except Exception as e:
            logger.exception(f"Unexpected error in skill execution")
            return Result(
                status="error",
                message="An unexpected error occurred. Please try again.",
                error_code="INTERNAL_ERROR",
            )

    def list_skills(self) -> list:
        """List all registered skills.
        
        Returns:
            List of skill names
        """
        return self.skill_registry.list_skills()

    def get_skill_help(self, skill_name: str) -> Optional[str]:
        """Get help text for a skill.
        
        Args:
            skill_name: Name of skill
            
        Returns:
            Help text or None if skill not found
        """
        try:
            skill = self.skill_registry.get_skill(skill_name)
            return skill.get_help()
        except SkillNotFoundError:
            return None
