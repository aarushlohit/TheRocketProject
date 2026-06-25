"""Rocket Phase 1 terminal entry point."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional
import webbrowser

import typer

from agent.adapters.nemotron import NemotronAdapter
from agent.adapters.pollinations import PollinationsAdapter
from agent.runtime import RocketAdapter, RuntimeTerminalBridge, rocket_bootstrap
from agent.pairing.manager import PairingManager, PairingPayload
from agent.server.websocket_handler import RocketWebSocketServer, pick_available_port
from agent.server.dashboard_http import DashboardState, serve_dashboard
from agent.terminal.rocket_terminal import RocketTerminal
from agent.utils.config import load_config
from agent.utils.env import load_local_env
from agent.utils.logger import setup_logging


app = typer.Typer(help="RocketTerminal: Phase 1 perception bridge.")


@app.command()
def terminal(
    host: str = typer.Option("0.0.0.0", help="Websocket host."),
    port: int = typer.Option(8765, help="Websocket port."),
    dashboard_port: int = typer.Option(8790, help="Dashboard HTTP port."),
    dashboard_root: Optional[Path] = typer.Option(None, help="Optional Flutter web dashboard root."),
    open_dashboard: bool = typer.Option(False, help="Open dashboard in the default browser."),
    config: Optional[Path] = typer.Option(None, help="Optional config file."),
    log_level: str = typer.Option("INFO", help="DEBUG, INFO, WARNING, ERROR."),
) -> None:
    """Run RocketTerminal."""

    load_local_env(Path.cwd())
    setup_logging(log_level)
    rocket_config = load_config(config)
    rocket_config.host = host
    rocket_config.port = port
    rocket_config.data_dir.mkdir(parents=True, exist_ok=True)

    resolved_port = pick_available_port(host, port)
    if resolved_port != port:
        print(f"[RocketTerminal] Port {port} is busy, using {resolved_port} instead.")

    terminal_ui = RocketTerminal()
    did_bootstrap = rocket_bootstrap(rocket_config.data_dir, non_interactive=True, workspace_root=Path.cwd())
    if did_bootstrap:
        terminal_ui.log("Rocket Bootstrap complete.")

    runtime_adapter = RocketAdapter(repo_root=Path.cwd(), data_dir=rocket_config.data_dir)
    terminal_bridge = RuntimeTerminalBridge(terminal_ui, runtime_adapter)

    pairing = PairingManager(storage_dir=rocket_config.data_dir / "pairing", port=resolved_port)
    payload = pairing.load_or_create()

    adapter = NemotronAdapter(
        fallback=PollinationsAdapter(model="mistral-small-3.2"),
    )
    server = RocketWebSocketServer(
        adapter=adapter,
        terminal=terminal_bridge,
        token=payload.token,
        host=host,
        port=resolved_port,
    )

    terminal_ui.show_startup(payload)
    resolved_dashboard_root = dashboard_root or _bundled_dashboard_root()
    try:
        asyncio.run(
            _run_servers(
                websocket_server=server,
                dashboard_root=resolved_dashboard_root,
                pairing=payload,
                websocket_port=resolved_port,
                dashboard_port=dashboard_port,
                open_dashboard=open_dashboard or bool(os.getenv("ROCKET_OPEN_DASHBOARD")),
            )
        )
    except KeyboardInterrupt:
        terminal_ui.log("Shutdown requested.")


async def _run_servers(
    websocket_server: RocketWebSocketServer,
    dashboard_root: Path | None,
    pairing: PairingPayload,
    websocket_port: int,
    dashboard_port: int,
    open_dashboard: bool,
) -> None:
    tasks = [asyncio.create_task(websocket_server.serve_forever())]
    if dashboard_root is not None and dashboard_root.exists():
        state = DashboardState(web_root=dashboard_root, pairing=pairing, websocket_port=websocket_port, port=dashboard_port)
        tasks.append(asyncio.create_task(serve_dashboard(state)))
        if open_dashboard:
            webbrowser.open(f"http://127.0.0.1:{dashboard_port}")
    await asyncio.gather(*tasks)


def _bundled_dashboard_root() -> Path | None:
    bundle_dir = os.getenv("ROCKET_APP_BUNDLE_DIR", "").strip()
    if not bundle_dir:
        return None
    return Path(bundle_dir) / "dashboard"


if __name__ == "__main__":
    app()
