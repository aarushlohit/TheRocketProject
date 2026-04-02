# Nova Stage 0 Report

## Goal Delivered

Stage 0 was implemented around the draw-to-action pipeline:

`Mobile drawing -> authenticated WebSocket -> Python backend -> Pollinations vision AI -> validated intent -> Linux execution -> JSON response`

The work focused only on drawing mode, as requested.

## What Changed

### 1. Backend runtime was rebuilt around Stage 0

New modules were added under `agent/stage0/` and `agent/core/`:

- `agent/core/nova_stage0.py`
  - new top-level Stage 0 orchestrator
  - connects AI inference to OS execution
  - returns mobile-ready JSON payloads

- `agent/stage0/pairing.py`
  - generates and persists a pairing token
  - computes local LAN IP
  - prints QR in terminal
  - saves a PNG copy of the QR

- `agent/stage0/pipeline.py`
  - saves incoming drawings
  - uploads images to `https://media.pollinations.ai/upload`
  - calls Pollinations text inference with `gemini-fast`
  - falls back to `qwen-vision` when confidence is low
  - uses the Stage 0 system prompt for strict JSON-only extraction

- `agent/stage0/validation.py`
  - extracts the first valid JSON object from model output
  - validates allowed intents
  - validates confidence range
  - validates required slots
  - normalizes app/url/target slot formats

- `agent/stage0/executor.py`
  - maps validated intents to platform adapter calls
  - builds the final success/error message for mobile

### 2. WebSocket server was replaced with authenticated binary handling

`agent/server/websocket_handler.py` now:

- accepts binary image uploads directly
- authenticates via pairing token in the WebSocket query string
- returns JSON in the requested format
- supports a small `ping` message
- works with the current `websockets` API

### 3. Entry point now boots Nova Stage 0 directly

`agent/main.py` now:

- loads `.env` / `.ENV`
- runs startup dependency checks before server startup
- requires `POLLINATIONS_API_KEY`
- creates the Stage 0 data directory
- generates or reuses a pairing token
- prints the QR code in terminal
- starts the authenticated WebSocket server

### 4. Startup dependency checks were added

New module:

- `agent/utils/dependency_check.py`
  - adds `async def check_and_prepare_dependencies()`
  - predicts the current OS
  - predicts Linux distro via `/etc/os-release`
  - checks `xdg-open`, `wmctrl`, and `scrot`
  - attempts non-interactive Arch Linux installs with `pacman`
  - never blocks startup permanently
  - never crashes the backend when install fails
  - stores global runtime flags:
    - `HAS_XDG_OPEN`
    - `HAS_WMCTRL`
    - `HAS_SCROT`

Dependency behavior:

- `xdg-open`
  - treated as required for normal URL opening
  - if missing, install is attempted on Arch-like Linux
  - if still unavailable, Python `webbrowser` fallback is enabled

- `wmctrl`
  - treated as optional
  - if missing, install is attempted on Arch-like Linux
  - if still unavailable, Linux execution switches to pkill-based fallbacks where possible

- `scrot`
  - treated as optional
  - if missing, install is attempted on Arch-like Linux
  - if still unavailable, screenshot falls back to Pillow grab support

Expected startup logging now looks like:

```text
[INFO] Checking system dependencies...
[INFO] Predicted environment: Linux (arch)
[OK] xdg-open installed
[WARN] wmctrl missing -> attempting install
[FAIL] wmctrl install failed -> pkill fallback enabled
[OK] scrot installed
```

### 5. Linux execution layer was implemented

`agent/platform/linux.py` now supports:

- `OPEN_APP`
  - app alias resolution for common names like `chrome`, `firefox`, `code`, `settings`

- `CLOSE_APP`
  - `pkill -f <app>` when app is named
  - `wmctrl -c :ACTIVE:` for focused window fallback
  - if `wmctrl` is unavailable, focused-window close is rejected gracefully unless an app name is provided

- `MINIMIZE`
  - `wmctrl -r <target> -b add,hidden`
  - if `wmctrl` is unavailable and app name is provided, fallback uses `pkill -STOP`

- `MAXIMIZE`
  - `wmctrl -r <target> -b add,maximized_vert,maximized_horz`
  - if `wmctrl` is unavailable and app name is provided, fallback uses `pkill -CONT`

- `OPEN_URL`
  - `xdg-open`
  - Python `webbrowser` fallback when `xdg-open` is unavailable

- `SCREENSHOT`
  - `scrot` first
  - Pillow fallback if needed

