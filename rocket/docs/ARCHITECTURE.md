# Rocket System Architecture

## Overview

Rocket is a **hybrid client-server automation system** where:
- **AI decides WHAT to do** (intent parsing, planning)
- **Rocket decides HOW to do it** (skill selection, execution, error handling)

```
User Input (Voice/Drawing)
    ↓
Mobile App (Flutter)
    ├─ Input capture
    ├─ Local preprocessing
    └─ Send to PC Agent
         ↓
    WebSocket (JSON commands)
         ↓
    PC Agent (Python)
    ├─ Intent parsing
    ├─ Skill routing
    ├─ Execution
    └─ Platform adapters
         ↓
    OS/Python libraries
         ↓
    Action on computer
```

---

## Architecture Layers

### 1. Input Layer (Mobile App - Flutter)

**Responsibility**: Capture, preprocess, send input to agent.

**Components**:
- **Voice input recorder**: Streams audio to Whisper (local or cloud)
- **Drawing input**: Captures touch/stylus strokes, sends raw coordinates
- **Input preprocessor**: Normalizes formats, filters noise
- **WebSocket client**: Maintains connection to PC Agent
- **Feedback renderer**: Haptic/audio confirmation for user

**Design Decisions**:
- ✅ **Local inference preferred**: Whisper runs on-device if possible (Flutter native plugin)
- ✅ **Fallback to cloud**: For devices without GPU, fall back to cloud Whisper API
- ✅ **Raw data transmission**: Send OCR input (drawing), audio vectors (voice) NOT interpreted commands
  - Let server decide intents
  - Mobile is stateless

**Data Flow**:
```
voice_input → Whisper → text transcription
drawing_input → preprocessing → [x, y, pressure, time] coordinates
both → normalize → JSON command → WebSocket → PC Agent
```

---

### 2. Command Transport Layer (WebSocket)

**Responsibility**: Reliable, low-latency communication between mobile and agent.

**Protocol**:
- JSON format
- Binary support for audio/drawing streams
- Heartbeat/keepalive messages
- Automatic reconnection with exponential backoff

**Message Categories**:
- **Input commands** (from mobile)
  ```json
  {
    "type": "voice_input",
    "transcription": "open chrome",
    "confidence": 0.95
  }
  ```
- **Draw commands** (from mobile)
  ```json
  {
    "type": "drawing_input",
    "strokes": [[x1,y1,p,t], [x2,y2,p,t], ...],
    "recognized_action": null
  }
  ```
- **Response/feedback** (from agent)
  ```json
  {
    "status": "success|error|executing",
    "message": "Chrome opened",
    "action_id": "uuid"
  }
  ```

See **API_SPEC.md** for full protocol.

---

### 3. Parsing & Intent Layer (PC Agent)

**Responsibility**: Convert raw input (text, drawing) into structured intent.

**Components**:
- **NLU module**: Parses voice transcription into intent
  - Example: "open chrome" → `{"action": "OPEN_APP", "app": "chrome"}`
- **Drawing recognizer**: Interprets gesture drawings
  - Example: upward stroke → `{"action": "SCROLL", "direction": "up"}`
- **Context manager**: Remembers last action, foreground window, etc.
- **Ambiguity resolver**: When intent is unclear, asks user for clarification

**Design Decisions**:
- ✅ **Rule-based NLU initially**: No heavy ML models on agent
- ✅ **Extensible intent registry**: New intents registered by skills
- ✅ **Graceful degradation**: If intent unclear, ask user instead of guessing

**NLU Flow**:
```
"open spotify and play my liked songs"
    ↓
Tokenize: [open] [spotify] [and] [play] [my] [liked] [songs]
    ↓
Entity recognition: app=spotify, action=play, playlist=liked_songs
    ↓
Intent resolution: [OPEN_APP(spotify), PLAY_PLAYLIST(liked_songs)]
    ↓
Execution plan: {skill: spotify_skill, steps: [...]}
```

---

### 4. Skill & Execution Layer (PC Agent)

**Responsibility**: Execute the parsed intent using registered skills.

**Components**:
- **Skill registry**: Maps intents to skill handlers
- **Skill executor**: Runs skills with error handling
- **Platform adapter**: Abstraction for OS-specific commands
- **State manager**: Tracks automation state (windows open, focus, etc.)

**Skill Structure**:
```python
class Skill:
    def __init__(self):
        self.name = "OPEN_APP"
        self.intents = ["open_app"]
        self.supported_apps = ["chrome", "firefox", ...]
    
    def execute(self, intent: Intent) -> Result:
        """Execute the skill, return Result with status"""
        return Result(status="success", data={...})
```

