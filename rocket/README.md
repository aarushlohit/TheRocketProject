# Rocket V3

Rocket Phase 1 is a blind-first perception bridge.

```text
Flutter App
  -> Voice, Drawing, Braille
  -> Nemotron Omni
  -> RocketParser Prompt
  -> One executable task
  -> RocketTerminal display
  -> OpenWork in Phase 2
```

Phase 1 deliberately does not execute tasks.

## Run RocketTerminal

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:NVIDIA_API_KEY="your_key"
python -m agent.main terminal --host 0.0.0.0 --port 8765
```

Scan the QR code from the Flutter app settings screen.

## Run Flutter

```powershell
cd mobile_app
flutter pub get
flutter run
```

On Windows, enable Developer Mode so Flutter can create plugin symlinks.

## Phase 1 Boundary

- No automation.
- No execution.
- No deterministic planner.
- No verification.
- No memory.
- No MCP.
- No skills.
- No Windows or browser control.

OpenWork is vendored in `external/openwork` for Phase 2 only.