Windows and macOS adapters were updated with Stage 0 method stubs so the abstract interface stays consistent, but execution is intentionally Linux-first.

### 6. Config and environment handling were cleaned up

Updated files:

- `agent/utils/config.py`
  - host default changed to `0.0.0.0`
  - confidence threshold changed to `0.6`
  - added `data/stage0` storage location

- `agent/utils/env.py`
  - new helper to load `.env` / `.ENV` safely without exposing values

- `agent/utils/logger.py`
  - now works with `loguru`
  - falls back cleanly to stdlib logging if `loguru` is absent

- `.gitignore`
  - ignores env files, venv, data, logs, and Flutter build artifacts

### 7. Flutter mobile app source was added

The mobile app lives under `mobile_app/`.

Implemented app features:

- `mobile_app/lib/main.dart`
  - app bootstrap
  - loads saved pairing config
  - auto-connects on launch

- `mobile_app/lib/models/pairing_config.dart`
  - QR payload parsing and validation

- `mobile_app/lib/services/pairing_store.dart`
  - persists pairing details with `shared_preferences`

- `mobile_app/lib/services/nova_socket_service.dart`
  - auto-reconnecting WebSocket client
  - binary PNG sending
  - last-response tracking
  - connection state tracking

- `mobile_app/lib/screens/home_screen.dart`
  - full-screen 2x2 layout
  - quadrants:
    - Voice
    - Drawing Mode
    - Braille
    - Settings
  - tap selects a quadrant with haptic feedback
  - double tap activates the mode

- `mobile_app/lib/screens/drawing_screen.dart`
  - full-screen canvas
  - white background
  - black strokes
  - no extra controls
  - double tap renders canvas to PNG and sends bytes over WebSocket

- `mobile_app/lib/screens/settings_screen.dart`
  - pairing status
  - connection status
  - QR scan trigger
  - reconnect
  - clear pairing

- `mobile_app/lib/screens/qr_pairing_screen.dart`
  - QR scanner flow using `mobile_scanner`

- `mobile_app/lib/widgets/quadrant_tile.dart`
  - reusable quadrant widget

Also added:

- `mobile_app/pubspec.yaml`
- `mobile_app/analysis_options.yaml`
- `mobile_app/README.md`

## Important Runtime Behavior

### Startup dependency preparation

1. Backend starts.
2. `check_and_prepare_dependencies()` runs before server startup.
3. OS is predicted.
4. If Linux, distro is predicted.
5. Missing dependencies attempt best-effort install on Arch-like Linux.
6. Fallback flags are stored globally.
7. Startup continues even if installation fails.

### Pairing flow

1. Start backend.
2. Backend generates or reuses token.
3. Backend prints QR containing:

```json
{
  "ip": "<local ip>",
  "port": 8765,
  "token": "<pairing token>"
}
```

4. Mobile scans QR in Settings.
5. Mobile stores pairing locally.
6. Mobile auto-connects on later launches.

### Drawing flow

1. User double taps `Drawing`.
2. User draws on blank canvas.
3. User double taps canvas.
4. Mobile renders drawing to PNG.
5. Mobile sends PNG bytes to:

`ws://<ip>:8765?token=<token>`

6. Backend:
  - saves image
  - uploads image
  - infers intent
  - validates output
  - executes Linux action
  - returns JSON response

### Response shape

Current backend response shape:

```json
{
  "status": "success",
  "intent": "OPEN_APP",
  "message": "Opened Chrome",
  "normalized_text": "open chrome",
  "confidence": 1.0,
  "model": "gemini-fast",
  "slots": {
    "app": "chrome"
  }
}
```

This is a superset of the required format and remains mobile-friendly.

## Validation Rules Implemented

Allowed intents only:

- `OPEN_APP`
- `CLOSE_APP`
- `MINIMIZE`
- `MAXIMIZE`
- `SCREENSHOT`
- `OPEN_URL`

Validation checks:

- JSON object must exist
- `intent` must be allowed
- `slots` must be a JSON object
- `confidence` must be numeric and between `0.0` and `1.0`
- `normalized_text` must be present
- required slot checks:
  - `OPEN_APP` requires `slots.app`
  - `OPEN_URL` requires `slots.url`
- `MINIMIZE` and `MAXIMIZE` default to `target=focused`
- `CLOSE_APP` defaults to `target=focused` when no app is named

Invalid or low-confidence outputs are rejected gracefully.

## Verification Performed

### Automated checks

Executed successfully:

- `PYTHONPATH=. .venv/bin/pytest tests -q`
  - result: `8 passed`

