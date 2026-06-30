# Rocket

**Blind-first autonomous desktop agent.** Rocket lets people with visual impairments control a Windows PC using only their voice, hand-drawn gestures, or 8-dot Braille — all from a Flutter mobile app.

A Flutter phone app captures input and sends it over WebSocket to a Python backend running on the target PC. The backend parses intent using NVIDIA Nemotron, compiles a mission brief, executes it through OpenCode CLI (which drives Playwright, computer-use, and Rocket Windows MCP tools), and verifies the result against real OS state before reporting back to the user in natural speech.

---

## Architecture at a Glance

```
Flutter app  (voice / braille / drawing)
  └─▶ WebSocket  ──────────────────────────────────────────────────┐
                                                                    ▼
                              agent/server/websocket_handler.py  (intake)
                                          │
                              agent/adapters/nemotron.py         (perception)
                                          │
                              agent/runtime/browser_state.py     (mission compile)
                                          │
                              agent/runtime/adapter.py           (execute + verify + recover)
                                          │
                                    OpenCode CLI  ──▶  Real Windows desktop
                                          │
                              agent/runtime/phone_speech.py      (natural speech reply)
                                          └─▶  WebSocket  ──▶  Flutter app
```

**Golden rule:** Rocket never trusts words. Rocket trusts reality. The verifier must confirm the goal in the real OS before success is reported.

---

## Repository Layout

```
rocket/
├── agent/                  # Python backend service
│   ├── adapters/           # Perception: speech, vision, Nemotron, Pollinations
│   ├── pairing/            # QR-code / token pairing manager
│   ├── phase2/             # MCP compatibility entrypoints (windows, memory, shokunin)
│   ├── runtime/            # Execution engine: adapter, verifier, recovery, memory, vault
│   ├── server/             # Authenticated WebSocket intake + HTTP dashboard
│   ├── terminal/           # Rich terminal UI (Rich library)
│   ├── utils/              # Config, env loader, logger
│   └── main.py             # Entry point
│
├── apps/
│   ├── mobile/             # Flutter mobile app — voice / braille / drawing capture
│   ├── desktop/            # Flutter Windows launcher — embeds the Python backend
│   └── web/                # Flutter web dashboard — live task and status view
│
├── tests/                  # Python unit + integration test suite (204 tests)
├── docs/                   # Architecture, perception, UI guidelines, and vision docs
├── labs/                   # Isolated research experiments (Nemotron validation scripts)
├── packaging/              # PowerShell build, install, and Inno Setup scripts
├── external/               # Vendored repos (openwork, shokunin) — untracked
├── shokunin-opencode-powers/ # Machine-local OpenCode config — never committed
│
├── requirements.txt        # Python dependencies
├── ARCHITECTURE.md         # Frozen module map and data-flow reference
├── HANDOFF.md              # Engineering state, known issues, and next steps
└── RUNBOOK.md              # Operational commands (run, test, lint, benchmark)
```

---

## Quick Start

### Backend (Windows — requires Python 3.11+)

```powershell
cd rocket
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

$env:NVIDIA_API_KEY = "your_nvidia_key"
python -m agent.main --host 0.0.0.0 --port 8765
```

Scan the QR code shown in the terminal from the mobile app.

### Mobile App (Flutter)

```bash
cd rocket/apps/mobile
flutter pub get
flutter run
```

### Run via convenience scripts (Windows)

```bat
# Start everything in two separate windows
rocket\START_ALL.bat

# Backend only
rocket\start_backend.bat

# Mobile app only
rocket\start_frontend.bat
```

---

## Development

### Tests

```powershell
cd rocket
python -m unittest discover -s tests
```

### Lint

```powershell
python -m ruff check agent tests
python -m compileall agent tests
```

### Flutter

```bash
cd rocket/apps/mobile   # or apps/desktop / apps/web
flutter test
flutter analyze
```

---

## Key Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `NVIDIA_API_KEY` | — | Required for Nemotron perception and OpenCode models |
| `ROCKET_WHISPER_MODEL` | `base` | faster-whisper model size (`base` / `small` / `medium` / `large-v3`) |
| `ROCKET_DRAWING_DIRECT` | `1` | Send drawing image straight to OpenCode vision (no pre-extraction) |
| `ROCKET_VERIFIER_ENABLED` | `1` | Verifier authority over OpenCode result |
| `ROCKET_RECOVERY_ENABLED` | `1` | Enable recovery loop on failure |
| `ROCKET_OPENCODE_TIMEOUT_SECONDS` | `60` | Per-task OpenCode timeout (`0` = infinite) |

See `HANDOFF.md` for the full variable reference.

---

## Documentation

| File | Purpose |
|---|---|
| [`rocket/ARCHITECTURE.md`](rocket/ARCHITECTURE.md) | Complete frozen module map |
| [`rocket/HANDOFF.md`](rocket/HANDOFF.md) | Engineering state, known issues, and next steps |
| [`rocket/RUNBOOK.md`](rocket/RUNBOOK.md) | Operational commands |
| [`rocket/docs/00_VISION.md`](rocket/docs/00_VISION.md) | Product vision and goals |
| [`rocket/docs/04_PERCEPTION_ENGINE.md`](rocket/docs/04_PERCEPTION_ENGINE.md) | Perception pipeline design |
| [`rocket/docs/05_NEMOTRON_PROMPTS.md`](rocket/docs/05_NEMOTRON_PROMPTS.md) | Prompt engineering reference |

---

## Contributing

- One logical change per commit. Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
- Keep `python -m unittest discover -s tests` green and `ruff check` clean on every change.
- `shokunin-opencode-powers/` and `external/` are machine-local — never commit them.
