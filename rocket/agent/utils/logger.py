"""Logging setup."""

import sys
from loguru import logger as loguru_logger


def get_logger(name: str):
    """Get logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger
    """
    return loguru_logger.bind(name=name)


def setup_logging(level: str = "INFO"):
    """Configure logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    # Remove default handler
    loguru_logger.remove()

    # Add stderr handler with format
    loguru_logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[name]}</cyan> - <level>{message}</level>",
        level=level,
    )

    # Optionally add file logging
    loguru_logger.add(
        "logs/rocket-agent.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[name]} - {message}",
        level="DEBUG",
        rotation="500 MB",
    )