- `PYTHONPATH=. .venv/bin/python -m compileall agent`
  - result: success

### Live backend checks

Performed and confirmed:

1. Pollinations upload contract
  - verified upload requires API key
  - verified success payload includes direct image `url`

2. Pollinations text contract
  - verified endpoint returns raw text
  - updated JSON extraction to tolerate extra trailing text

3. Live AI smoke test
  - generated a sample image with `opn chrme`
  - backend produced:
    - `intent = OPEN_APP`
    - `slots.app = chrome`
    - `normalized_text = open chrome`
    - `confidence = 1.0`

4. Live WebSocket smoke test
  - started server locally
  - connected with valid token
  - sent binary bytes
  - received JSON response successfully

## Constraints and Caveats

### Flutter tooling

Flutter was not installed in this workspace, so I could not run:

- `flutter pub get`
- `flutter analyze`
- `flutter run`

The full Dart source and package manifest are present, but host scaffolding still needs to be generated on a machine with Flutter:

```bash
cd mobile_app
flutter create . --platforms=android,ios
flutter pub get
flutter run
```

The mobile README explains the Android/iOS permission requirements for QR scanning and plain `ws://` development traffic.

### Linux dependencies

For full Stage 0 desktop execution, the machine should have:

- `wmctrl`
- `scrot` for screenshots or Pillow available
- `xdg-open`
- target app executables available in `PATH`

### Intent quality

The system is functional, but image understanding quality still depends on:

- drawing clarity
- device camera/render quality
- how distorted the writing is

The validation layer prevents bad execution when confidence is too low.

## Future Scope

### Immediate next improvements

1. Add explicit app alias normalization table in AI validation
   - e.g. `chrme -> chrome`
   - `yt -> youtube`
   - `calc -> calculator`

2. Add desktop-side confirmation sounds or optional TTS
   - useful for blind users after action execution

3. Add screenshot return path or preview support to mobile
   - currently only success message is returned

4. Add connection status hints directly on the home screen
   - currently shown in Settings

5. Add retry/backoff tuning on mobile reconnects

### Accessibility and UX next steps

1. Voice mode implementation
2. Braille mode input/output
3. Spoken success/failure feedback
4. Haptic pattern differentiation for:
   - connected
   - sent
   - success
   - failure

### Backend next steps

1. Local OCR + local NLU fallback
   - reduces cloud dependence further

2. Better window targeting
   - focused window title resolution
   - app-aware minimize/maximize on Linux

3. Safer execution policy
   - allowlist apps/URLs
   - optional confirmation on risky actions

4. Add structured logging for:
   - upload latency
   - model latency
   - execution latency

5. Add integration tests for end-to-end WebSocket + intent + executor flow

## Files Added or Updated

### Added

- `.gitignore`
- `agent/utils/env.py`
- `agent/utils/dependency_check.py`
- `agent/core/nova_stage0.py`
- `agent/stage0/__init__.py`
- `agent/stage0/pairing.py`
- `agent/stage0/pipeline.py`
- `agent/stage0/validation.py`
- `agent/stage0/executor.py`
- `mobile_app/pubspec.yaml`
- `mobile_app/analysis_options.yaml`
- `mobile_app/README.md`
- `mobile_app/lib/main.dart`
- `mobile_app/lib/models/pairing_config.dart`
- `mobile_app/lib/services/pairing_store.dart`
- `mobile_app/lib/services/nova_socket_service.dart`
- `mobile_app/lib/widgets/quadrant_tile.dart`
- `mobile_app/lib/screens/home_screen.dart`
- `mobile_app/lib/screens/drawing_screen.dart`
- `mobile_app/lib/screens/settings_screen.dart`
- `mobile_app/lib/screens/qr_pairing_screen.dart`
- `tests/test_stage0_validation.py`
- `tests/test_stage0_executor.py`
- `tests/test_stage0_pairing.py`
- `tests/test_dependency_check.py`

### Updated

- `agent/main.py`
- `agent/platform/adapter.py`
- `agent/platform/linux.py`
- `agent/platform/macos.py`
- `agent/platform/windows.py`
- `agent/server/websocket_handler.py`
- `agent/utils/config.py`
- `agent/utils/logger.py`
- `requirements.txt`

## Final State

Stage 0 is now implemented as a working backend plus a source-complete Flutter client for the draw-to-action flow.

The most important success case was verified live:

`opn chrme` -> `OPEN_APP` -> `chrome`

The remaining gap is mobile host scaffolding/runtime verification on a machine with the Flutter SDK installed.
