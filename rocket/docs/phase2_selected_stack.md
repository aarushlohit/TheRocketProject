# Phase 2 Selected Stack

## Final Decision

Rocket Phase 2 should use only five major technologies.

| Layer | Selected Technology | Why |
|---|---|---|
| Agent runtime | OpenWork + OpenCode | Already vendored. Provides sessions, skills, MCP config, approvals, todos, and event streaming. |
| Memory | Shokunin / Fork_shokunin | Persistent memory, freshness decay, claim verification, long-term preferences. |
| Browser automation | Playwright MCP | Accessibility snapshots, forms, tabs, downloads, uploads, cookies, high maintenance confidence. |
| Desktop automation | pywinauto | Python-native Windows UIA/Win32 automation by semantic controls, low complexity. |
| Skills and verifier | Rocket custom skills on OpenCode native skills | Keeps Rocket blind-first, concise, trust-aware, and recoverable. |

## Explicit Non-Selections

| Technology | Decision | Reason |
|---|---|---|
| FlaUI-MCP | Defer | Promising but adds .NET/MCP complexity. Use later if pywinauto cannot cover a class of Windows apps. |
| Windows MCP / MCP-Windows | Defer | Overlaps pywinauto; unclear maintenance and API stability. |
| AutoIt MCP | Avoid for MVP | Too close to coordinate/mouse fallback, not blind-first semantic automation. |
| Python UIAutomation | Defer | Useful as pywinauto fallback, not a separate first install. |
| VoltAgent awesome-agent-skills | Research only | Catalog is too large; install curated skills only. |
| Skillful | Defer | Native OpenCode skills are enough until Rocket has many skills. |
| Awesome MCP | Research only | Index, not runtime dependency. |
| Anti-bot browser projects | Avoid | Rocket should use normal accessibility/browser APIs, not bypass protections. |

## Phase 2 Runtime Shape

```text
Voice / Drawing / Braille
  -> Nemotron
  -> Task String
  -> RocketAdapter
  -> OpenWork/OpenCode session
  -> Rocket skills
  -> Memory
  -> MCP tools
  -> pywinauto / Playwright
  -> Verifier skill
  -> RocketTerminal status
```

## RocketAdapter Contract

```python
class RocketAdapter:
    def execute(self, task: str) -> RocketExecutionResult:
        ...
```

Required behavior:

- Accept the existing task string unchanged.
- Start or reuse OpenWork backend runtime.
- Send a concise execution prompt to an OpenCode session.
- Apply Rocket trust policy before destructive actions.
- Stream concise progress to RocketTerminal.
- Verify action completion before reporting success.

## Trust Policy

Default: `trusted`.

Trusted may execute:

- Open apps
- Search
- Downloads
- Forms
- Settings
- Explorer
- VSCode
- Browser actions
- Software install discovery and normal installers

Always ask before:

- Payments
- Banking
- Account deletion
- Factory reset
- Deleting many files
- Irreversible destructive operations

## Verifier Strategy

Do not build a separate verifier framework first.

Use:

- Playwright MCP accessibility snapshot for browser state.
- pywinauto/UIA tree for Windows app state.
- Rocket `verifier` skill for expected-state checks.
- OpenCode todos/session status for plan progress.

This keeps verification semantic and blind-first.
