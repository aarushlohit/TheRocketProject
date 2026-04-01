"""Skill registry - manages skill discovery and instantiation."""

import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, Optional, Type

from agent.core.exceptions import SkillNotFoundError
from agent.skills.base import BaseSkill
from agent.utils.logger import get_logger


logger = get_logger(__name__)


class SkillRegistry:
    """Registry for available skills."""

    def __init__(self, adapter):
        """Initialize registry.
        
        Args:
            adapter: Platform adapter instance
        """
        self.adapter = adapter
        self.skills: Dict[str, Type[BaseSkill]] = {}
        self.instances: Dict[str, BaseSkill] = {}

    def register(self, action: str, skill_class: Type[BaseSkill]) -> None:
        """Register a skill.
        
        Args:
            action: Action name (e.g., "OPEN_APP")
            skill_class: Skill class
        """
        self.skills[action] = skill_class
        logger.info(f"Registered skill: {action}")

    def get_skill(self, action: str) -> BaseSkill:
        """Get or instantiate a skill.
        
        Args:
            action: Action name
            
        Returns:
            Skill instance
            
        Raises:
            SkillNotFoundError: If skill not found
        """
        if action in self.instances:
            return self.instances[action]

        if action not in self.skills:
            raise SkillNotFoundError(f"No skill for action: {action}")

        # Instantiate skill
        skill_class = self.skills[action]
        skill = skill_class(self.adapter)
        self.instances[action] = skill
        return skill

    def list_skills(self) -> list:
        """List all registered skill names.
        
        Returns:
            List of skill action names
        """
        return list(self.skills.keys())

    def auto_register(self, skills_dir: str = "agent/skills") -> None:
        """Auto-import and register all skills in directory.
        
        Args:
            skills_dir: Directory containing skill modules
        """
        # Manual registration for Phase 0
        # In Phase 1+, this will dynamically import skill_*.py files
        
        # For now, manually import core skills
        try:
            from agent.skills.skill_open_app import OpenAppSkill
            self.register("OPEN_APP", OpenAppSkill)
        except ImportError:
            logger.warning("Could not import OpenAppSkill")

        # More skills can be added here as they're implemented
        logger.info(f"Auto-registered {len(self.skills)} skills")

    def get_skill_help(self, action: str) -> Optional[str]:
        """Get help text for a skill.
        
        Args:
            action: Skill action name
            
        Returns:
            Help text or None if not found
        """
        try:
            skill = self.get_skill(action)
            return skill.get_help()
        except SkillNotFoundError:
            return None
