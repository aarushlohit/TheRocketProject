import json

import pytest

from agent.server import websocket_handler


class DummyState:
    def __init__(self):
        self.client_id = "test-client"
        self.sent_messages = []

    async def send(self, message: dict):
        self.sent_messages.append(message)


class TripleTapAgent:
    def __init__(self):
        self.received_confirmation_ids = []

    def peek_pending_confirmation_id(self):
        return "pending-123"

    async def handle_confirmation_response(self, confirmation_id: str, confirmed: bool):
        self.received_confirmation_ids.append((confirmation_id, confirmed))
        return {
            "type": "result",
            "status": "success",
            "message": "Locking system",
        }


@pytest.mark.asyncio
async def test_triple_tap_confirm_uses_latest_pending_agent_confirmation(monkeypatch):
    monkeypatch.setattr(websocket_handler, "get_confirmation_manager", lambda: None)
    state = DummyState()
    agent = TripleTapAgent()

    await websocket_handler.handle_message(
        state=state,
        message=json.dumps({"type": "triple_tap_confirm"}),
        agent=agent,
        ws_callback=lambda message: message,
    )

    assert agent.received_confirmation_ids == [("pending-123", True)]
    assert state.sent_messages == [
        {"type": "result", "status": "success", "message": "Locking system"}
    ]


@pytest.mark.asyncio
async def test_triple_tap_confirm_uses_explicit_confirmation_id(monkeypatch):
    monkeypatch.setattr(websocket_handler, "get_confirmation_manager", lambda: None)
    state = DummyState()
    agent = TripleTapAgent()

    await websocket_handler.handle_message(
        state=state,
        message=json.dumps(
            {"type": "triple_tap_confirm", "confirmation_id": "confirm-456"}
        ),
        agent=agent,
        ws_callback=lambda message: message,
    )

    assert agent.received_confirmation_ids == [("confirm-456", True)]
