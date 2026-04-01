# PC Agent Design

## Overview

The PC Agent is the **brain** of Rocket. It runs on the user's desktop, listens to mobile commands via WebSocket, parses intent, routes to skills, and executes OS automation.

```
Mobile App → WebSocket → PC Agent → Skills → OS Actions
```

---

## Agent Architecture

```python
agent/
├── main.py                    # Entry point, server initialization
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── agent.py              # Main Agent class
│   ├── intent.py             # Intent data structures
│   ├── result.py             # Result/feedback structures
│   ├── context.py            # Execution context (state)
│   └── exceptions.py         # Custom exceptions
├── skills/
│   ├── __init__.py
│   ├── base.py               # BaseSkill abstract class
│   ├── registry.py           # Skill registration/discovery
│   ├── skill_open_app.py     # Concrete skill implementations
│   ├── skill_type_text.py
│   ├── skill_open_url.py
│   ├── skill_scroll.py
│   └── skill_*.py            # Future skills
├── nlu/
│   ├── __init__.py
│   ├── parser.py             # NLU engine
│   ├── rules.py              # Intent rules
│   ├── entities.py           # Entity extractors
│   └── gesture_recognizer.py # Drawing gesture recognition
├── platform/
│   ├── __init__.py
│   ├── adapter.py            # Abstract platform adapter
│   ├── windows.py            # Windows implementation
│   ├── macos.py              # macOS implementation
│   └── linux.py              # Linux implementation
├── server/
│   ├── __init__.py
│   ├── websocket_handler.py  # WebSocket message handling
│   ├── message_queue.py      # Async message queue
│   └── authenticator.py      # Connection validation (Phase 1)
├── utils/
│   ├── __init__.py
│   ├── logger.py             # Logging setup
│   ├── config.py             # Configuration loading
│   └── metrics.py            # Metrics collection
└── tests/                    # Unit/integration tests
    ├── test_*.py
    └── fixtures/
```

---

## Core Components

### 1. Agent Class (core/agent.py)

Main orchestrator that ties everything together.

```python
class Agent:
    """Main automation agent."""
    
    def __init__(self, config: Config):
        self.config = config
        self.platform = self._init_platform()
        self.nlu = NLUEngine(self.platform)
        self.skill_registry = SkillRegistry()
        self.context = ExecutionContext()
        self.logger = get_logger(__name__)
    
    async def handle_voice_input(self, text: str) -> Result:
        """Process voice transcription."""
        intent = self.nlu.parse(text, context=self.context)
        return await self.execute_intent(intent)
    
    async def handle_drawing_input(self, strokes: List[Stroke]) -> Result:
        """Process drawing gesture."""
        intent = self.nlu.recognize_gesture(strokes)
        return await self.execute_intent(intent)
    
    async def execute_intent(self, intent: Intent) -> Result:
        """Route intent to appropriate skill and execute."""
        try:
            skill = self.skill_registry.get_skill(intent.action)
            result = await skill.execute(intent, context=self.context)
            self.context.record_action(intent, result)
            return result
        except SkillNotFoundError:
            return Result(status="error", message=f"Unknown action: {intent.action}")
        except Exception as e:
            self.logger.error(f"Skill execution failed: {e}")
            return Result(status="error", message=str(e))
    
    async def start(self):
        """Start WebSocket server."""
        self.logger.info(f"Starting agent on {self.config.host}:{self.config.port}")
        async with websockets.serve(handle_connection, self.config.host, self.config.port):
            await asyncio.Event().wait()
```

---

### 2. Intent Structure (core/intent.py)

```python
@dataclass
class Intent:
    """Parsed user intent ready for execution."""
    
    action: str                      # e.g., "OPEN_APP", "TYPE_TEXT"
    parameters: Dict[str, Any]       # Action-specific params
    confidence: float                # 0-1 confidence score
    context: Optional[Dict] = None   # Execution context
    metadata: Optional[Dict] = None  # Timing, source, etc.
    
    def validate(self) -> bool:
        """Check intent is well-formed."""
        assert self.action, "Intent must have action"
        assert 0 <= self.confidence <= 1
        return True
```

