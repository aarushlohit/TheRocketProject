"""Rich terminal UI for Rocket Phase 1."""

from __future__ import annotations

from datetime import datetime
import sys

import qrcode
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent.pairing.manager import PairingPayload


class RocketTerminal:
    def __init__(self) -> None:
        self.console = Console()

    def show_startup(self, payload: PairingPayload) -> None:
        self.console.print(Panel.fit("RocketTerminal\nPhase 1 perception bridge", title="Rocket V3"))
        self.console.print(self._status_table(payload))
        self.console.print("Scan this QR code from Rocket mobile settings:\n")
        qr = qrcode.QRCode(border=1)
        qr.add_data(payload.to_json())
        self._print_qr(qr)

    def show_health(self, status: dict[str, str]) -> None:
        table = Table(title="API Health")
        table.add_column("Service")
        table.add_column("Status")
        for service, state in status.items():
            table.add_row(service, state)
        self.console.print(table)

    def connection_open(self, client_id: str) -> None:
        self.log(f"Connection established: {client_id}")

    def connection_closed(self, client_id: str) -> None:
        self.log(f"Connection lost: {client_id}")

    def received_task(self, client_id: str, source: str, task: str, latency_ms: int) -> None:
        table = Table(title="Received Task")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Client", client_id)
        table.add_row("Source", source)
        table.add_row("Latency", f"{latency_ms} ms")
        table.add_row("Task", task)
        self.console.print(table)

    def log(self, message: str) -> None:
        self.console.print(f"[dim]{_now()}[/dim] {message}")

    def error(self, message: str) -> None:
        self.console.print(f"[red]{_now()} {message}[/red]")

    @staticmethod
    def _status_table(payload: PairingPayload) -> Table:
        table = Table(title="Connection")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Device name", "RocketTerminal")
        table.add_row("IP", payload.ip)
        table.add_row("Websocket", f"ws://{payload.ip}:{payload.port}")
        table.add_row("Backend", "Nemotron primary, Pollinations fallback")
        table.add_row("Token", payload.token[:8] + "...")
        return table

    def _print_qr(self, qr: qrcode.QRCode) -> None:
        matrix = qr.get_matrix()
        if not matrix:
            return

        if self._supports_unicode_blocks():
            self._print_unicode_qr(matrix)
            return

        self._print_ascii_qr(matrix)

    @staticmethod
    def _supports_unicode_blocks() -> bool:
        encoding = (getattr(sys.stdout, "encoding", None) or "").lower()
        return "utf" in encoding

    def _print_unicode_qr(self, matrix: list[list[bool]]) -> None:
        padded = [([False] + row + [False]) for row in matrix]
        blank_row = [False] * len(padded[0])
        rows = [blank_row] + padded + [blank_row]
        if len(rows) % 2 != 0:
            rows.append(blank_row)

        for index in range(0, len(rows), 2):
            upper = rows[index]
            lower = rows[index + 1]
            rendered = "".join(self._unicode_qr_cell(top, bottom) for top, bottom in zip(upper, lower))
            self.console.print(rendered, soft_wrap=False, overflow="ignore", highlight=False)

    def _print_ascii_qr(self, matrix: list[list[bool]]) -> None:
        border = 1
        width = len(matrix[0])
        use_wide_cells = (width + border * 2) * 2 <= self.console.width
        filled = "##" if use_wide_cells else "#"
        blank = "  " if use_wide_cells else " "

        for _ in range(border):
            self.console.print(blank * (width + border * 2), soft_wrap=False, overflow="ignore", highlight=False)
        for row in matrix:
            rendered = blank * border + "".join(filled if cell else blank for cell in row) + blank * border
            self.console.print(rendered, soft_wrap=False, overflow="ignore", highlight=False)
            if not use_wide_cells:
                self.console.print(rendered, soft_wrap=False, overflow="ignore", highlight=False)
        for _ in range(border):
            self.console.print(blank * (width + border * 2), soft_wrap=False, overflow="ignore", highlight=False)

    @staticmethod
    def _unicode_qr_cell(top: bool, bottom: bool) -> str:
        if top and bottom:
            return "\u2588"
        if top:
            return "\u2580"
        if bottom:
            return "\u2584"
        return " "


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")
