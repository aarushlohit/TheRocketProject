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

## Install Backend App Wrapper

Create a Start Menu/Desktop launcher for the backend:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_rocket_backend.ps1
```

Remove only the launcher wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_rocket_backend.ps1
```

## Build Bundled Backend Desktop App

### No Visual Studio Build Tools Required

Build a shippable backend app package with a Flutter web dashboard bundled into the Python backend app:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build_no_vs_backend_app.ps1
```

Install it for the current Windows user:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\install_no_vs_backend_app.ps1
```

Installed users launch **Rocket Backend** from the Start Menu or desktop. The app opens a local browser dashboard and starts the bundled backend.

Uninstall only the app wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\uninstall_no_vs_backend_app.ps1
```

### Native Flutter Windows App

Build a Flutter Windows backend app with the Python backend bundled inside it:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build_backend_app.ps1
```

The ready-to-run app is created at:

```text
backend_app\build\windows\x64\runner\Release\rocket_backend_app.exe
```

To create a real Windows installer, install Inno Setup 6 and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\make_windows_installer.ps1
```

The installer output is:

```text
dist\installer\RocketBackendSetup.exe
```

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
