# Bootstrap Report

Rocket bootstrap now means OpenCode powers verification.

## Verified Assets

- `C:\Users\Aarush\.config\opencode\opencode.json`
- `C:\Users\Aarush\.config\opencode\plugins\superpowers.js`
- `C:\Users\Aarush\.config\opencode\skills\superpowers`
- `C:\Users\Aarush\.shokunin\memory\mcp-server.py`
- `C:\Users\Aarush\.shokunin\scripts\chroma-helper.py`

## Behavior

- Missing MCP entries are merged from `C:\Users\Aarush\shokunin-opencode-powers\opencode.json`.
- Existing customized MCP entries are preserved.
- Full access sets OpenCode permission to `allow`.
- Workspace mode sets OpenCode permission to `ask` and runs CLI tasks inside the configured workspace.
- Real-looking MCP env secrets are migrated into `data/rocket/phase2/RocketVault.json`.

## Security

Do not keep real tokens in `opencode.json`. Rotate any token that was already stored there in plaintext.
