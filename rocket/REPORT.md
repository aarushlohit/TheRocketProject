# Patch Report

## Scope

- Added OS-level desktop minimize support.
- Added dedicated Windows mute and unmute support through `pycaw`.
- Removed keypress-based mute handling from the active Stage 0 executor path.
- Added test coverage for the new parsing and execution routes.

## Files Changed

- `agent/platform/audio_control.py`
  - New Windows audio helper module using `pycaw` and `comtypes`.
  - Added `mute()`, `unmute()`, `is_muted()`, and volume scalar helpers.

- `agent/stage0/executor.py`
  - Added `minimize_all_windows()` using `ctypes.windll.user32.keybd_event`.
  - Added `MINIMIZE_ALL` / `SHOW_DESKTOP` execution path.
  - Replaced mute toggle logic with direct `mute()` and `unmute()` calls.

- `agent/stage0/pipeline.py`
  - Added `MINIMIZE_ALL` and `UNMUTE` to supported Stage 0 intents.
  - Added explicit resolver rules for `mute`, `unmute`, `minimize all`, and `show desktop`.

- `agent/platform/windows.py`
  - Added `show_desktop()` OS-level implementation.
  - Switched volume up/down to `pycaw` helper logic only.
  - Removed keyboard fallback for mute.
  - Added `volume_unmute()`.

- `agent/core/execution_engine.py`
  - Added `minimize_all_windows()` helper.
  - Added handlers for `MINIMIZE_ALL`, `MUTE`, and `UNMUTE`.
  - Changed `SHOW_DESKTOP` to use OS-level desktop minimize instead of `press_keys("win+d")`.

- `agent/core/intent_system.py`
  - Registered `MINIMIZE_ALL` as a valid system-level intent.

- `agent/core/verification_layer.py`
  - Added verification strategy mapping for `MINIMIZE_ALL`.

- `requirements.txt`
  - Added `comtypes` and `pycaw`.

- `tests/test_intent_system.py`
  - Updated valid intent count and expected system intent set.

- `tests/test_stage0_pipeline_api.py`
  - Added parser coverage for `unmute` and `show desktop`.

- `tests/test_stage0_executor.py`
  - Added executor coverage for `MUTE`, `UNMUTE`, and `MINIMIZE_ALL`.

## Risk Notes

- `keybd_event` is still synthetic input, but it goes through the Windows user32 API rather than `pyautogui`.
- `pycaw` is Windows-only. On non-Windows environments these actions now fail explicitly instead of silently falling back to keyboard simulation.
