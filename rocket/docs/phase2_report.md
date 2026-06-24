# OpenCode Runtime Report

Status: OpenCode-only runtime implemented.

## Runtime Flow

```text
Voice / Drawing / Braille
  -> Nemotron Omni
  -> Context-aware task string
  -> RocketTerminal display
  -> Phase2TerminalBridge background worker
  -> RocketAdapter
  -> OpenCode runtime verifier
  -> OpenCode CLI
  -> MCP / skills / Shokunin memory / verification
```

## Implemented

- Removed OpenWork fallback from the active Rocket adapter path.
- Added a global OpenCode runtime verifier and repair layer.
- Synced powers from `C:\Users\Aarush\shokunin-opencode-powers`.
- Added DPAPI-backed Rocket vault for MCP env secrets.
- Added setup state for workspace/full access mode.
- Added runtime setup and permission response WebSocket message handling.
- Expanded Nemotron context with rolling history and runtime setup.
- Added tests for config merge, secret migration, and Nemotron context.

## First-Time Setup Direction

The mobile profile now carries setup fields for access mode, workspace path, credential mode, optional credential references, backup preference, and password-pattern reference. Credential mode can be `already_configured`, `add_now`, or `skip`; secrets should be entered into the backend vault or service OAuth flows, not stored in mobile shared preferences.