---

### 3. BaseSkill (skills/base.py)

Abstract base class all skills inherit from.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class Result:
    """Skill execution result."""
    status: str                 # "success", "error", "executing"
    message: str                # User-facing message
    data: Dict[str, Any] = None # Execution-specific data
    duration_ms: float = 0      # Execution time
    feedback: Dict = None       # Haptic/audio feedback

class BaseSkill(ABC):
    """Base class for all skills."""
    
    def __init__(self, name: str, adapter: PlatformAdapter):
        self.name = name
        self.adapter = adapter
        self.logger = get_logger(self.name)
    
    @abstractmethod
    async def execute(self, intent: Intent, context: ExecutionContext) -> Result:
        """Execute the skill."""
        pass
    
    def validate_parameters(self, intent: Intent) -> bool:
        """Validate intent parameters before execution."""
        pass
    
    def get_help(self) -> str:
        """Return usage help text."""
        pass
```

---

### 4. Concrete Skills Examples

#### OpenAppSkill (skills/skill_open_app.py)

```python
class OpenAppSkill(BaseSkill):
    """Open an application."""
    
    SUPPORTED_APPS = [
        "chrome", "firefox", "vscode", "notepad", 
        "spotify", "slack", "excel", "word"
    ]
    
    def __init__(self, adapter: PlatformAdapter):
        super().__init__("OPEN_APP", adapter)
    
    async def execute(self, intent: Intent, context: ExecutionContext) -> Result:
        """Open application by name."""
        app = intent.parameters.get("app")
        if not app:
            return Result(status="error", message="No app specified")
        
        app = app.lower()
        if app not in self.SUPPORTED_APPS:
            return Result(
                status="error", 
                message=f"App '{app}' not in supported list: {self.SUPPORTED_APPS}"
            )
        
        try:
            start_time = time.time()
            await self.adapter.open_app(app)
            duration = (time.time() - start_time) * 1000
            
            return Result(
                status="success",
                message=f"{app.capitalize()} opened",
                duration_ms=duration,
                feedback={"type": "haptic", "pattern": "success"}
            )
        except Exception as e:
            return Result(status="error", message=f"Failed to open {app}: {str(e)}")
    
    def validate_parameters(self, intent: Intent) -> bool:
        return "app" in intent.parameters
    
    def get_help(self) -> str:
        return f"Open an app. Usage: 'open [app_name]'. Supported: {', '.join(self.SUPPORTED_APPS)}"
```

#### TypeTextSkill (skills/skill_type_text.py)

```python
class TypeTextSkill(BaseSkill):
    """Type text into focused window."""
    
    def __init__(self, adapter: PlatformAdapter):
        super().__init__("TYPE_TEXT", adapter)
    
    async def execute(self, intent: Intent, context: ExecutionContext) -> Result:
        text = intent.parameters.get("text")
        if not text:
            return Result(status="error", message="No text specified")
        
        try:
            # Type with configurable delay between characters
            delay = intent.parameters.get("char_delay", 0.05)
            await self.adapter.type_text(text, delay=delay)
            
            return Result(
                status="success",
                message=f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}",
                duration_ms=len(text) * delay * 1000
            )
        except Exception as e:
            return Result(status="error", message=f"Failed to type: {str(e)}")
