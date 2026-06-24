# Phase 2 Stack Analysis

Status: historical research. The selected runtime is now OpenCode CLI only; see `docs/stack_decision.md`.

Goal: choose the smallest practical stack that gives Rocket roughly 90-95% blind-first desktop automation capability without installing 20 frameworks.

## Evaluation Table

| Technology | Category | Complexity | Coverage | Maintenance | Compatibility | Install | Reason | Example |
|---|---:|---:|---:|---:|---:|---|---|---|
| OpenWork + OpenCode | Agent runtime | Medium | High | High | Excellent | YES | Already vendored; provides sessions, skills, MCP, approvals, todos, runtime config. | Send task to OpenCode session and stream todos. |
| Shokunin / Fork_shokunin | Memory | Medium | High | Medium | Good | YES | Best fit for persistent memory, freshness decay, and claim verification. | Remember preferred browser and verify claims before reuse. |
| pywinauto | Desktop automation | Low | High | High | Excellent | YES | Python-native, Windows-first, supports Win32 and UIA backends, low integration cost. | Find a Save button by title/control and invoke it. |
| Python UIAutomation | Desktop automation | Medium | High | Medium | Good | NO | Useful fallback for raw UIA tree access, but pywinauto should cover MVP. | Inspect deep accessibility tree when pywinauto wrapper fails. |
| FlaUI | Desktop automation | High | High | High | Fair | NO | Strong .NET UIA library, but adds C#/.NET integration burden. Keep as later fallback. | WPF installer automation by AutomationId. |
| FlaUI-MCP / win-ui MCP variants | Desktop MCP | Medium | Medium | Unclear | Fair | NO | Promising but young; not the first dependency for a blind-first MVP. | Click Next by accessible name. |
| Windows MCP / MCP-Windows | Desktop MCP | Medium | Medium | Unclear | Fair | NO | Overlaps with pywinauto; maintenance and API stability unclear. | Window focus and file navigation. |
| AutoIt MCP | Desktop fallback | Medium | Medium | Medium | Fair | NO | Coordinate/mouse-heavy fallback risk; avoid for primary blind accessibility. | Legacy app click fallback. |
| Playwright MCP | Browser automation | Low | Very high | High | Excellent | YES | Official Microsoft MCP server, accessibility snapshots, no screenshot dependence. | Search YouTube and play first result. |
| Official MCP servers | MCP baseline | Low | Medium | High | Excellent | SELECTIVE | Use only needed reference servers: filesystem/github later if required. Avoid broad install. | Filesystem read/write in approved workspace. |
| Awesome MCP index | Discovery | Low | N/A | N/A | N/A | NO | Index only; useful for research, not runtime dependency. | Compare candidate MCPs. |
| Agent Skills | Skills | Low | Medium | Medium | Good | SELECTIVE | Good source of production skills, but install only curated skills. | Verification/debugging skill. |
| VoltAgent awesome-agent-skills | Skills index | Low | High | Medium | Good | NO | Huge catalog, useful for discovery but too broad to install. | Find a Gmail skill candidate. |
| Skillful | Skill loader | Medium | Medium | Medium | Good | DEFER | Lazy loading is attractive, but OpenCode has native skills. Defer until skill count is high. | Discover skills by keyword. |
| Rocket custom skills | Skills | Low | Very high | High | Excellent | YES | Needed for blind-first policy, trust rules, verifier, recovery, installers. | `software_installer`, `browser_download`, `emergency_stop`. |

## Source Notes

- Playwright MCP exposes browser automation through structured accessibility snapshots, avoiding screenshot-only control: https://github.com/microsoft/playwright-mcp and https://playwright.dev/docs/getting-started-mcp
- pywinauto supports Windows GUI automation through Win32 and Microsoft UI Automation backends: https://github.com/pywinauto/pywinauto
- FlaUI is a .NET UI Automation wrapper for Win32, WinForms, WPF, Store Apps: https://github.com/FlaUI/FlaUI
- Shokunin advertises freshness decay, claim verification, persistent memory, and MCP tools: https://github.com/EliasOulkadi/shokunin
- OpenCode supports native on-demand Agent Skills: https://opencode.ai/docs/skills/
- Model Context Protocol reference servers are indexed at: https://github.com/modelcontextprotocol/servers

## Recommendation

Use five major technologies:

1. OpenWork/OpenCode as the agent runtime.
2. Shokunin as memory.
3. Playwright MCP as browser automation.
4. pywinauto as desktop automation.
5. Rocket custom skills as policy, verification, and recovery layer.

Do not install FlaUI-MCP, Windows MCP variants, AutoIt MCP, VoltAgent catalog, Awesome MCP catalog, or anti-bot browser projects in Phase 2.
