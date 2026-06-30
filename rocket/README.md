# Rocket — Backend & Monorepo

This directory is the Rocket monorepo root. It contains the Python backend service, all Flutter apps, tests, documentation, and packaging scripts.

> For a high-level project overview start at [`../README.md`](../README.md).

---

## Data Flow

```
Flutter app  (voice / braille / drawing)
    │  WebSocket (authenticated)
    ▼
agent/server/websocket_handler.py      ← intake, routes by message type
    │
    ├─ audio   → agent/adapters/speech.py        (faster-whisper → Google SR → Riva)
    ├─ drawing → agent/adapters/nemotron.py       (direct MIMO vision path)
    └─ braille → agent/adapters/nemotron.py       (text intent parse)
                     │
                     ▼
         agent/runtime/browser_state.py           ← compile mission JSON
         agent/runtime/mission_brief.py           ← MISSION / CONTEXT / GOAL / DONE WHEN
         agent/server/task_quality.py             ← quality gate (reject vague input)
                     │
                     ▼
         agent/runtime/adapter.py  run_with_recovery()
             │
             ├─ agent/runtime/opencode_cli_client.py  → OpenCode CLI (PowerShell)
             │       └─ MCP tools: Playwright · computer-use · rocket-windows · memory
             │
             ├─ agent/runtime/verifier.py             → reality check (tri-state)
             └─ agent/runtime/recovery.py             → ordered recovery strategies
                     │
                     ▼
         agent/runtime/phone_speech.py            ← sanitize to natural language
    │  WebSocket reply
    ▼
Flutter app  (speech feedback)
```

---

## Directory Structure

