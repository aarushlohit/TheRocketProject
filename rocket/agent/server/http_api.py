"""Minimal HTTP API for mobile/backend synchronization.

Provides:
- POST /process  -> process and execute text input
- POST /confirm  -> confirm and execute pending dangerous action
- GET  /status   -> pending action status
"""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from agent.core.autonomous_os import classify_multi_step, get_processor, route_intent
from agent.utils.logger import get_logger


logger = get_logger(__name__)


class _ApiState:
    """In-memory API state for pending confirmations."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.pending_action: Optional[Dict[str, Any]] = None


_API_STATE = _ApiState()


def _build_pending_action(input_text: str, confirmation_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve an executable pending action from a confirmation payload."""

    original_intent = (
        confirmation_payload.get("original_intent")
        or confirmation_payload.get("slots", {}).get("original_intent")
    )
    original_slots = (
        confirmation_payload.get("original_slots")
        or confirmation_payload.get("slots", {}).get("original_slots", {})
    )

    if isinstance(original_intent, str) and original_intent and original_intent != "UNKNOWN":
        if not isinstance(original_slots, dict):
            original_slots = {}
        return {
            "intent": original_intent,
            "slots": original_slots,
            "confidence": 1.0,
        }

    classified = classify_multi_step(input_text)
    intent = classified.get("intent", "UNKNOWN")
    if intent in {"UNKNOWN", "CONFIRMATION_REQUIRED"}:
        return None

    return classified


class RocketApiHandler(BaseHTTPRequestHandler):
    """HTTP handler for process/confirm endpoints."""

    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/process":
            self._handle_process()
            return
        if self.path == "/confirm":
            self._handle_confirm()
            return

        self._send_json({"status": "error", "message": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/status":
            self._handle_status()
            return

        self._send_json({"status": "error", "message": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("[HTTP API] " + format % args)

    def _handle_process(self) -> None:
        body = self._read_json_body()
        if body is None:
            self._send_json(
                {"status": "error", "message": "Request body must be valid JSON"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        input_text = str(body.get("input", "")).strip()
        if not input_text:
            self._send_json(
                {"status": "error", "message": "Field 'input' is required"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        processor = get_processor()
        intent_data = processor.process(input_text)

        if intent_data.get("intent") == "CONFIRMATION_REQUIRED":
            pending_action = _build_pending_action(input_text, intent_data)
            confirmation_id = f"api-{uuid.uuid4().hex[:8]}"

            with _API_STATE.lock:
                _API_STATE.pending_action = pending_action

            action_preview = "dangerous action"
            if pending_action:
                action_preview = pending_action.get("intent", action_preview)

            response = {
                "status": "confirmation_required",
                "intent": "CONFIRMATION_REQUIRED",
                "message": "Confirmation required before execution",
                "confirmation_id": confirmation_id,
                "action": action_preview,
                "timeout": 30.0,
                "reason": intent_data.get("reason", "dangerous_operation"),
            }
            self._send_json(response, status=HTTPStatus.OK)
            return

        if intent_data.get("intent") not in {"MULTI_STEP", "UNKNOWN", "CONFIRMATION_REQUIRED"}:
            intent_data.setdefault("_route", route_intent(intent_data, input_text).value)

        execution_result = asyncio.run(processor.execute(intent_data))
        payload = execution_result.to_dict()
        payload.setdefault("intent", intent_data.get("intent", "UNKNOWN"))
        self._send_json(payload, status=HTTPStatus.OK)

    def _handle_confirm(self) -> None:
        processor = get_processor()

        with _API_STATE.lock:
            pending_action = _API_STATE.pending_action
            _API_STATE.pending_action = None

        if pending_action is None:
            pending_action = processor.confirm_dangerous_action()

        if pending_action is None:
            self._send_json(
                {
                    "status": "no_pending",
                    "intent": "UNKNOWN",
                    "message": "No pending confirmation",
                },
                status=HTTPStatus.OK,
            )
            return

        if pending_action.get("intent") not in {"MULTI_STEP", "UNKNOWN", "CONFIRMATION_REQUIRED"}:
            pending_action.setdefault("_route", route_intent(pending_action, "").value)

        execution_result = asyncio.run(processor.execute(pending_action))
        payload = execution_result.to_dict()
        payload["confirmed"] = True
        self._send_json(payload, status=HTTPStatus.OK)

    def _handle_status(self) -> None:
        processor = get_processor()

        with _API_STATE.lock:
            has_pending_api = _API_STATE.pending_action is not None

        has_pending_processor = processor.context.pending_confirmation is not None
        self._send_json(
            {
                "status": "ok",
                "has_pending_action": has_pending_api or has_pending_processor,
                "has_pending_api_action": has_pending_api,
                "has_pending_processor_action": has_pending_processor,
            },
            status=HTTPStatus.OK,
        )

    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None

        if length <= 0:
            return {}

        raw = self.rfile.read(length)
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

        if not isinstance(decoded, dict):
            return None

        return decoded

    def _send_json(self, payload: Dict[str, Any], status: HTTPStatus) -> None:
        body = json.dumps(payload).encode("utf-8")

        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_http_server(host: str = "0.0.0.0", port: int = 8000) -> ThreadingHTTPServer:
    """Start HTTP API server in a background thread."""

    server = ThreadingHTTPServer((host, port), RocketApiHandler)
    thread = threading.Thread(target=server.serve_forever, name="rocket-http-api", daemon=True)
    thread.start()

    logger.info(f"HTTP API server listening on http://{host}:{port}")
    print(f"[HTTP API] Listening on http://{host}:{port}")
    return server


def stop_http_server(server: Optional[ThreadingHTTPServer]) -> None:
    """Stop HTTP API server."""

    if server is None:
        return

    server.shutdown()
    server.server_close()
    logger.info("HTTP API server stopped")


__all__ = [
    "start_http_server",
    "stop_http_server",
]
