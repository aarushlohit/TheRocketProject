# Patch Report

## Scope

- Added OS-level desktop minimize support.
- Added deterministic maximize-all window control for visible application windows.
- Added dedicated Windows mute and unmute support through `pycaw`.
- Added lightweight deterministic runtime context memory for app-reference resolution.
- Added deterministic `SAVE_FILE` intent with regex filename parsing, context-aware app targeting, and OS-level save execution.
- Reworked `SAVE_FILE` execution to use safe wrapped `pyautogui` input with focus-first behavior and retry.
- Removed keypress-based mute handling from the active Stage 0 executor path.
- Added test coverage for the new parsing and execution routes.

## Files Changed

- `agent/platform/audio_control.py`
  - New Windows audio helper module using `pycaw` and `comtypes`.
  - Added `mute()`, `unmute()`, `is_muted()`, and volume scalar helpers.

- `agent/stage0/executor.py`
  - Added `minimize_all_windows()` using `ctypes.windll.user32.keybd_event`.
  - Added `MINIMIZE_ALL` / `SHOW_DESKTOP` execution path.
  - Added `MAXIMIZE_ALL` execution path with debug logging and affected-window count.
  - Added dedicated `SAVE_FILE` execution path using OS-level save controls with strict app guard.
  - Replaced mute toggle logic with direct `mute()` and `unmute()` calls.
  - Added safe blocking for app-targeted window actions when no app is resolved from explicit input or context.

- `agent/core/context_manager.py`
  - New lightweight runtime context manager.
  - Tracks `current_app`, `last_app`, `last_intent`, `last_text`, and `last_target`.
  - Resolves app references deterministically from current session context only.
  - Keeps `last_app` populated after successful app interactions and exposes a global `context` singleton alias.

- `agent/platform/input_safe.py`
  - New guarded `pyautogui` wrapper module.
  - Added `safe_hotkey()`, `safe_write()`, and `safe_press()` with delay and retry behavior.

- `agent/platform/save_file_control.py`
  - New Windows guarded save helper.
  - Added `focus_app(app_name)` using `pygetwindow` with a foreground delay.
  - Reworked save execution to focus app, send `Ctrl+S`, wait for dialog, type filename via safe wrapper, and confirm with `Enter`.
  - Added retry-once behavior and administrator warning when wrapped input fails.

- `agent/stage0/pipeline.py`
  - Added `MINIMIZE_ALL`, `MAXIMIZE_ALL`, `UNMUTE`, and `SAVE_FILE` to supported Stage 0 intents.
  - Added explicit resolver rules for `mute`, `unmute`, `minimize all`, `show desktop`, `maximize all`, `maximize everything`, and `save`.
  - Added pronoun-slot stripping for app-targeted intents such as `close it` and `restore that`.
  - Added context-based app resolution before intent execution and explicit `[CONTEXT INJECTED]` logging for injected targets.
  - Added regex-based filename extraction for `save file test.txt` / `save report.txt`.

- `agent/platform/window_control.py`
  - Added `maximize_all_windows()` using `win32gui.EnumWindows`.
  - Ignores hidden windows and empty-title windows automatically.

- `agent/platform/windows.py`
  - Added `show_desktop()` OS-level implementation.
  - Switched volume up/down to `pycaw` helper logic only.
  - Removed keyboard fallback for mute.
  - Added `volume_unmute()`.

- `agent/core/execution_engine.py`
  - Added `minimize_all_windows()` helper.
  - Added handlers for `MINIMIZE_ALL`, `MAXIMIZE_ALL`, `MUTE`, `UNMUTE`, and `SAVE_FILE`.
  - Changed `SHOW_DESKTOP` to use OS-level desktop minimize instead of `press_keys("win+d")`.

- `agent/core/nova_stage0.py`
  - Initialized shared runtime context access for the live Stage 0 agent.
  - Updates context only after successful execution.
  - Emits context debug state after updates.

- `agent/core/intent_system.py`
  - Registered `MINIMIZE_ALL` and `MAXIMIZE_ALL` as valid system-level intents.
  - Registered `SAVE_FILE` as a valid input control intent.

- `agent/core/verification_layer.py`
  - Added verification strategy mapping for `MINIMIZE_ALL`, `MAXIMIZE_ALL`, and `SAVE_FILE`.

- `requirements.txt`
  - Added `comtypes` and `pycaw`.

- `tests/test_intent_system.py`
  - Updated valid intent count and expected system intent set.

- `tests/test_stage0_pipeline_api.py`
  - Added parser coverage for `save`, `save file test.txt`, `save it`, plus existing context-aware commands.

- `tests/test_stage0_executor.py`
  - Added executor coverage for `SAVE_FILE` with and without filenames, safety blocking without a resolved app, and failure when focus cannot be established.

- `tests/test_nova_stage0.py`
  - Added coverage for Stage 0 context updates after successful execution, including persistent `last_app`.

## Risk Notes

- `keybd_event` is still synthetic input, but it goes through the Windows user32 API rather than `pyautogui`.
- `pycaw` is Windows-only. On non-Windows environments these actions now fail explicitly instead of silently falling back to keyboard simulation.
- Context memory is process-local runtime state only. It is intentionally lightweight and does not persist across restarts or provide long-term memory.
- `SAVE_FILE` now blocks if the target app cannot be focused. There is intentionally no fallback to the currently focused window.
- `SAVE_FILE` now depends on `pygetwindow` for focus and `pyautogui` for guarded input, so reliability still depends on desktop session accessibility and foreground-window permissions.
