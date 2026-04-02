"""Logging setup with a graceful stdlib fallback."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

try:
    from loguru import logger as loguru_logger
except ImportError:  # pragma: no cover - exercised only when loguru is absent
    loguru_logger = None


def get_logger(name: str):
    """Get a configured logger using loguru when available."""
    if loguru_logger is not None:
        return loguru_logger.bind(name=name)
    return logging.getLogger(name)


def setup_logging(level: str = "INFO"):
    """Configure logging handlers for the current process."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    if loguru_logger is not None:
        loguru_logger.remove()
        loguru_logger.add(
            sys.stderr,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[name]}</cyan> - <level>{message}</level>",
            level=level,
        )
        loguru_logger.add(
            logs_dir / "rocket-agent.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[name]} - {message}",
            level="DEBUG",
            rotation="500 MB",
        )
        return

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler(logs_dir / "rocket-agent.log"),
        ],
    )
