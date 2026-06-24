# Cleanup Report

## Current Architecture

```text
mobile_app
  -> NovaSocketService
  -> RocketWebSocketServer
  -> NemotronAdapter
  -> RocketTerminal
  -> agent.runtime
  -> OpenCode CLI
```

## Cleanup Decisions

- Removed OpenWork from the active runtime path.
- Removed OpenWork startup scripts.
- Moved active execution code from `agent/phase2` to `agent/runtime`.
- Kept `agent/phase2` only for MCP compatibility modules referenced by OpenCode config.
- Replaced stale project docs with OpenCode-only architecture notes.
- Added backend tests for runtime config merge, vault migration, and Nemotron context.

## Preserved

- Flutter app and onboarding flow.
- QR pairing and WebSocket transport.
- Nemotron and Pollinations adapters.
- RocketTerminal rich terminal UI.
- Shokunin memory and Rocket Windows MCP entrypoints.

## Follow-Up

- Add real phone-side permission approval UI.
- Add OAuth/vault credential management.
- Add an end-to-end test that starts backend, pairs mobile, and executes a harmless OpenCode workspace task.