```

---

### 5. Skill Registry (skills/registry.py)

```python
class SkillRegistry:
    """Registry for available skills."""
    
    def __init__(self):
        self.skills: Dict[str, Type[BaseSkill]] = {}
        self.instances: Dict[str, BaseSkill] = {}
        self.logger = get_logger(__name__)
    
    def register(self, action: str, skill_class: Type[BaseSkill]):
        """Register a skill class."""
        self.skills[action] = skill_class
        self.logger.info(f"Registered skill: {action}")
    
    def get_skill(self, action: str, adapter: PlatformAdapter) -> BaseSkill:
        """Get or instantiate a skill."""
        if action in self.instances:
            return self.instances[action]
        
        if action not in self.skills:
            raise SkillNotFoundError(f"No skill for action: {action}")
        
        skill = self.skills[action](adapter)
        self.instances[action] = skill
        return skill
    
    def list_skills(self) -> List[str]:
        """List all registered skill names."""
        return list(self.skills.keys())
    
    def auto_register(self, skills_dir: str):
        """Auto-import and register all skills in directory."""
        # Dynamically import all skill_*.py modules
        # Each module registers itself via register()
```

---

### 6. NLU Engine (nlu/parser.py)

```python
class NLUEngine:
    """Natural Language Understanding for intent parsing."""
    
    def __init__(self, platform: PlatformAdapter):
        self.platform = platform
        self.rules = IntentRules()
        self.gesture_recognizer = GestureRecognizer()
    
    def parse(self, text: str, context: ExecutionContext) -> Intent:
        """Parse voice text into intent."""
        text = text.lower().strip()
        
        # Try to match against registered rules
        for action, pattern in self.rules.patterns.items():
            match = pattern.match(text)
            if match:
                parameters = self._extract_parameters(action, match, text)
                return Intent(
                    action=action,
                    parameters=parameters,
                    confidence=0.95  # High confidence for rule-based match
                )
        
        # If no match, return error intent
        return Intent(
            action="CLARIFY",
            parameters={"question": f"Did you mean to '{text}'? Please rephrase."},
            confidence=0.5
        )
    
    def recognize_gesture(self, strokes: List[Stroke]) -> Intent:
        """Recognize drawn gesture into intent."""
        gesture = self.gesture_recognizer.recognize(strokes)
        
        gesture_to_action = {
            "scroll_up": "SCROLL",
            "scroll_down": "SCROLL",
            "go_back": "NAVIGATE",
            "go_forward": "NAVIGATE",
            "select_all": "SELECT",
        }
        
        action = gesture_to_action.get(gesture, "UNKNOWN_GESTURE")
        return Intent(
            action=action,
            parameters={"gesture": gesture},
            confidence=0.85
        )
    
    def _extract_parameters(self, action: str, match, text: str) -> Dict:
        """Extract parameters from matched pattern."""
        # Implementation depends on pattern type
        if action == "OPEN_APP":
            return {"app": match.group("app")}
        elif action == "TYPE_TEXT":
            return {"text": match.group("text")}
        # ... more parameter extraction
        return {}
```

---

### 7. Platform Adapter (platform/adapter.py)

```python
class PlatformAdapter(ABC):
    """Abstract interface for OS-specific operations."""
    
    @abstractmethod
    async def open_app(self, app_name: str):
        """Launch application."""
        pass
    
    @abstractmethod
    async def type_text(self, text: str, delay: float = 0.05):
        """Type text into focused window."""
        pass
    
    @abstractmethod
    async def click(self, x: int, y: int, button: str = "left"):
        """Mouse click at coordinates."""
        pass
    
    @abstractmethod
    async def screenshot(self) -> bytes:
        """Capture screen."""
        pass
    
    @abstractmethod
    async def get_focused_window(self) -> Dict[str, Any]:
        """Get current foreground window."""
        pass
    
    @abstractmethod
    async def scroll(self, direction: str, amount: int):
        """Scroll in direction."""
        pass

# Platform-specific implementations
class WindowsAdapter(PlatformAdapter):
    async def open_app(self, app_name: str):
        import subprocess
        subprocess.Popen(f"start {app_name}", shell=True)
    # ... etc

class MacOSAdapter(PlatformAdapter):
    async def open_app(self, app_name: str):
        import subprocess
        subprocess.Popen(f"open -a '{app_name}'")
    # ... etc

