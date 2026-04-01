# Skills System

A **skill** is a unit of automation that performs a single, well-defined action. Every user command is translated into one or more skills executed in sequence.

---

## Skill Anatomy

```python
class MySkill(BaseSkill):
    """One sentence describing what this skill does."""
    
    # Metadata
    NAME = "MY_SKILL"
    DESCRIPTION = "Detailed description of behavior and limitations."
    CATEGORY = "productivity|browser|system|accessibility"
    
    # Configuration
    SUPPORTED_PLATFORMS = ["windows", "macos", "linux"]
    REQUIRES_PERMISSIONS = ["screen_read", "keyboard_control"]
    COMPLEXITY = "simple|moderate|advanced"  # How hard for user to understand
    
    # NLU patterns that trigger this skill
    VOICE_PATTERNS = [
        r"open (?P<app>\w+)",
        r"launch (?P<app>\w+)",
    ]
    GESTURE_PATTERNS = ["upward_stroke", "circle"]
    
    async def execute(self, intent: Intent, context: ExecutionContext) -> Result:
        """Execute the skill. Must return Result."""
        pass
    
    def validate_parameters(self, intent: Intent) -> bool:
        """Check that intent has all required parameters."""
        pass
    
    def get_help(self) -> str:
        """Return usage help text."""
        pass
```

---

## Phase 0 Skills (MVP)

These are the **minimum viable skills** to demonstrate the system works.

### 1. OPEN_APP

**Description**: Open an application by name.

**Voice Patterns**:
```
"open chrome"
"launch vscode"
"start firefox"
"open spotify"
```

**Parameters**:
```json
{
  "app": "chrome|firefox|vscode|notepad|emacs|spotify|slack"
}
```

**Implementation**: Platform-specific app launchers
- Windows: `subprocess.Popen("start app_name")`
- macOS: `subprocess.Popen("open -a 'App Name'")`
- Linux: `subprocess.Popen("app_name")`

**Feedback**: "Chrome opened" (with haptic confirmation)

---

### 2. TYPE_TEXT

**Description**: Type text into the focused window.

**Voice Patterns**:
```
"type hello world"
"write my name is john"
"input password123"
```

**Parameters**:
```json
{
  "text": "string to type",
  "char_delay": 0.05  // Optional, seconds between chars
}
```

**Implementation**: 
```python
import pyautogui
pyautogui.typewrite(text, interval=char_delay)
```

**Safety**:
- ❌ No auto-execution of shell commands from text
- ❌ No special key sequences unless specified
- ✅ User can review before executing

**Feedback**: "Typed 'hello world'"

---

### 3. PRESS_KEYS

**Description**: Press keyboard shortcuts.

**Voice Patterns**:
```
"press control s"
"hit enter"
"do command z"  (macOS)
"escape"
"tab"
```

**Parameters**:
```json
{
  "keys": ["ctrl", "s"]  // Array of key names
}
```

**Supported Keys**:
```
ctrl, shift, alt, cmd, win
enter, escape, tab, backspace, delete
space, capslock
home, end, pageup, pagedown
left, right, up, down
f1-f12
a-z, 0-9, and symbols
```

**Implementation**: pyautogui.hotkey("ctrl", "s")

**Feedback**: "Pressed Ctrl+S"

---

### 4. SCROLL

**Description**: Scroll in a direction.

**Voice Patterns**:
```
"scroll up"
"scroll down"
"scroll left"
```

**Drawing Gestures**:
- Upward stroke → scroll up
- Downward stroke → scroll down
- Leftward stroke → scroll left
- Rightward stroke → scroll right

**Parameters**:
```json
{
  "direction": "up|down|left|right",
  "amount": 3  // Lines/pixels to scroll
}
```

**Implementation**:
- Windows: SendInput with wheel events
- macOS: PyObjC scroll events
- Linux: xdotool key Page_Up/Page_Down

**Feedback**: "Scrolled up 3 lines"

---

### 5. CLICK

**Description**: Click at screen coordinates.

**Voice Patterns**:
```
"click submit button"  // Future: Button detection
"click at 100 200"     // Coordinate-based
```

