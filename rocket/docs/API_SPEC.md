# WebSocket API Specification

## Overview

Rocket uses **WebSocket** for real-time bidirectional communication between Mobile App and PC Agent.

**Connection Details**:
- Protocol: `ws://` or `wss://` (TLS recommended in production)
- Default URL: `ws://localhost:8765`
- Reconnection: Automatic exponential backoff (500ms → 30s)

---

## Message Format

All messages are **JSON** with required fields:

```json
{
  "id": "uuid",              // Unique message ID for tracking
  "type": "input|response|heartbeat|error",
  "timestamp": "ISO-8601",   // When message was created
  "payload": {               // Type-specific data
    ...
  }
}
```

---

## Message Types

### 1. Voice Input (Mobile → Agent)

User speaks, mobile sends transcription.

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "voice_input",
  "timestamp": "2025-01-15T10:30:00.123Z",
  "payload": {
    "text": "open chrome",
    "confidence": 0.95,
    "language": "en-US",
    "raw_audio_url": null,
    "user_id": "user123"
  }
}
```

**Fields**:
- `text`: Transcribed text from Whisper
- `confidence`: 0-1 confidence score from STT engine
- `language`: BCP-47 language tag
- `raw_audio_url`: Optional, for server-side re-processing
- `user_id`: For multi-user support (future)

**Agent Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "response",
  "timestamp": "2025-01-15T10:30:00.456Z",
  "payload": {
    "status": "success|executing|error|clarification_needed",
    "message": "Chrome opened",
    "action_id": "chrome-open-1234",
    "execution_time_ms": 234,
    "feedback": {
      "type": "audio|haptic|text",
      "content": "Chrome launched"
    }
  }
}
```

---

### 2. Drawing Input (Mobile → Agent)

User draws gesture, mobile sends coordinates.

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "type": "drawing_input",
  "timestamp": "2025-01-15T10:30:01.000Z",
  "payload": {
    "strokes": [
      {
        "points": [
          {"x": 100, "y": 200, "pressure": 0.8, "timestamp_ms": 0},
          {"x": 105, "y": 190, "pressure": 0.9, "timestamp_ms": 10},
          {"x": 110, "y": 180, "pressure": 0.85, "timestamp_ms": 20}
        ],
        "start_time": "2025-01-15T10:30:01.000Z",
        "end_time": "2025-01-15T10:30:01.100Z"
      }
    ],
    "canvas_dimensions": {"width": 1080, "height": 1920},
    "device": "stylus|finger",
    "user_id": "user123"
  }
}
```

**Fields**:
- `strokes`: Array of continuous touch/stylus movements
- `points`: Array of coordinates with pressure/time
- `canvas_dimensions`: Screen size for normalization
- `device`: Input device type
- `user_id`: User identifier

**Agent Response**:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "type": "response",
  "timestamp": "2025-01-15T10:30:01.234Z",
  "payload": {
    "status": "success|executing|error|unrecognized",
    "recognized_action": "scroll_up",
    "confidence": 0.87,
    "message": "Scrolled up 3 items",
    "action_id": "scroll-up-5678",
    "execution_time_ms": 145,
    "feedback": {
      "type": "haptic",
      "pattern": "double_tap"
    }
  }
}
```

---

### 3. Heartbeat (Bidirectional)

Keep connection alive, detect disconnection.

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "type": "heartbeat",
  "timestamp": "2025-01-15T10:30:05.000Z",
  "payload": {
    "sender": "mobile|agent",
    "sequence": 1
  }
}
```

**Interval**: Every 30 seconds
**Timeout**: No heartbeat in 60s → reconnect

---

### 4. Error Response (Agent → Mobile)

```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "type": "error",
  "timestamp": "2025-01-15T10:30:02.000Z",
  "payload": {
    "error_code": "SKILL_NOT_FOUND|INTENT_AMBIGUOUS|NETWORK_ERROR|TIMEOUT",
    "message": "Could not find skill handler for action 'delete_all_emails'",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "recoverable": true,
    "suggested_action": "Did you mean 'delete email'? Or be more specific."
  }
}
```

**Error Codes**:
- `SKILL_NOT_FOUND`: Intent has no registered skill
- `INTENT_AMBIGUOUS`: Multiple possible intents
- `INTENT_UNRECOGNIZED`: Cannot parse user input
- `SKILL_FAILED`: Skill execution error
- `NETWORK_ERROR`: Connection lost
- `TIMEOUT`: Operation took too long
- `PERMISSION_DENIED`: Skill needs OS permission
- `INVALID_STATE`: Cannot perform action in current state

---

### 5. Status Update (Agent → Mobile, Optional)

For long-running operations, send progress.

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "status_update",
  "timestamp": "2025-01-15T10:30:02.500Z",
  "payload": {
    "action_id": "chrome-open-1234",
    "status": "downloading|installing|launching|ready",
    "progress_percent": 75,
    "message": "Launching Chrome... (this may take a moment)",
    "eta_seconds": 5
  }
}
```

