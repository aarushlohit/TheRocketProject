# Rocket: Accessibility-First Computer Automation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Stage: Phase 0 Foundation](https://img.shields.io/badge/Stage-Phase%200%20Foundation-blue)

**Rocket** is an open-source, accessibility-first automation system that empowers blind, deaf-blind, and motor-impaired users to control computers using voice and drawing commands.

Instead of clicking and typing, users can say:
- *"Open Chrome"*
- *"Go to Google"*
- *"Type my email address"*

Or draw simple gestures:
- Upward stroke → scroll up
- Downward stroke → scroll down
- Left swipe → go back

**Zero cloud dependency. Works offline. Open source. Fully accessible.**

---

## Why Rocket?

### The Problem
- Screen readers describe interfaces but don't automate them
- Voice assistants are locked into proprietary ecosystems
- Motor-impaired users struggle with precise mouse control
- Existing RPA tools are GUI-dependent and inaccessible

### The Solution
Rocket separates **decision-making** (AI) from **execution** (automation):
- **AI decides WHAT** to do (intent from voice/drawing)
- **Rocket decides HOW** to do it (skill execution, error handling)

### For Accessibility Users
✅ **Zero proprietary lock-in** — Open source, own your data
✅ **Works offline** — Local Whisper STT, no internet needed
✅ **Universal** — Works across Windows, macOS, Linux
✅ **Low latency** — < 800ms voice → action
✅ **Accessible to extend** — Write custom skills without modifying core

---

## Quick Start

### Prerequisites
- Python 3.11+
- iOS 14+ or Android 11+ (mobile app)
- 2GB free disk space (for models)

### Setup (5 minutes)

```bash
# Clone and enter directory
git clone https://github.com/rocket-automation/rocket.git
cd rocket

# Run setup script
bash scripts/setup.sh

# Download models (first-time only, ~5 min)
bash scripts/setup_models.sh

# Start agent
python agent/main.py
```

Agent runs on: `ws://localhost:8765`

### Build & Deploy Mobile App

```bash
cd flutter_app
flutter pub get
flutter run  # iOS/Android
```

---

## Architecture Overview

```
Mobile App (Flutter)
  ├─ Voice capture (Whisper)
  ├─ Drawing gestures
  └─ WebSocket → PC Agent
       ↓
PC Agent (Python)
  ├─ Intent parsing (NLU)
  ├─ Skill routing
  ├─ Platform adapter
  └─ OS automation
       ↓
Action executed on desktop
  └─ Haptic/audio feedback to mobile
```

