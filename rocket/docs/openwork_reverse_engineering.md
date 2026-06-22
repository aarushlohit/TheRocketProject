# OpenWork Reverse Engineering

Scope: documentation only. No OpenWork files were modified.

## Executive Summary

OpenWork is a desktop and server wrapper around OpenCode. For Rocket Phase 2, the clean integration point is not the OpenWork UI. It is the OpenWork server/orchestrator path that starts OpenCode, exposes sessions, manages skills, stores MCP configuration, streams events, and handles approvals.

Rocket should treat OpenWork as an invisible backend runtime:

`Rocket task string -> RocketAdapter -> OpenWork/OpenCode session prompt -> Skills/MCP/tools -> verification result`

## Key Local Files

| Area | File | Finding |
|---|---|---|
| Product overview | `external/openwork/README.md` | OpenWork runs OpenCode locally, supports sessions, SSE events, skills, MCP servers, permissions, templates, local/remote mode. |
| CLI host | `external/openwork/apps/orchestrator/README.md` | `openwork start --workspace <path> --approval auto` is the CLI-first host path. It can run without the desktop UI and has `--no-tui` / `serve` modes. |
| Embedding seam | `external/openwork/apps/server/src/embedded.ts` | Exposes `startEmbeddedServer(options)`, can manage an OpenCode child process, returns URL, port, config, and stop handle. |
| Server entry | `external/openwork/apps/server/src/index.ts` | Exports `startEmbeddedServer`, `startServer`, and config resolution. |
| Server core | `external/openwork/apps/server/src/server.ts` | Registers routes, creates OpenCode client, manages runtime config, MCP sync, approvals, skills, commands, workspace import/export, sessions. |
| Approvals | `external/openwork/apps/server/src/approvals.ts` | `ApprovalService` supports `auto` mode and manual pending approvals with timeout. |
| MCP | `external/openwork/apps/server/src/mcp.ts` | Reads global/project/runtime MCP entries; runtime MCPs are stored by OpenWork and injected into OpenCode. |
| Skills | `external/openwork/apps/server/src/skills.ts` | Lists project/global skills from `.opencode/skills`, `.claude/skills`, `.agents/skills`, and supports upsert/delete. |
| Commands | `external/openwork/apps/server/src/commands.ts` | Commands are markdown files under `.opencode/commands`. |
| Sessions | `external/openwork/apps/server/src/routes/sessions.ts` | Uses `@opencode-ai/sdk/v2/client` to list, create, read snapshots, messages, todos, and delete sessions. |
| Runtime config DB | `external/openwork/apps/server/src/runtime-opencode-config-store.ts` | SQLite-backed runtime config for `default_agent`, plugins, MCP, permissions, providers. |
| Workspace paths | `external/openwork/apps/server/src/workspace-files.ts` | Project config conventions: `opencode.json/jsonc`, `.opencode/openwork.json`, `.opencode/skills`, `.opencode/commands`. |
| Desktop runtime | `external/openwork/apps/desktop/electron/runtime.mjs` | Electron starts the runtime, selects ports, manages server tokens, launches OpenWork server and OpenCode. |
| Desktop IPC | `external/openwork/packages/types/src/desktop-ipc.ts` | Typed command map includes runtime lifecycle, skills, MCP auth, computer use, UI bridge, and filesystem utilities. |

## Component Map

| Requested Item | OpenWork Reality |
|---|---|
| Main Agent | OpenCode is the actual agent engine. OpenWork hosts and configures it. |
| Planner | OpenCode session todos are exposed through session snapshots and form the visible plan/timeline. |
| Executor | OpenCode executes tools/MCP/skills. OpenWork manages runtime and config. |
| MCP | Runtime MCP config lives in OpenWork server SQLite and is pushed into OpenCode. |
| Skills | `.opencode/skills/<name>/SKILL.md` is the native project skill path. Global skill paths are also supported. |
| Memory | No Rocket-specific memory is present. OpenWork has runtime SQLite for config, not long-term user memory. Add memory as a Phase 2 dependency. |
| Verifier | No standalone verifier module found. Use a Rocket verifier skill plus tool-state reads from Playwright/pywinauto. |
| Prompt Loading | OpenCode reads system/agent behavior from config, commands, and skills. OpenWork voice has its own realtime instructions in `server.ts`. |
| Agent Loop | OpenCode session loop, exposed through server routes and SSE events. |
| Approval Hooks | `ApprovalService` with `auto` mode and pending request flow. |
| Permission Hooks | Runtime OpenCode config supports permission entries, especially external directory permission. |
| Tool Registry | OpenCode MCP registry plus OpenWork runtime MCP map. |
| Context Registry | Workspace/session state, session groups, snapshots, authorized folders, runtime config. |

## Rocket Integration Recommendation

Do not embed the OpenWork desktop UI. Use one of two backend-only paths:

1. Preferred first integration: spawn `openwork start --workspace <rocket_workspace> --approval auto --no-tui` or `openwork serve`.
2. Later embedded integration: call `startEmbeddedServer()` from a Node sidecar if Rocket needs tighter lifecycle control.

RocketAdapter should:

1. Ensure bootstrap marker exists.
2. Ensure OpenWork server is running.
3. Create or reuse a Rocket OpenCode session.
4. Send the task string as the session prompt.
5. Stream status/todos/events to RocketTerminal.
6. Return concise status to mobile.

## Risks

- Windows support in OpenWork README is not positioned as the free default path. Rocket may need direct source/runtime use rather than relying on packaged Windows desktop.
- OpenWork is TypeScript/Node/OpenCode based while Rocket backend is Python. Use a process boundary first, not in-process imports.
- Approval auto mode must be constrained by Rocket trust policy, not blindly enabled for destructive actions.
- MCP servers are high-privilege supply-chain dependencies. Phase 2 should pin versions and install only a small set.

## References

- OpenWork local README: `external/openwork/README.md`
- OpenWork orchestrator README: `external/openwork/apps/orchestrator/README.md`
