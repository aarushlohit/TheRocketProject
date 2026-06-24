# Rocket V3

Rocket is a blind-first computer control bridge.

```text
Flutter app
  -> voice / drawing / braille capture
  -> WebSocket
  -> Nemotron intent parsing
  -> RocketTerminal task display
  -> OpenCode runtime verification
  -> OpenCode CLI execution
```

## Project Layout

- `agent/adapters`: perception adapters and Nemotron parser prompts.
- `agent/server`: authenticated WebSocket intake from the mobile app.
- `agent/runtime`: OpenCode-only execution, setup state, memory, vault, and powers sync.
- `agent/phase2`: compatibility MCP entrypoints used by OpenCode config.
- `agent/terminal`: rich terminal UI and pairing display.
- `mobile_app`: Flutter client for blind-first capture and onboarding.
- `tests`: backend regression tests.

## Run Backend

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:NVIDIA_API_KEY="your_key"
python -m agent.main --host 0.0.0.0 --port 8765
```

The backend verifies global OpenCode powers from `C:\Users\Aarush\shokunin-opencode-powers` into `C:\Users\Aarush\.config\opencode`.

## Run Mobile App

```powershell
cd mobile_app
flutter pub get
flutter run
```

Scan the backend QR code from the Flutter app.

## Test

```powershell
python -m unittest discover -s tests
python -m compileall agent tests
cd mobile_app
flutter analyze
```

## Security

Do not store real credentials in `opencode.json`. Rocket migrates real-looking MCP env secrets into a DPAPI-backed local vault and passes them to OpenCode through process environment variables. Rotate any token that was previously stored in plaintext.
