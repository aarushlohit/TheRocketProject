# Risk Matrix

| Risk | Mitigation | Current Behavior |
|---|---|---|
| OpenCode CLI missing | Runtime readiness check reports `opencode=false`. | Execution fails closed. |
| Powers package missing | Verifier checks `C:\Users\Aarush\shokunin-opencode-powers`. | Execution fails closed. |
| MCP config incomplete | Verifier merges missing MCP entries. | Config is repaired before execution. |
| Plaintext token in config | Real-looking env secrets migrate to RocketVault. | Secret is removed from MCP env block and injected through process env. |
| Token already exposed | User must rotate it. | Documented security warning. |
| Workspace escape in workspace mode | Prompt and setup context constrain execution to workspace. | Permission bridge groundwork records responses. |
| Full access overreach | Full access must be explicit setup. | CLI permission bypass only applies in full mode. |
| Memory dependency unavailable | Rocket memory remains SQLite/DPAPI-backed. | Fails closed or falls back where available. |
| False completion | Prompt requires verification before concise status. | Result is recorded in execution history. |