**Execution Pipeline**:
```
Parsed Intent
    ↓
Route to appropriate skill
    ↓
Pre-execute hooks (validation, permissions)
    ↓
Execute skill.execute()
    ↓
Post-execute hooks (state update, feedback)
    ↓
Return result to user
```

---

### 5. Platform Adaptation Layer

**Responsibility**: Abstract away OS-specific implementation details.

**Design**:
```
Platform Adapter Interface
    ├─ Windows implementation (pyautogui, win32api)
    ├─ macOS implementation (AppKit, Quartz)
    └─ Linux implementation (xdotool, python-xlib)
```

**Abstraction Examples**:
```python
# Instead of:
import pyautogui
pyautogui.click(100, 200)

# We do:
adapter = get_platform_adapter()
adapter.click(100, 200)
```

This allows:
- ✅ Single skill codebase on all platforms
- ✅ Easy switching between implementations
- ✅ Testing with mocked adapter

---

## Data Flow Examples

### Example 1: Voice Command
```
User speaks: "Go to google.com"
    ↓
Mobile records audio, sends to Whisper
    ↓
Transcription received: "go to google.com"
    ↓
PC Agent NLU: intent=OPEN_URL, url="google.com"
    ↓
Route to browser_skill.open_url("google.com")
    ↓
Skill executes:
  - Focus existing browser or launch new
  - Press Ctrl+L (address bar)
  - Type "google.com"
  - Press Enter
    ↓
Agent sends feedback: "Google.com opened"
    ↓
Mobile plays confirmation sound
```

### Example 2: Drawing Command
```
User draws upward stroke on mobile
    ↓
Mobile captures coordinates: [(x1,y1), (x2,y2), ...]
    ↓
Send to PC Agent with raw data
    ↓
Drawing recognizer identifies: gesture="scroll_up"
    ↓
NLU converts to intent: action=SCROLL, direction=UP
    ↓
Route to scroll_skill.scroll(direction="up", distance=3)
    ↓
Skill executes window scroll
    ↓
Status feedback sent back: "Scrolled up 3 lines"
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Client-server architecture** | Allows mobile to be stateless, agent handles complexity |
| **WebSocket over REST** | Lower latency, better for real-time feedback |
| **JSON command format** | Human-readable, debuggable, polyglot |
| **Skill-based execution** | Modular, extensible, testable |
| **Local preprocessing** | Privacy-first, works offline, faster feedback |
| **Rule-based NLU initially** | Fast, predictable, no dependency on heavy ML |
| **Platform adapters** | Multi-OS support without code duplication |
| **Stateless mobile** | Simple, no sync issues, easier testing |

---

## Future Architectural Evolution

### Phase 2: Distributed Skills
- Skills can run on different machines (home automation, cloud services)
- Agent becomes a router/orchestrator

### Phase 3: Learned Skills
- System learns new patterns from user behavior
- ML models train locally on user's automation patterns

### Phase 4: Cross-Device Sync
- State synchronized across devices
- Automation continues on mobile if PC unavailable

### Phase 5: Multi-Agent Coordination
- Multiple agents coordinate (home automation, mobile, desktop)
- Smart delegation of tasks

---

## Error Handling & Recovery

**Principle**: When automation fails, tell user immediately and suggest recovery.

**Levels**:
1. **Skill execution fails**: Return error, suggest alternatives
2. **Network disconnection**: Queues commands locally, retries on reconnect
3. **Ambiguous intent**: Ask user for clarification immediately
4. **Silent failure prevention**: All operations send confirmation

**Recovery Examples**:
```
Goal: Open Chrome
Step 1: Check if Chrome is installed → ✅
Step 2: Launch Chrome → ✅
Step 3: Wait for window (timeout 5s) → ❌ FAILED
Response: "Chrome didn't launch. Please check if installed."
```

---

## Security & Privacy Considerations

- **Local processing first**: No uploading user actions unless explicitly needed
- **No telemetry by default**: User data stays on device
- **Encrypted communication**: TLS for mobile-agent WebSocket
- **Permission model**: Skills declare what OS permissions they need
- **Audit log**: Local log of all executed commands for user review

---

## Testing Architecture

```
Unit Tests
├─ Skill tests (mock adapter)
├─ NLU tests (intent parsing)
└─ Adapter tests (OS-specific)

Integration Tests
├─ Skill + adapter
├─ Mobile + agent communication
└─ Full pipeline tests

E2E Tests
├─ Real mobile app + real agent
├─ Real OS interaction
└─ Accessibility validation
```

---

## Deployment Model

- **Mobile**: Distributed via Google Play, Apple App Store
- **Agent**: Pip package, or standalone executable
- **Models**: Downloaded on first run (Whisper, OCR models)
- **Configuration**: YAML file in user home directory
- **Logs**: Accessible to user for debugging