**Parameters**:
```json
{
  "x": 100,
  "y": 200,
  "button": "left|right|middle",
  "double_click": false  // Optional
}
```

**Implementation**: pyautogui.click(x, y)

**Accessibility Note**: 
- Coordinates hard for blind users → focus on semantic commands
- Phase 1+: Use OCR to identify buttons by text instead

**Feedback**: "Clicked at (100, 200)"

---

### 6. OPEN_URL

**Description**: Open URL in default browser.

**Voice Patterns**:
```
"go to google.com"
"open www.github.com"
"visit twitter"  // Inferred as twitter.com
```

**Parameters**:
```json
{
  "url": "https://google.com"
}
```

**Implementation**:
```python
import webbrowser
webbrowser.open(url)
```

**Smart Features**:
- Auto-prepend "https://" if needed
- Expand shortcuts ("google" → "google.com")
- Validate URL format

**Feedback**: "Opened Google.com in Chrome"

---

### 7. SELECT_TEXT

**Description**: Select text via multiple methods.

**Voice Patterns**:
```
"select all"
"select word"
"select line"
```

**Parameters**:
```json
{
  "mode": "all|word|line|paragraph|custom",
  "custom_regex": null  // For custom selection
}
```

**Implementation**:
```python
# Select all: Ctrl+A
# Select word: Ctrl+Shift+Left/Right
# Select line: Home, Shift+End
```

**Feedback**: "Selected 50 characters"

---

## Phase 1 Skills (After MVP)

### 8. SEARCH_WEB

Search Google/Bing for a query.

```
"search for python documentation"
"look up nearest coffee shop"
```

**Implementation**: Opens search engine + types query

---

### 9. READ_SCREEN

Read aloud text on screen using TTS.

```
"read this page"
"speak the paragraph"
```

**Implementation**: 
- Extract visible text (OCR or a11y tree)
- Use pyttsx3 or Google TTS
- With proper punctuation/pause handling

---

### 10. TAKE_SCREENSHOT

Capture screen to file.

```
"take a screenshot"
"capture screen"
```

**Implementation**: 
- PIL Image capture
- Save to ~/Downloads/rocket_screenshot_*.png
- Voice confirmation with file path

---

### 11. SMART_CLICK_BY_TEXT

Click buttons/elements by text content.

```
"click submit button"
"click the 'More' link"
```

**Implementation**:
- Use OCR to detect text on screen
- Find bounding box
- Click center of box

**Is this accessible?** Better than coordinates, but still screen-dependent.

---

### 12. ACTIVATE_APP

Switch to already-open app.

```
"switch to chrome"
"go to vscode"
"focus spotify"
```

**Implementation**:
- List open windows
- Find by app name
- Alt+Tab or platform-specific window switching

---

## Phase 2+ Future Skills

- **Email operations**: SEND_EMAIL, REPLY_EMAIL, CHECK_INBOX
- **File operations**: CREATE_FILE, OPEN_FILE, DELETE_FILE
- **Calendar**: SCHEDULE_MEETING, CHECK_SCHEDULE
- **Code execution**: RUN_COMMAND, EXECUTE_PYTHON, COMPILE_CODE
- **Media control**: PLAY_MUSIC, PAUSE, VOLUME, SEEK
- **Window management**: MINIMIZE, MAXIMIZE, TILE_WINDOWS
- **Network**: DOWNLOAD_FILE, UPLOAD_FILE, PING
- **System**: SHUTDOWN, RESTART, SLEEP, LOCK_SCREEN
- **Accessibility**: INCREASE_TEXT_SIZE, CHANGE_COLORS, ENABLE_READER

---

## Skill Discovery & Registration

### Auto-Registration

Placing a skill in `skills/` directory auto-registers it:

```python
# skills/skill_open_app.py
from agent.skills.base import BaseSkill

class OpenAppSkill(BaseSkill):
    NAME = "OPEN_APP"
    # ...

# Agent automatically discovers and registers
agent.skill_registry.auto_register("skills/")
```

### Manual Registration (if needed)

```python
agent.skill_registry.register("OPEN_APP", OpenAppSkill)
```

### Skill Metadata API

