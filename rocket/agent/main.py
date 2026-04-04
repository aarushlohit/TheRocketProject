#!/usr/bin/env python3
"""
Nova Stage 0 backend entry point.

Usage:
    python agent/main.py --config ~/.rocket/config.yaml
    python agent/main.py --host 0.0.0.0 --port 8765
"""

from __future__ import annotations

import asyncio
import argparse
import os
import sys
from pathlib import Path

from agent.core.nova_stage0 import NovaStageZeroAgent
from agent.server.http_api import start_http_server, stop_http_server
from agent.server.websocket_handler import start_websocket_server
from agent.stage0.pairing import PairingManager
from agent.stage0.pipeline import validate_api_key
from agent.utils.config import load_config
from agent.utils.dependency_check import check_and_prepare_dependencies
from agent.utils.env import load_local_env
from agent.utils.logger import get_logger, setup_logging


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
        default="0.0.0.0",
        help="WebSocket server host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)",
    )
    parser.add_argument(
        "--http-port",
        type=int,
        default=8000,
        help="HTTP API server port (default: 8000)",
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
    load_local_env(Path.cwd())
    setup_logging("DEBUG" if args.debug else args.log_level)
    await check_and_prepare_dependencies()

    api_key = os.environ.get("POLLINATIONS_API_KEY")
    if not api_key:
        logger.error("POLLINATIONS_API_KEY is required in .env or the process environment")
        sys.exit(1)

    # Validate the API key at boot time
    validate_api_key(api_key)

    agent = None
    http_server = None

    try:
        config = load_config(args.config)
        config.host = args.host
        config.port = args.port
        config.data_dir.mkdir(parents=True, exist_ok=True)

        pairing = PairingManager(storage_dir=config.data_dir / "pairing", port=args.port)
        payload = pairing.load_or_create()
        pairing.print_qr(payload)
        logger.info(f"Pairing payload: ip={payload.ip} port={payload.port}")

        agent = NovaStageZeroAgent(config=config, api_key=api_key)
        logger.info("Nova Stage 0 backend ready")

        http_server = start_http_server(
            host=args.host,
            port=args.http_port,
        )

        await start_websocket_server(
            agent=agent,
            token=payload.token,
            host=args.host,
            port=args.port,
        )

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        stop_http_server(http_server)
        if agent is not None:
            await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
