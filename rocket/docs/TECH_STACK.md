# Technology Stack

## Overview

Rocket uses a **carefully curated** technology stack optimized for accessibility, performance, and open-source sustainability.

**Design Rule**: Every dependency must justify its existence.

---

## Backend (PC Agent)

### Core Language: Python 3.11+

**Why Python?**
- ✅ Accessibility: Mature a11y testing libraries
- ✅ Rapid development: Write skills quickly
- ✅ Open-source ecosystem: Most automation tools are Python
- ✅ Cross-platform: Works on Windows, macOS, Linux with minimal changes
- ✅ Accessible tooling: VS Code + accessibility mode, Jupyter notebooks
- ❌ Performance-critical? Skills can be Cython/Rust if needed

**Version**: 3.11+ (modern async, better error messages, type hints)

---

### Core Dependencies

#### async/networking
| Package | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| `websockets` | 12+ | WebSocket server for mobile connection | Low-level, minimal overhead, well-maintained |
| `asyncio` | stdlib | Async task scheduling | Built-in, no external deps |

#### NLU & Intent Parsing
| Package | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| `spacy` | 3.7+ | Tokenization, entity recognition | Lightweight, open-source, good accuracy |
| `regex` | 2023+ | Pattern matching for intent rules | Better than standard `re`, supports lookahead |

#### Platform Control
| Package | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| `pyautogui` | 0.9.53+ | Cross-platform mouse/keyboard automation | Reliable, maintains good compatibility |
| `pyperclip` | 1.8.2+ | Clipboard access across platforms | Lightweight, single-purpose |

**Platform-Specific**:
- **Windows**: `pywin32` (COM automation, window control)
- **macOS**: `PyObjC` (native API access)
- **Linux**: `python-xlib`, `xdotool` (X11/Wayland automation)

#### OCR & Vision
| Package | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| `opencv-python` | 4.8+ | Image preprocessing for drawings | Fast, widely used, good drawing support |
| `pytesseract` | 0.3.10+ | Text detection in UI (future) | Open-source OCR engine |
| `gesture-controlled` | custom/TBD | Drawing gesture recognition | Custom module for MVP (see below) |

#### Logging & Monitoring
| Package | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| `loguru` | 0.7+ | Structured logging with rotation | Better than `logging`, cleaner API |
| `prometheus-client` | 0.17+ | Metrics export (optional) | Standard for observability |

#### Testing
| Package | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| `pytest` | 7.4+ | Test framework | Industry standard, great assertion introspection |
| `pytest-asyncio` | 0.21+ | Async test support | Seamless async testing |
| `pytest-cov` | 4.1+ | Coverage reporting | Standard coverage tool |

#### Development
| Package | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| `black` | 23+ | Code formatting | Opinionated, consistency across team |
| `ruff` | 0.1+ | Fast linting | Modern, fast alternative to flake8 |
| `mypy` | 1.5+ | Static type checking | Catches type errors early |

---

## Frontend (Mobile App)

### Core Language: Dart/Flutter

**Why Flutter?**
- ✅ Single codebase for iOS, Android
- ✅ Accessibility: Flutter has good a11y support (Semantics, TalkBack, VoiceOver)
- ✅ Performance: Compiled to native, 60+ fps on old devices
- ✅ Open-source: Active community, good documentation
- ❌ Not React Native? Better performance, better a11y defaults

**Version**: Latest stable (currently 3.13+)

---

### Mobile Dependencies

| Package | Purpose | Rationale |
|---------|---------|-----------|
| `web_socket_channel` | WebSocket client | Low-level, minimal overhead |
| `speech_to_text` | Voice input capture | Flutter native, good a11y |
| `flutter_sound` | Audio playback for feedback | Lightweight, good latency |
| `gestures` | Drawing input recognition | Native Flutter gesture detection |
| `permission_handler` | Platform permissions | Standard for iOS/Android permissions |
| `connectivity_plus` | Check network status | Graceful offline handling |

---

## AI Models (Local)

### Whisper (Speech-to-Text)

**Model**: OpenAI Whisper

**Why Whisper?**
- ✅ Open-source (under MIT-like license)
- ✅ Works offline locally
- ✅ Good accuracy on diverse accents
- ✅ Available in multiple sizes (tiny 39M → large 1.5GB)
- ✅ Easy integration with Python

**Implementation Plan**:
- **Mobile**: Use `openai-whisper` Python package on agent, not on device
- **Alternative**: Whisper.cpp for mobile if needed (not in Phase 0)
- **Fallback**: Cloud Whisper API if local too slow

**Installation**:
```bash
pip install openai-whisper
python -m pip install openai-whisper[energy]  # GPU support if available
```

**Model Size Selection**:
- **MVP (Phase 0)**: `base` model (140M) - balance of speed/accuracy
- **Future**: User-selectable (tiny for speed, large for accuracy)