---

### 6. Configuration Update (Mobile → Agent, Optional Phase 1)

```json
{
  "id": "990e8400-e29b-41d4-a716-446655440004",
  "type": "config_update",
  "timestamp": "2025-01-15T10:30:03.000Z",
  "payload": {
    "key": "input_language",
    "value": "es-ES",
    "apply_to": "current_session|persistent"
  }
}
```

---

## Intent Format (Internal)

Used by agent internally, not directly in messages. Example of what agent derives from voice/drawing:

```json
{
  "action": "OPEN_APP",
  "parameters": {
    "app": "chrome"
  },
  "confidence": 0.95,
  "context": {
    "foreground_app": "desktop",
    "last_action": "none"
  }
}
```

---

## Complete Example: Voice Command

**User**: "Open Chrome and go to Google"

**1. Mobile captures and sends**:
```json
{
  "id": "a1b2c3d4",
  "type": "voice_input",
  "timestamp": "2025-01-15T10:30:00Z",
  "payload": {
    "text": "open chrome and go to google",
    "confidence": 0.92,
    "language": "en-US"
  }
}
```

**2. Agent parses intent**:
```
Intent 1: OPEN_APP (app=chrome)
Intent 2: OPEN_URL (url=google.com)
Sequential execution planned
```

**3. Agent executes sequentially**:
```
Step 1: Launch Chrome (250ms)
Step 2: Wait for window (500ms)
Step 3: Navigate to google.com (150ms)
Total: 900ms
```

**4. Agent sends feedback**:
```json
{
  "id": "a1b2c3d4",
  "type": "response",
  "timestamp": "2025-01-15T10:30:00.900Z",
  "payload": {
    "status": "success",
    "message": "Chrome opened and Google loaded",
    "action_id": "multi-action-5678",
    "execution_time_ms": 900,
    "feedback": {
      "type": "audio",
      "content": "Chrome and Google ready"
    }
  }
}
```

**5. Mobile provides feedback to user** (audio + haptic)

---

## Security & Validation

### Input Validation (Agent)

All agent-side validation:
```python
# Validate voice input
assert 0 <= confidence <= 1, "Confidence must be 0-1"
assert len(text) > 0 and len(text) < 500, "Text too short/long"
assert isinstance(text, str), "Text must be string"

# Validate drawing input
assert all(0 <= p["x"] <= canvas_width for p in points), "X out of bounds"
assert all(0 <= p["y"] <= canvas_height for p in points), "Y out of bounds"
assert 0 <= pressure <= 1, "Pressure must be 0-1"
```

### Message ID Tracking

- Mobile generates UUID for each input
- Agent echoes same UUID in response
- Allows matching responses to requests
- Prevents duplicate processing on reconnect

### TLS in Production

```
wss://example.com/ws  (TLS-encrypted)
Agent must validate certificate
Mobile must support pinning (optional)
```

---

## Latency Targets

| Step | Target | Notes |
|------|--------|-------|
| Voice input capture | 50ms | Local buffering |
| Transmission | 100ms | Network RTT |
| Agent NLU parsing | 200ms | Intent extraction |
| Skill execution | varies | Depends on action |
| Feedback transmission | 50ms | Back to mobile |
| **Total** | **< 800ms** | User-perceivable threshold |

---

## Future Enhancements (Phase 2+)

- [ ] Binary protocol for audio/video streams (currently JSON only)
- [ ] Skill chaining syntax in single message
- [ ] Context persistence (remember user preferences)
- [ ] Multi-agent federation (multiple PC agents)
- [ ] Event subscriptions (notify mobile of OS changes)
- [ ] Custom skill definitions sent from mobile
- [ ] Compression for bandwidth optimization

---

## Testing

### Unit Tests
```python
def test_voice_input_validation():
    msg = {"text": "hello", "confidence": 0.95, "language": "en-US"}
    assert validate_voice_input(msg) == True
    
def test_invalid_confidence():
    msg = {"text": "hello", "confidence": 1.5, "language": "en-US"}
    with pytest.raises(ValidationError):
        validate_voice_input(msg)
```

### Integration Tests
```python
def test_end_to_end_voice_command():
    mobile_ws = connect_to_agent()
    mobile_ws.send(voice_input_msg)
    response = mobile_ws.recv(timeout=2000)
    assert response["status"] == "success"
    mobile_ws.close()
```

---

## Debugging

### WebSocket Debugging Tools

- **Chrome DevTools**: chrome://inspect → WebSockets tab
- **wscat**: Command-line WebSocket client
- **Wireshark**: Packet-level inspection (if needed)

### Demo WebSocket Client

```bash
# Terminal 1: Start agent
python agent/main.py

# Terminal 2: Test with wscat
wscat -c ws://localhost:8765

# Send test message
> {"id":"test1","type":"voice_input","payload":{"text":"open chrome","confidence":0.95,"language":"en-US"}}
< {"id":"test1","type":"response",...}
```
