# Rocket V3 Architecture

```text
Flutter App
  -> Voice / Drawing / Braille capture
  -> WebSocket
  -> Nemotron Omni intent parser
  -> Context-enriched executable task
  -> RocketTerminal display
  -> OpenCode runtime verifier
  -> OpenCode CLI
  -> MCP / skills / memory / desktop automation
```

## Runtime Boundary

Rocket keeps perception and execution separate:

- Phase 1 turns user input into one executable task.
- Runtime setup verifies global OpenCode powers before execution.
- Execution uses OpenCode CLI only.
- Shokunin memory and Rocket memory provide persistent context.
- Workspace mode is the default first-run access mode.

## OpenCode Powers

Rocket treats `C:\Users\Aarush\shokunin-opencode-powers` as the source package and `C:\Users\Aarush\.config\opencode` as the global OpenCode config directory.

The verifier syncs:

- `plugins/superpowers.js`
- `skills/superpowers`
- `~\.shokunin\memory\mcp-server.py`
- `~\.shokunin\scripts\chroma-helper.py`
- missing MCP entries from the powers package config

## Secrets

Credentials must not live in plaintext `opencode.json`. Rocket migrates real-looking MCP env secrets into the local DPAPI-backed vault and passes them to OpenCode through the subprocess environment.

Rotate any token that was previously stored directly in `opencode.json`.