```
rocket/
│
├── agent/                        # Python backend service
│   ├── adapters/
│   │   ├── nemotron.py           # Perception orchestrator (audio / image / braille → mission)
│   │   ├── speech.py             # Speech-to-text chain (faster-whisper primary)
│   │   ├── vision.py             # Kimi K2.6 vision extraction (fallback path)
│   │   ├── pollinations.py       # Text fallback parser
│   │   └── prompts.py            # Shared parser prompt templates
│   ├── pairing/
│   │   └── manager.py            # QR-code / token pairing
│   ├── phase2/                   # MCP compatibility entrypoints (OpenCode config)
│   │   ├── windows_mcp.py        # Rocket Windows MCP server
│   │   ├── memory_mcp.py         # Memory MCP server
│   │   └── shokunin_mcp.py       # Shokunin memory MCP
│   ├── runtime/
│   │   ├── adapter.py            # RocketAdapter.execute + run_with_recovery
│   │   ├── verifier.py           # Reality verifier suite (tri-state, fail-closed)
│   │   ├── recovery.py           # Recovery decision engine
│   │   ├── opencode_cli_client.py# Runs OpenCode via PowerShell; builds prompts
│   │   ├── opencode_runtime.py   # Syncs ~/.config/opencode (agent md, MCP, plugins)
│   │   ├── browser_state.py      # Mission compilation + browser session model
│   │   ├── mission_brief.py      # MISSION / CONTEXT / GOAL / DONE WHEN builder
│   │   ├── first_launch.py       # First-run onboarding + component detection
│   │   ├── memory.py             # DPAPI-encrypted SQLite profile & kv store
│   │   ├── vault.py              # DPAPI secret vault
│   │   ├── security.py           # DPAPI protect / unprotect
│   │   ├── phone_speech.py       # Natural-language speech sanitizer
│   │   ├── terminal_bridge.py    # Bridges WebSocket execution → terminal + adapter
│   │   ├── results.py            # RocketExecutionResult dataclass
│   │   ├── benchmark.py          # 350-task simulated benchmark harness
│   │   ├── benchmark_live.py     # Live executor wiring (inert unless armed)
│   │   ├── bootstrap.py          # Repo bootstrap utilities
│   │   ├── browser_runtime.py    # Browser ownership / reuse controller
│   │   ├── install_mission.py    # Install verb parsing
│   │   ├── prompts.py            # OpenCode system prompt (Manus-style)
│   │   └── setup.py              # RocketSetup state (workspace / full access)
│   ├── server/
│   │   ├── websocket_handler.py  # Authenticated WebSocket intake
│   │   ├── dashboard_http.py     # Local HTTP dashboard server
│   │   └── task_quality.py       # Pre-execution quality gate
│   ├── terminal/
│   │   └── rocket_terminal.py    # Rich terminal UI + QR pairing display
│   ├── utils/
│   │   ├── config.py             # Config loader (YAML / env)
│   │   ├── env.py                # .env file loader
│   │   └── logger.py             # Structured logging setup
│   ├── backend_app_entry.py      # Alternate entry point for bundled desktop app
│   └── main.py                   # Primary entry point (Typer CLI)
│
├── apps/
│   ├── mobile/                   # Flutter mobile app (voice / braille / drawing capture)
│   ├── desktop/                  # Flutter Windows launcher (embeds Python backend)
│   └── web/                      # Flutter web dashboard (live task & status view)
│
├── tests/                        # Python test suite — 204 tests across 16 files
├── docs/                         # Architecture, perception, UI, and vision documentation
├── labs/                         # Isolated research & validation scripts
│   └── nemotron/                 # Nemotron + Pollinations adapter validation
│       ├── adapter.py            # Thin build_adapter() factory
│       ├── audio_test.py         # WAV → task validation
│       ├── braille_test.py       # Braille text → task validation
│       ├── image_test.py         # PNG → task validation
│       ├── generate_audio_sample.py  # Synthetic WAV generator
│       ├── samples/              # Test inputs (audio.wav, braille.txt, image.png)
│       └── outputs/              # Generated outputs — gitignored
│
├── packaging/                    # Windows build & distribution scripts
│   ├── build_backend_app.ps1     # Flutter Windows app + embedded Python backend
│   ├── build_no_vs_backend_app.ps1  # PyInstaller backend + Flutter web dashboard
│   ├── install_no_vs_backend_app.ps1
│   ├── uninstall_no_vs_backend_app.ps1
│   ├── make_windows_installer.ps1   # Inno Setup installer (requires Inno Setup 6)
│   ├── RocketBackend.spec           # PyInstaller spec
│   └── rocket_backend_app.iss       # Inno Setup script
│
├── external/                     # Vendored repos — untracked, never commit
├── shokunin-opencode-powers/     # Machine-local OpenCode config — never commit
│
├── requirements.txt              # Python dependencies
├── opencode.json                 # Local OpenCode config (gitignored)
├── ARCHITECTURE.md               # Frozen module map — read before changing anything
├── HANDOFF.md                    # Engineering state, known issues, next steps
├── RUNBOOK.md                    # All operational commands
├── START_ALL.bat                 # Launch backend + Flutter app (Windows)
├── start_backend.bat             # Launch backend only (Windows)
├── start_frontend.bat            # Launch mobile app only (Windows)
├── install_rocket_backend.ps1    # Install Start Menu / Desktop launcher
└── uninstall_rocket_backend.ps1  # Remove launcher
```

---

## Running the Backend

```powershell
# Create venv and install dependencies
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Set required API key
$env:NVIDIA_API_KEY = "your_key"

# Start (WebSocket on :8765, dashboard on :8790)
python -m agent.main --host 0.0.0.0 --port 8765
```

The terminal will display a QR code — scan it from the mobile app to pair.

Optional flags:

```
--dashboard-port 8790     HTTP dashboard port
--open-dashboard          Open dashboard in default browser on startup
--log-level DEBUG         Verbose logging
--config path/to/cfg.yml  Custom config file
```

---

## Running the Flutter Apps

```bash
# Mobile app
cd apps/mobile && flutter pub get && flutter run

# Web dashboard
cd apps/web && flutter pub get && flutter run -d chrome

# Windows desktop launcher
cd apps/desktop && flutter pub get && flutter run -d windows
```

