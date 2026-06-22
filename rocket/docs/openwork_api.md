# OpenWork API Investigation

Scope: research only. No OpenWork source was modified.

## Decision

OpenWork can be used as a backend, but Rocket should treat it as a process boundary, not as a library inside the Python backend.

Recommended Phase 2 path:

```text
RocketAdapter
  -> start/reuse OpenWork Orchestrator or OpenWork server
  -> create/reuse OpenCode session
  -> send task as prompt
  -> read session snapshot/todos/events
  -> report status to RocketTerminal
```

## Questions

| Question | Answer | Evidence |
|---|---|---|
| Can planner be called? | Indirectly yes. | OpenCode session todos are exposed through session snapshot routes. OpenWork does not expose a separate planner function. |
| Can executor be called? | Indirectly yes. | OpenCode is the execution engine. OpenWork starts/configures it and exposes sessions. |
| Can MCP registry be called? | Yes. | `apps/server/src/mcp.ts` supports list/add/remove/toggle for runtime MCP entries. |
| Can skills registry be called? | Yes. | `apps/server/src/skills.ts` lists/upserts/deletes `.opencode/skills/<name>/SKILL.md`. |
| Can verifier be called? | No direct verifier API found. | Use Rocket `verifier` skill plus Playwright/pywinauto state checks. |
| Can memory be injected? | Yes, as a skill/MCP/runtime config, not native Rocket memory. | Runtime MCP config and skills can inject memory tools/instructions. |
| Can prompts be injected? | Yes. | OpenCode commands/skills/config are prompt injection points; OpenWork uses `.opencode` workspace files. |
| Can agent loop be called? | Yes, through OpenCode session prompt APIs. | `routes/sessions.ts` uses `@opencode-ai/sdk/v2/client` for sessions. |
| Can approvals be bypassed? | Yes, with auto approval mode, but Rocket must constrain this. | `ApprovalService` returns allowed in `auto` mode. |
| Can chat UI be bypassed? | Yes. | OpenWork Orchestrator and server paths are CLI/server first; UI is not required. |
| Can OpenWork work as backend? | Yes, with risk. | `startEmbeddedServer()` exists; `openwork start/serve` also exists. |

## Highest-Risk Findings

- OpenWork is OpenCode-powered. Rocket should not assume internal planner/executor APIs exist as stable named modules.
- Windows packaging support may be less mature than Linux/macOS, so Rocket should start with CLI/process integration and keep a fallback RocketAgent.
- OpenWork can run approvals in auto mode, but Rocket must implement trust filtering before sending risky tasks.
- MCP sync is best-effort in the OpenWork server. Rocket must verify tool availability before relying on it.

## Fallback Gate

If OpenWork fails to start, cannot expose a session, or cannot load MCP/skills:

```text
RocketAgent
  -> tiny planner
  -> tiny verifier
  -> tiny executor
  -> pywinauto / native Playwright
```

Fallback must preserve the Phase 1 task pipeline.

## Local Files Reviewed

- `external/openwork/README.md`
- `external/openwork/apps/orchestrator/README.md`
- `external/openwork/apps/server/src/embedded.ts`
- `external/openwork/apps/server/src/server.ts`
- `external/openwork/apps/server/src/mcp.ts`
- `external/openwork/apps/server/src/skills.ts`
- `external/openwork/apps/server/src/routes/sessions.ts`
- `external/openwork/apps/server/src/approvals.ts`
- `external/openwork/apps/server/src/runtime-opencode-config-store.ts`
- `external/openwork/packages/types/src/desktop-ipc.ts`
