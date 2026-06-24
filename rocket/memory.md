# Rocket Memory Notes

## Current State

- Active runtime code lives in `agent/runtime`.
- `agent/phase2` remains only for compatibility MCP entrypoints.
- OpenCode CLI is the only executor.
- Runtime state is stored under `data/rocket/phase2`.
- Secrets are stored in `RocketVault.json` with DPAPI protection when available.
- Shokunin memory is synced from the global OpenCode powers package.

## Important Decisions

- Default first-run access mode is `workspace`.
- Credential onboarding supports `already_configured`, `add_now`, and `skip`.
- Real credentials should not be stored in Flutter `SharedPreferences`.
- Real MCP env secrets are migrated out of OpenCode config into RocketVault.

## Next Memory Work

- Add a user-visible vault/OAuth credential management screen.
- Add permission request history and approval expiration policy.
- Add a compact runtime dashboard in RocketTerminal.
