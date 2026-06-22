# Phase 2 Stack Decision

## Final Stack

| Layer | Primary | Fallback |
|---|---|---|
| Agent runtime | OpenWork + OpenCode | RocketAgent |
| Memory | Fork_shokunin / Shokunin | RocketMemory SQLite + JSON + DPAPI |
| Desktop automation | pywinauto | Python UIAutomation |
| Browser automation | Playwright MCP | Native Playwright |
| Skills | OpenCode native skills + Rocket skills | `rocket_skills/` only |
| Verifier | Rocket verifier skill | Local verifier checks |

## Decision Gate

Use OpenWork if all are true:

- Starts from terminal without UI.
- Creates or reuses an OpenCode session.
- Accepts a task prompt without user text entry.
- Loads Rocket skills.
- Loads selected MCP tools.
- Exposes enough session state to verify progress.

Fallback to RocketAgent if any are false.

## Why This Stack

- Smallest stack that covers most Windows desktop and browser automation.
- Accessibility APIs first.
- By name and by control, not pixels.
- Python remains the desktop automation path.
- OpenWork stays invisible.
- Existing Rocket Phase 1 pipeline remains frozen.

## Explicit Non-Selections

- Do not install FlaUI in MVP.
- Do not install Windows MCP variants in MVP.
- Do not install AutoIt MCP in MVP.
- Do not install anti-bot browser projects.
- Do not install broad skill catalogs blindly.
- Do not build MCP Store UI.

## RocketAgent Fallback

If OpenWork is not viable:

```text
RocketAgent
  planner: split task into 1-5 semantic steps
  executor: pywinauto / native Playwright / shell-safe commands
  verifier: read UIA tree or browser accessibility snapshot
  memory: RocketMemory
```

RocketAgent must be deliberately tiny and must not become a second architecture.
