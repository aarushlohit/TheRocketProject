#!/usr/bin/env python3
"""
Rocket PC Agent - Main Entry Point

This is the core automation agent that runs on the user's desktop.
It listens for commands from the mobile app via WebSocket and executes them.

Usage:
    python agent/main.py --config ~/.rocket/config.yaml
    python agent/main.py --host localhost --port 8765
"""

import asyncio
import argparse
import sys
from pathlib import Path

from agent.core.agent import Agent
from agent.utils.logger import get_logger
from agent.utils.config import load_config
from agent.server.websocket_handler import start_websocket_server


logger = get_logger(__name__)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Rocket PC Agent - Accessibility Automation System"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path.home() / ".rocket" / "config.yaml",
        help="Path to config file (default: ~/.rocket/config.yaml)",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="WebSocket server host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (verbose logging)",
    )

    args = parser.parse_args()

    # Set log level
    import logging
    logging.getLogger("agent").setLevel(
        "DEBUG" if args.debug else args.log_level
    )

    try:
        # Load configuration
        config = load_config(args.config)
        config.host = args.host
        config.port = args.port

        # Initialize agent
        agent = Agent(config)
        logger.info(f"Rocket Agent initialized")

        # Override config with CLI args if provided
        agent.config.host = args.host
        agent.config.port = args.port

        # Start WebSocket server
        logger.info(f"Starting WebSocket server on {args.host}:{args.port}")
        await start_websocket_server(agent, args.host, args.port)

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
