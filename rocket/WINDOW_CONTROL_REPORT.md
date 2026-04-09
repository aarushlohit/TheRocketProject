# Window Control Patch Report

## Diagnosis

The Windows window-management path was using keyboard shortcuts through the adapter (`Win+Up` / `Win+Down`). That is not deterministic for target selection or state transitions, and it cannot reliably restore a specific application window.

## Root Cause

- Window state changes were delegated to keyboard automation instead of the Windows window manager.
- There was no dedicated `RESTORE_APP` intent path.
- App-specific targeting was not backed by HWND lookup.

## Fix

- Added [window_control.py](c:/Users/Prahan/Myoffice/Patent%20Project/TheRocketProject/rocket/agent/platform/window_control.py) with Win32-based `maximize_window`, `minimize_window`, and `restore_window`.
- Updated [windows.py](c:/Users/Prahan/Myoffice/Patent%20Project/TheRocketProject/rocket/agent/platform/windows.py) to use Win32 APIs for minimize/maximize/restore instead of keyboard shortcuts.
- Added `RESTORE_APP` support through the parser and executor surfaces:
  - [pipeline.py](c:/Users/Prahan/Myoffice/Patent%20Project/TheRocketProject/rocket/agent/stage0/pipeline.py)
  - [executor.py](c:/Users/Prahan/Myoffice/Patent%20Project/TheRocketProject/rocket/agent/stage0/executor.py)
  - [execution_engine.py](c:/Users/Prahan/Myoffice/Patent%20Project/TheRocketProject/rocket/agent/core/execution_engine.py)
  - [autonomous_os.py](c:/Users/Prahan/Myoffice/Patent%20Project/TheRocketProject/rocket/agent/core/autonomous_os.py)
  - [intent_system.py](c:/Users/Prahan/Myoffice/Patent%20Project/TheRocketProject/rocket/agent/core/intent_system.py)
- Added dependencies to [requirements.txt](c:/Users/Prahan/Myoffice/Patent%20Project/TheRocketProject/rocket/requirements.txt): `pywin32`, `psutil`.

## Verification

- Installed runtime deps: `pip install pywin32 psutil`
- Compiled changed modules successfully.
- Passed focused regression suite:
  - `tests/test_stage0_executor.py`
  - `tests/test_stage0_pipeline_api.py`
  - `tests/test_intent_system.py`
  - `tests/test_autonomous_os.py`
- Result: `116 passed`

## Outcome

- Minimize/maximize are now OS-level operations on Windows.
- Restore is now a first-class intent.
- App-specific window control is deterministic through process-to-HWND lookup.
