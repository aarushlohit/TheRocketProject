# Phase 2 Risk Matrix

| Risk | Impact | Likelihood | Mitigation | Fallback |
|---|---:|---:|---|---|
| OpenWork server fails on Windows | High | Medium | Use process boundary, health checks, version pinning. | RocketAgent. |
| OpenCode session API changes | High | Medium | Wrap in RocketAdapter, keep contract small. | Local planner/executor/verifier. |
| MCP server fails to install | Medium | High | Pin versions, verify tool list after bootstrap. | Native library wrapper. |
| Playwright MCP unavailable | Medium | Medium | Test browser tool availability during bootstrap. | Native Playwright. |
| pywinauto fails on app | Medium | Medium | Prefer UIA backend and semantic selectors. | Python UIAutomation. |
| Shokunin integration fails | Medium | Medium | Treat memory as optional capability. | RocketMemory SQLite + DPAPI. |
| Prompt injection through web content | High | High | Keep Rocket system prompt, trust policy, verifier. | Ask confirmation for risky actions. |
| Over-permissive trusted mode | High | Medium | Hard block payments, banking, account deletion, factory reset, mass delete. | Strict confirmation. |
| Skill supply-chain risk | High | Medium | Curate Rocket skills, avoid broad catalog installs. | Local `rocket_skills/` only. |
| False success report | High | Medium | Always verify with UIA/accessibility snapshot. | Report uncertain state, recover. |
| Blind user interruption overload | Medium | High | Trusted default, concise status only. | Batch confirmations only for high-risk actions. |
| Automation clicks wrong control | High | Medium | Use accessibility names/control types, no pixels. | Ask user or abort. |

## Hard Rules

- No pixel clicking as primary automation.
- No anti-bot bypass projects.
- No hidden destructive actions.
- No broad filesystem access without trust policy.
- No Phase 3 UI work in Phase 2.
