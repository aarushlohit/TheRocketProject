# Stack Decision

## Implemented Runtime Stack

| Layer | Selection | Status |
|---|---|---|
| Agent runtime | OpenCode CLI only | Implemented |
| Powers source | `C:\Users\Aarush\shokunin-opencode-powers` | Implemented |
| Config source | `C:\Users\Aarush\.config\opencode` | Implemented |
| Memory | Shokunin memory MCP plus Rocket SQLite/DPAPI memory | Implemented |
| Desktop/browser automation | OpenCode MCP servers and installed skills | Configured |
| Trust | Workspace mode by default, full access by explicit setup | Implemented groundwork |
| Secrets | Rocket DPAPI vault, injected into OpenCode env | Implemented |

## Decision

Rocket no longer uses OpenWork as an active runtime or fallback. Nemotron produces the intent, Rocket verifies the global OpenCode powers install, and OpenCode CLI executes the task.

The global powers package provides the main MCP and skill catalog. Rocket preserves user-customized OpenCode config entries, adds missing required entries, and migrates real-looking env secrets out of `opencode.json`.

## Configuration

- `ROCKET_PHASE2_ENABLED=0` disables execution.
- `ROCKET_OPENCODE_COMMAND=opencode.cmd` selects the CLI executable.
- `ROCKET_OPENCODE_MODEL=nvidia/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` selects the OpenCode model.
- `C:\Users\Aarush\.config\opencode\opencode.json` is the global config Rocket verifies.
- `data/rocket/phase2/RocketVault.json` stores protected secret values.

## Security Note

Any token previously committed or stored directly in `opencode.json` should be rotated. Rocket can remove/migrate plaintext values from future config reads, but it cannot make an already-exposed token safe again.