---

### OCR & Drawing Recognition

**Phase 0 Approach**: Rule-based gesture recognition (no heavy ML)

**Gesture Library**:
- Upward stroke → SCROLL_UP
- Downward stroke → SCROLL_DOWN
- Leftward stroke → GO_BACK
- Rightward stroke → GO_FORWARD
- Circular stroke → UNDO/REDO
- Rectangular selection → SELECT_MULTIPLE

**Implementation**: Custom gesture.py module using velocity, angle, shape analysis

**Future (Phase 2)**: 
- TensorFlow.js on mobile for real-time drawing recognition
- Or TinyML model for custom drawings

---

## Data Formats

### Protocol: JSON over WebSocket

**Why JSON?**
- ✅ Human-readable (debuggable)
- ✅ Language-agnostic (future multi-language agents)
- ✅ Schema standardization available (JSON Schema)
- ✅ Easy integration with logging/monitoring
- ❌ Binary? Not needed for Phase 0; can stream separately if needed

---

### Storage: YAML for Config, JSON for Data

**Config Files**: YAML (human-editable)
```yaml
# ~/.rocket/config.yaml
agent:
  port: 8765
  log_level: INFO
models:
  whisper_model: base
  device: cuda  # or cpu
```

**State/Logs**: JSON (machine-readable)
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "event": "skill_executed",
  "skill": "open_app",
  "app": "chrome",
  "duration_ms": 250,
  "status": "success"
}
```

---

## Development Environment

### IDE: VS Code

**Required Extensions**:
- Python
- Pylance (type checking)
- Dart (Flutter)
- WebSocket viewer (debugging)

**Accessibility Plugins**:
- Accessibility Checker
- axe DevTools
- ARIA linter

---

### Package Management

**Backend**: `pip` with `requirements.txt`
- Simple, dependency-transparent
- No lock files initially (can add `poetry` in Phase 1)

**Mobile**: `pub` (Dart's package manager)
- Built-in to Flutter
- Good security model

---

### Docker (Optional, Phase 1)

For distribution and easy setup:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY agent/ .
CMD ["python", "main.py"]
```

---

## DevOps & CI/CD

### Source Control: Git

**Platform**: GitHub (free, accessible, community-standard)

**Branching**:
```
main           (stable releases)
├─ develop     (integration branch)
│  ├─ feature/skill-open-app
│  ├─ feature/nlu-improvement
│  └─ fix/latency-timeout
```

### CI/CD Pipeline (GitHub Actions)

**Stage 1: Lint & Type Check**
```yaml
- name: Lint & Type Check
  run: |
    black --check .
    ruff check .
    mypy agent/
```

**Stage 2: Unit Tests**
```yaml
- name: Run Tests
  run: pytest tests/ -v --cov=agent
```

**Stage 3: Accessibility Checks**
```yaml
- name: A11y Checks
  run: |
    python tests/a11y_checks.py
```

**Stage 4: Benchmark**
```yaml
- name: Latency Benchmarks
  run: pytest benchmarks/ --benchmark-autosave
```

---

## Deployment

### Local Installation
```bash
git clone https://github.com/rocket-automation/rocket.git
cd rocket
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python agent/main.py
```

### Package Distribution (Future)
```bash
pip install rocket-agent
rocket start --voice --drawing
```

---

## Dependency Rationale Summary

| Dependency | Why Not... | Why Yes |
|-----------|-----------|---------|
| `websockets` | `socket.io` (too heavy), `aiohttp` (overkill) | Low-level, no overhead, WebSocket-native |
| `spacy` | `NLTK` (outdated), `transformers` (slow) | Modern, fast, good default accuracy |
| `pyautogui` | `keyboard` + `mouse` (low-level) | High-level, cross-platform unified API |
| `pytest` | `unittest` (verbose) | Industry standard, great introspection |
| Flutter | React Native | Better a11y, better performance |
| Whisper | Google STT, Amazon Lex | Open-source, offline, diverse accents |

---

## Future Technology Swaps

**No current dependencies on**:
- Cloud APIs (intentional)
- Heavy ML frameworks (intentional)
- Real-time databases (not needed yet)
- Container orchestration (not needed yet)

**When to Reconsider**:
- **More ML models**: If gesture recognition gets complex, add TensorFlow Lite
- **More performance**: If Python agent too slow, rewrite skills in Rust (still Python glue)
- **Cloud features**: Phase 2+, use Firebase or open-source alternative only
- **Scaling**: Phase 3+, then consider message queues, databases

---

## Total Dependencies (Phase 0)

**Backend**: ~15 core packages
- Minimal surface area
- Easy to audit
- Easy to update

**Mobile**: ~10 packages
- Core Flutter framework
- Accessibility plugins

**Total**: ~25 packages
- ALL open-source
- ALL well-maintained
- ALL have clear purpose
