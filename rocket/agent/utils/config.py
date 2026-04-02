"""Configuration loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from agent.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class Config:
    """Agent configuration."""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8765
    log_level: str = "INFO"
    
    # Platform
    platform_type: str = "auto"  # auto, windows, macos, linux
    
    # Skills
    enabled_skills: list = field(default_factory=list)
    disabled_skills: list = field(default_factory=list)
    
    # NLU
    confidence_threshold: float = 0.6
    ask_on_ambiguous: bool = True
    
    # Models
    whisper_model: str = "base"  # tiny, base, small, medium, large
    device: str = "auto"  # cuda, cpu, mps, auto
    
    # Additional settings
    data_dir: Path = Path("data/stage0")
    extra: Dict[str, Any] = field(default_factory=dict)


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Config object
    """
    config = Config()
    
    # Use default if not provided
    if config_path is None:
        config_path = Path.home() / ".rocket" / "config.yaml"
    
    if config_path.exists():
        logger.info(f"Loading config from {config_path}")
        try:
            with open(config_path, "r") as f:
                data = yaml.safe_load(f) or {}
            
            # Update config from file
            if "agent" in data:
                agent_cfg = data["agent"]
                config.host = agent_cfg.get("host", config.host)
                config.port = agent_cfg.get("port", config.port)
                config.log_level = agent_cfg.get("log_level", config.log_level)
            
            if "platform" in data:
                platform_cfg = data["platform"]
                config.platform_type = platform_cfg.get("type", config.platform_type)
            
            if "skills" in data:
                skills_cfg = data["skills"]
                config.enabled_skills = skills_cfg.get("enabled", config.enabled_skills)
                config.disabled_skills = skills_cfg.get("disabled", config.disabled_skills)
            
            if "nlu" in data:
                nlu_cfg = data["nlu"]
                config.confidence_threshold = nlu_cfg.get("confidence_threshold", config.confidence_threshold)
                config.ask_on_ambiguous = nlu_cfg.get("ask_on_ambiguous", config.ask_on_ambiguous)

            if "storage" in data:
                storage_cfg = data["storage"]
                configured_dir = storage_cfg.get("data_dir")
                if configured_dir:
                    config.data_dir = Path(configured_dir)
            
            if "models" in data:
                models_cfg = data["models"]
                config.whisper_model = models_cfg.get("whisper_model", config.whisper_model)
                config.device = models_cfg.get("device", config.device)
            
            logger.info(f"Config loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            logger.info("Using default configuration")
    else:
        logger.info(f"Config file not found at {config_path}, using defaults")
    
    return config


def create_default_config() -> None:
    """Create default configuration file."""
    config_dir = Path.home() / ".rocket"
    config_file = config_dir / "config.yaml"
    
    if config_file.exists():
        logger.info(f"Config file already exists at {config_file}")
        return
    
    # Create directory
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create default config
    default_config = """# Rocket Agent Configuration

agent:
  host: 0.0.0.0
  port: 8765
  log_level: INFO

platform:
  type: auto  # auto-detect platform

skills:
  enabled:
    - OPEN_APP
    - TYPE_TEXT
    - PRESS_KEYS
    - SCROLL
    - CLICK
    - OPEN_URL
  disabled: []

nlu:
  confidence_threshold: 0.6
  ask_on_ambiguous: true

storage:
  data_dir: data/stage0

models:
  whisper_model: base  # tiny, base, small, medium, large
  device: auto  # cuda, cpu, mps, auto
"""
    
    with open(config_file, "w") as f:
        f.write(default_config)
    
    logger.info(f"Default config created at {config_file}")