class LinuxAdapter(PlatformAdapter):
    async def open_app(self, app_name: str):
        import subprocess
        subprocess.Popen(f"{app_name}")
    # ... etc
```

---

### 8. Execution Context (core/context.py)

```python
class ExecutionContext:
    """Track state during automation execution."""
    
    def __init__(self):
        self.foreground_app = None
        self.action_history: List[Tuple[Intent, Result]] = []
        self.clipboard_content = None
        self.user_preferences = {}
    
    def record_action(self, intent: Intent, result: Result):
        """Record execution for context awareness."""
        self.action_history.append((intent, result))
        self.foreground_app = self._get_foreground_app()
    
    def get_last_action(self) -> Optional[Intent]:
        """Get previous action for context."""
        return self.action_history[-1][0] if self.action_history else None
    
    def get_last_result(self) -> Optional[Result]:
        """Get result of previous action."""
        return self.action_history[-1][1] if self.action_history else None
```

---

## Execution Pipeline

```
1. User Input (voice/drawing)
    ↓
2. WebSocket server receives message
    ↓
3. Parse message, extract text/coordinates
    ↓
4. Call agent.handle_voice_input() or agent.handle_drawing_input()
    ↓
5. NLU engine parses → Intent
    ↓
6. Skill registry looks up skill
    ↓
7. Skill.execute(intent, context)
    ↓
8. Platform adapter performs OS action
    ↓
9. Return Result to WebSocket
    ↓
10. Send feedback to mobile (audio/haptic)
```

---

## Error Handling

```python
# Skill can raise, agent catches and converts to Result
try:
    result = await skill.execute(intent, context)
except SkillNotFoundError as e:
    result = Result(status="error", message=f"Skill not found: {intent.action}")
except SkillExecutionError as e:
    result = Result(status="error", message=f"Execution failed: {str(e)}")
except Exception as e:
    logger.exception("Unexpected error in skill execution")
    result = Result(status="error", message="Internal error, please try again")

return result
```

---

## Testing Strategy

### Unit Tests (test_*.py)

```python
def test_open_app_skill():
    adapter = MockPlatformAdapter()
    skill = OpenAppSkill(adapter)
    intent = Intent(action="OPEN_APP", parameters={"app": "chrome"}, confidence=0.95)
    result = asyncio.run(skill.execute(intent, ExecutionContext()))
    assert result.status == "success"

def test_nlu_parse_voice():
    nlu = NLUEngine(MockAdapter())
    intent = nlu.parse("open chrome")
    assert intent.action == "OPEN_APP"
    assert intent.parameters["app"] == "chrome"
```

### Integration Tests

```python
async def test_end_to_end_voice_command():
    agent = Agent(test_config)
    result = await agent.handle_voice_input("open chrome")
    assert result.status == "success"
```

---

## Logging & Observability

All operations logged via loguru:

```python
self.logger.info(f"Executing skill: {skill.name}")
self.logger.debug(f"Intent parameters: {intent.parameters}")
self.logger.error(f"Skill failed: {e}", exc_info=True)
```

Logs include:
- Timestamp, level, component name
- User action + parameters
- Execution time
- Success/failure
- Optional stacktrace on error

---

## Configuration (via ~/.rocket/config.yaml)

```yaml
agent:
  host: localhost
  port: 8765
  log_level: INFO
  
platform:
  type: auto  # auto-detect or specify: windows, macos, linux

skills:
  enabled:
    - "OPEN_APP"
    - "TYPE_TEXT"
    - "SCROLL"
  disabled:
    - "DELETE_FILES"  # Safety feature
  
nlu:
  confidence_threshold: 0.7
  ask_on_ambiguous: true

models:
  whisper_model: "base"  # tiny, base, small, medium, large
  device: "auto"  # cuda, cpu, mps (macOS)
```