---

## Testing

```powershell
# All 204 backend tests
python -m unittest discover -s tests

# Lint
python -m ruff check agent tests

# Type check (non-blocking, ~29 known pre-existing findings)
python -m mypy agent

# Compile check
python -m compileall agent tests

# Flutter
cd apps/mobile && flutter test && flutter analyze
```

---

## Building for Distribution

### No-Visual-Studio package (PyInstaller + Flutter web dashboard)

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build_no_vs_backend_app.ps1
powershell -ExecutionPolicy Bypass -File .\packaging\install_no_vs_backend_app.ps1
```

### Native Flutter Windows app with embedded backend

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build_backend_app.ps1
```

### Full Windows installer (requires [Inno Setup 6](https://jrsoftware.org/isdl.php))

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\make_windows_installer.ps1
# Output: dist\installer\RocketBackendSetup.exe
```

---

## Key Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `NVIDIA_API_KEY` | — | Required — Nemotron + OpenCode models |
| `ROCKET_WHISPER_MODEL` | `base` | faster-whisper size: `base` · `small` · `medium` · `large-v3` |
| `ROCKET_DRAWING_DIRECT` | `1` | Send drawing directly to OpenCode vision (skip text extraction) |
| `ROCKET_VERIFIER_ENABLED` | `1` | Verifier authority over OpenCode result |
| `ROCKET_RECOVERY_ENABLED` | `1` | Enable recovery loop on execution failure |
| `ROCKET_RECOVERY_MAX_RETRIES` | `1` | Adapter-level recovery retry count |
| `ROCKET_OPENCODE_TIMEOUT_SECONDS` | `60` | Per-task OpenCode timeout (`0` = infinite) |
| `ROCKET_OPENCODE_PERSISTENT_SERVER` | `1` | Reuse one OpenCode server across tasks |
| `ROCKET_OPENCODE_REUSE_SESSION` | `1` | Reuse OpenCode session between tasks |
| `ROCKET_DISABLE_SPEECH` | — | Disable all speech-to-text |

---

## Documentation Index

| File | Description |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Frozen module map, verifier dispatch table, test suite reference |
| [`HANDOFF.md`](HANDOFF.md) | **Start here** — engineering state, known issues, next steps |
| [`RUNBOOK.md`](RUNBOOK.md) | All operational and debug commands |
| [`docs/00_VISION.md`](docs/00_VISION.md) | Product vision |
| [`docs/01_ARCHITECTURE.md`](docs/01_ARCHITECTURE.md) | Architecture overview |
| [`docs/02_PHASE1.md`](docs/02_PHASE1.md) | Phase 1 implementation notes |
| [`docs/03_UI_GUIDELINES.md`](docs/03_UI_GUIDELINES.md) | UI and accessibility guidelines |
| [`docs/04_PERCEPTION_ENGINE.md`](docs/04_PERCEPTION_ENGINE.md) | Perception pipeline design |
| [`docs/05_NEMOTRON_PROMPTS.md`](docs/05_NEMOTRON_PROMPTS.md) | Prompt engineering reference |
| [`docs/06_FLUTTER_APP.md`](docs/06_FLUTTER_APP.md) | Flutter app structure and decisions |
| [`docs/07_TERMINAL.md`](docs/07_TERMINAL.md) | Terminal UI design |
| [`docs/risk_matrix.md`](docs/risk_matrix.md) | Risk register |
| [`docs/stack_decision.md`](docs/stack_decision.md) | Technology stack rationale |

---

## Conventions

- Architecture is **frozen** — do not redesign. Polish, fix, and extend only. See `HANDOFF.md`.
- All commits must leave `python -m unittest discover -s tests` green and `ruff check` clean.
- `shokunin-opencode-powers/` and `external/` are machine-local — they must never be committed.
- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.