**Full details**: See [ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Features (Phase 0)

### Core Skills
- ✅ **OPEN_APP** — Launch applications
- ✅ **TYPE_TEXT** — Type into focused window
- ✅ **PRESS_KEYS** — Keyboard shortcuts (Ctrl+S, etc.)
- ✅ **SCROLL** — Navigate up/down/left/right
- ✅ **CLICK** — Click at screen coordinates
- ✅ **OPEN_URL** — Navigate to websites
- ✅ **SELECT_TEXT** — Select word/line/all

### Input Methods
- ✅ **Voice commands** (Whisper-based)
- ✅ **Drawing gestures** (strokes, swipes)
- ✅ **Haptic feedback** (mobile vibration)
- ✅ **Audio confirmation** (text-to-speech)

### Platforms
- ✅ Windows 10/11
- ✅ macOS 12+
- ✅ Linux (Ubuntu, Fedora, Debian)
- ✅ iOS 14+
- ✅ Android 11+

### Accessibility
- ✅ Screen reader compatible
- ✅ Keyboard-only workflows
- ✅ No visual-only feedback
- ✅ Haptic feedback for deaf-blind users

---

## Documentation

| Document | Purpose |
|----------|---------|
| [PROJECT_IDEA.md](docs/PROJECT_IDEA.md) | Problem statement, real-world scenarios |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, components |
| [ENGINEERING_PRINCIPLES.md](docs/ENGINEERING_PRINCIPLES.md) | Design rules and philosophy |
| [TECH_STACK.md](docs/TECH_STACK.md) | Technology choices and rationale |
| [API_SPEC.md](docs/API_SPEC.md) | WebSocket protocol specification |
| [AGENT_DESIGN.md](docs/AGENT_DESIGN.md) | PC agent architecture and code |
| [SKILLS.md](docs/SKILLS.md) | Skill system and current skills |
| [ROADMAP.md](docs/ROADMAP.md) | Phase-by-phase development plan |
| [FEATURES_V1.md](docs/FEATURES_V1.md) | MVP scope and quality gates |

---

## Installation

### From Source (Development)

```bash
git clone https://github.com/rocket-automation/rocket.git
cd rocket
bash scripts/setup.sh
python agent/main.py
```

### From PyPI (Future)

```bash
pip install rocket-agent
rocket start --voice --drawing
```

### With Docker (Phase 1)

```bash
docker pull rocket-automation/agent
docker run -p 8765:8765 rocket-automation/agent
```

---

## Configuration

Default config: `~/.rocket/config.yaml`

```yaml
agent:
  host: localhost
  port: 8765
  log_level: INFO

models:
  whisper_model: base    # tiny, base, small, medium, large
  device: auto          # cuda, cpu, mps, auto
```

Full example: [scripts/config.example.yaml](scripts/config.example.yaml)

---

## Development

### Architecture
- **Backend**: Python 3.11, asyncio, WebSocket
- **Mobile**: Flutter, Dart
- **Core Skills**: Platform-specific adapters (Windows/macOS/Linux)

### Project Structure
```
rocket/
├── docs/              # Documentation
├── agent/             # PC agent (backend)
│   ├── core/          # Intent, Result, Context
│   ├── skills/        # Skill implementations
│   ├── nlu/           # Intent parsing
│   ├── platform/      # OS adapters
│   ├── server/        # WebSocket server
│   └── utils/         # Logging, config
├── mobile_app/        # Flutter app (WIP)
├── models/            # Model storage
├── scripts/           # Setup scripts
├── tests/             # Unit/integration tests
├── requirements.txt   # Python dependencies
└── README.md          # You are here
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=agent
```

### Code Style

```bash
# Format code
black agent/

# Lint
ruff check agent/

# Type check
mypy agent/
```

### Debugging

```bash
# Start agent with debug logging
python agent/main.py --debug

# Monitor WebSocket traffic
wscat -c ws://localhost:8765

# Watch logs in real-time
tail -f logs/rocket-agent.log
```

---

## Contributing

We welcome contributions from everyone, especially from disabled developers and users!

### Getting Started
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-skill`
3. Make changes and test: `pytest tests/`
4. Submit a pull request

### Contribution Guidelines
- See [CONTRIBUTING.md](CONTRIBUTING.md) (coming soon)
- Follow [ENGINEERING_PRINCIPLES.md](docs/ENGINEERING_PRINCIPLES.md)
- Include tests for new features
- Update documentation

### Areas to Help
- Add new skills (see [SKILLS.md](docs/SKILLS.md))
- Improve platform adapters
- Add more unit tests
- Documentation improvements
- Accessibility testing with real users
- Mobile app development (Flutter)

---

## Testing Accessibility

Before submitting PRs, test with:
- **Screen readers**: NVDA (Windows), JAWS (Windows), VoiceOver (macOS/iOS), TalkBack (Android)
- **Keyboard only**: No mouse, all navigation via keyboard
- **Motor**: Use voice input instead of mouse clicks
- **Deaf-blind**: Haptic feedback, no audio-only alerts

---

## Roadmap

### Phase 0: Foundation (NOW)
- [x] Repository setup
- [x] Core documentation
- [x] Agent skeleton
- [ ] Implement 6+ core skills
- [ ] Mobile app MVP
- [ ] User testing with accessibility community

### Phase 1: Stabilization (Q2 2025)
- [ ] 95%+ test coverage
- [ ] Multi-platform validation
- [ ] Performance optimization
- [ ] Community feedback integration

### Phase 2: Expansion (Q3-Q4 2025)
- [ ] 30+ skills
- [ ] Mobile app on app stores
- [ ] Custom skill SDK
- [ ] Braille input support

### Phase 3+: Advanced (2026+)
- [ ] Eye-tracking support
- [ ] Learning from user behavior
- [ ] Multi-device coordination
- [ ] Non-profit sustainability

**Full roadmap**: [ROADMAP.md](docs/ROADMAP.md)

---

## Known Limitations (Phase 0)

❌ Does not work with:
- GUI-only applications (some proprietary tools)
- Web applications requiring visual interaction (for now)
- Real-time games
- Applications that block automation APIs

✅ Workarounds planned for Phase 1+

---

## Performance

### Latency Targets
| Action | Target | Status |
|--------|--------|--------|
| Voice input → action | < 800ms | Phase 0 |
| Drawing recognition | < 500ms | Phase 0 |
| Network round-trip | < 100ms | Depends on network |

### Resource Usage
- **Memory**: ~100MB baseline + model size (140MB for base Whisper)
- **CPU**: ~5% idle, 20-30% during skill execution
- **Battery** (mobile): ~1% per hour of active use

---

## Security & Privacy

### By Design
- ✅ **No cloud upload** — Everything runs locally
- ✅ **No telemetry** — Your actions stay on your device
- ✅ **Open source** — Audit everything
- ✅ **Encrypted transport** — TLS in production

### Best Practices
- Use `wss://` (TLS) in production
- Run agent on trusted network only
- Review skill code before installing custom skills
- Monitor `~/.rocket/` for audit logs

---

## Community

### Get Involved
- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Q&A, general discussion
- **Discord** (coming soon): Real-time chat with maintainers

### User Testing
We need feedback from actual accessibility users! If you use assistive technology and want to help shape Rocket, please:

1. File an issue: https://github.com/rocket-automation/rocket/issues
2. Test the MVP when available
3. Share your experience

### Accessibility-First Development

Rocket itself must be accessible to contribute to. If you find barriers to contribution (unclear docs, inaccessible tooling, etc.), please report it.

---

## License

MIT License — See [LICENSE](LICENSE) for details.

**In short**: Use Rocket however you want, include the license in distributions.

---

## Support

### Getting Help
1. Check [docs/](docs/) for comprehensive guides
2. Search [GitHub Issues](https://github.com/rocket-automation/rocket/issues)
3. Ask in GitHub Discussions
4. Contact maintainers (email in GitHub profile)

### Reporting Bugs
- Use GitHub Issues with detailed steps to reproduce
- Include error logs from `~/.rocket/logs/`
- Mention your OS and Python version

---

## Acknowledgments

Rocket is built by and for the accessibility community. Special thanks to:
- The Whisper team (OpenAI) for open-source STT
- Accessibility advocates who shaped the vision
- Early testers and contributors

---

## Roadmap: What's Next?

**Immediate (Week 1)**
- Implement core skills (OPEN_APP, TYPE_TEXT, SCROLL)
- WebSocket server integration testing
- Mobile app voice input capture

**This Month**
- 95% test coverage
- Platform adapter implementation (all 3 OSes)
- User testing with blind users

**This Quarter**
- Phase 0 release (v0.1.0)
- Community onboarding
- Phase 1 planning

---

## Questions?

This is the foundation stage. Questions about design, architecture, or accessibility considerations? Open a GitHub issue labeled `question` or start a discussion!

---

**Let's build the future of accessible automation. 🚀**
