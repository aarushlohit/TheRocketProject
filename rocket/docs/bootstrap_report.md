# Bootstrap Report

Status: plan only. Bootstrap was not implemented or run.

## Proposed Bootstrap

```text
Rocket Bootstrap
Installing Memory...
Installing Skills...
Installing MCP...
Installing Prompt...
Installing OAuth...
Collecting Profile...
Done.
```

## One-Time Marker

```json
{
  "rocket_initialized": true,
  "version": "phase2",
  "completed_at": "<iso timestamp>"
}
```

## Proposed Stores

| Store | Purpose |
|---|---|
| `data/rocket/bootstrap_state.json` | One-time marker. |
| `data/rocket/RocketProfile.db` | Encrypted user profile. |
| `prompts/rocket_system.txt` | Rocket execution policy. |
| `prompts/rocket_intent.txt` | Intent domain routing examples. |
| `rocket_skills/` | Rocket-specific skills. |

## Security Position

- Use DPAPI-protected key material on Windows.
- Use AES-256 for profile database content.
- Keep OAuth terminal-only.
- Pin all MCP package versions.
- Ask only for high-risk actions under trusted mode.

## Not Done

- No bootstrap code.
- No profile database.
- No OAuth flow.
- No MCP install.
- No skills install.
- No OpenWork modification.

## Failure Assumptions

- OpenWork may fail, so RocketAdapter must fall back to RocketAgent.
- Shokunin may fail, so memory must fall back to RocketMemory.
- Playwright MCP may fail, so browser automation must fall back to native Playwright.
- pywinauto may fail, so desktop automation must fall back to Python UIAutomation.
- Skills may fail, so Rocket must keep a tiny local verifier/recovery path.