```python
# List all skills
agent.skill_registry.list_skills()
# ["OPEN_APP", "TYPE_TEXT", "SCROLL", ...]

# Get skill help
skill = agent.skill_registry.get_skill("OPEN_APP")
print(skill.get_help())
# "Open an app. Usage: 'open [app_name]'. Supported: chrome, firefox, vscode, ..."

# Get skill complexity
print(skill.COMPLEXITY)  # "simple"
```

---

## Testing Skills

### Unit Test Template

```python
import pytest
from agent.skills.skill_open_app import OpenAppSkill
from agent.core.intent import Intent
from agent.core.context import ExecutionContext
from agent.platform.adapter import MockPlatformAdapter

@pytest.fixture
def skill():
    adapter = MockPlatformAdapter()
    return OpenAppSkill(adapter)

@pytest.mark.asyncio
async def test_open_app_success(skill):
    intent = Intent(action="OPEN_APP", parameters={"app": "chrome"}, confidence=0.95)
    result = await skill.execute(intent, ExecutionContext())
    assert result.status == "success"
    assert "Chrome" in result.message

@pytest.mark.asyncio
async def test_open_unsupported_app(skill):
    intent = Intent(action="OPEN_APP", parameters={"app": "unknown_app"}, confidence=0.95)
    result = await skill.execute(intent, ExecutionContext())
    assert result.status == "error"

@pytest.mark.asyncio
async def test_open_app_missing_parameters(skill):
    intent = Intent(action="OPEN_APP", parameters={}, confidence=0.95)
    assert not skill.validate_parameters(intent)
```

---

## Skill Best Practices

1. **One responsibility per skill**: Don't mix unrelated behaviors
2. **Explicit parameters**: No magic parameter inference
3. **Clear error messages**: Tell user what went wrong and how to fix
4. **Accessibility-first**: Avoid visual/audio-only feedback
5. **Graceful degradation**: Work without advanced OS features if possible
6. **Testable**: All skills must work with mocked platform adapter
7. **Documented**: Usage examples, parameters, limitations
8. **Logged**: All executions logged with timing
9. **Recoverable**: Return specific errors, not generic "failed"
10. **Quick feedback**: Respond within 200ms even if background work continues

---

## Skill Failure Recovery

When a skill fails:

1. **Immediate feedback**: "Failed to open Chrome"
2. **Root cause**: "Error: App not installed"
3. **Suggestion**: "Please install Chrome, then try again"
4. **Logging**: Full error + stacktrace in logs

```python
try:
    await self.adapter.open_app("chrome")
except AppNotFoundError as e:
    return Result(
        status="error",
        message="Failed to open Chrome",
        data={"error_code": "APP_NOT_FOUND", "suggestion": "Install Chrome first"}
    )
except Exception as e:
    logger.exception("Unexpected error")
    return Result(
        status="error",
        message="Internal error opening Chrome",
        data={"error": str(e)}
    )
```

---

## Custom Skills (User-Created)

In Phase 2+, users can write custom skills:

```python
# ~/.rocket/skills/my_custom_skill.py
from agent.skills.base import BaseSkill

class MyCustomSkill(BaseSkill):
    NAME = "MY_CUSTOM_ACTION"
    DESCRIPTION = "Do something custom"
    
    async def execute(self, intent: Intent, context: ExecutionContext):
        # Custom implementation
        return Result(status="success", message="Done")
```

Agent automatically loads from `~/.rocket/skills/`.

---

## Summary: Phase 0 Skills

| Skill | Priority | Estimated Effort | Accessibility |
|-------|----------|------------------|-----------------|
| OPEN_APP | P0 | 2 hours | ✅ Excellent |
| TYPE_TEXT | P0 | 2 hours | ✅ Excellent |
| PRESS_KEYS | P0 | 1 hour | ✅ Excellent |
| SCROLL | P0 | 2 hours | ✅ Good |
| CLICK | P0 | 1 hour | ⚠️ Fair (coordinate-based) |
| OPEN_URL | P0 | 1 hour | ✅ Good |
| SELECT_TEXT | P1 | 2 hours | ✅ Excellent |

**Total for MVP**: ~11 hours of skill development
