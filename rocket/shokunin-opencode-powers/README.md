# Shokunin OpenCode Powers

**One directory. Copy it. Instant god mode.**

Everything you need to turn OpenCode into a fully-loaded AI development powerhouse. 13 MCP servers, 14 superpowers skills, persistent memory, and full system access.

## What's Inside

```
shokunin-opencode-powers/
├── opencode.json              # Drop-in config (merge with yours)
├── install.ps1                # One-click Windows installer
├── mcp-servers/
│   └── shokunin-memory/       # Persistent memory (ChromaDB + ONNX)
│       ├── mcp-server.py      # MCP server (7 tools)
│       └── chroma-helper.py   # CLI for memory management
├── skills/
│   ├── superpowers.js         # Plugin (auto-injects into every session)
│   └── superpowers/           # 14 agentic skills
│       ├── brainstorming/
│       ├── test-driven-development/
│       ├── systematic-debugging/
│       ├── executing-plans/
│       ├── verification-before-completion/
│       ├── dispatching-parallel-agents/
│       ├── subagent-driven-development/
│       ├── writing-plans/
│       ├── writing-skills/
│       ├── requesting-code-review/
│       ├── receiving-code-review/
│       ├── finishing-a-development-branch/
│       ├── using-git-worktrees/
│       └── using-superpowers/
└── README.md                  # You are here
```

## Quick Start

```powershell
# Option 1: Run the installer
.\install.ps1

# Option 2: Manual copy
Copy-Item -Recurse shokunin-opencode-powers ~/.config/opencode/
# Then merge opencode.json with your existing config
```

Restart OpenCode. Done.

## MCP Servers (13)

| Server | Tools | What It Does |
|--------|-------|--------------|
| **shokunin-memory** | 7 | Persistent memory across sessions (ChromaDB + ONNX embeddings) |
| **github** | — | GitHub repos, PRs, issues, code search |
| **google-workspace** | 80+ | Gmail, Docs, Sheets, Slides, Drive, Calendar, Tasks, Forms |
| **claude-screen** | 12 | Screen capture, OCR, region screenshots, screen recording |
| **playwright** | — | Browser automation, screenshots, form filling |
| **computer-use** | — | Mouse/keyboard control, desktop interaction |
| **obsidian** | 15 | Read/write/search/manage Obsidian vault notes |
| **darbot-windows** | 50+ | Windows automation, clipboard, processes, registry |
| **weather** | — | Weather queries, forecasts, conditions |
| **mcp-notifications** | — | Desktop notifications (Windows/macOS/Linux) |
| **mcp-personal-suite** | 49 | Productivity tools, messaging, notes, calendar |
| **neo-mcp** | — | AI task automation (needs API key) |
| **youtube** | — | YouTube API (needs OAuth re-auth) |

## Skills (14 Superpowers)

| Skill | Purpose |
|-------|---------|
| brainstorming | Structured ideation and exploration |
| test-driven-development | Write tests first, implement after |
| systematic-debugging | Methodical bug hunting |
| executing-plans | Step-by-step plan execution |
| verification-before-completion | Always verify before marking done |
| dispatching-parallel-agents | Multi-agent parallel workflows |
| subagent-driven-development | Delegate to sub-agents |
| writing-plans | Create structured development plans |
| writing-skills | Create new reusable skills |
| requesting-code-review | Ask for code review |
| receiving-code-review | Process review feedback |
| finishing-a-development-branch | Clean branch completion |
| using-git-worktrees | Git worktree workflows |
| using-superpowers | Meta-skill for using superpowers |

## Persistent Memory

The **shokunin-memory** MCP server gives OpenCode a brain that persists across sessions:

```
# Via MCP tools (in chat):
store_context(project="my-app", content="User prefers TypeScript")
search_context(query="user preferences", project="my-app")
get_session_summary(project="my-app")

# Via CLI (in terminal):
python ~/.shokunin/scripts/chroma-helper.py count
python ~/.shokunin/scripts/chroma-helper.py search "typescript"
python ~/.shokunin/scripts/chroma-helper.py stats
```

## API Keys Setup

Some servers need API keys. Edit `~/.config/opencode/opencode.json`:

| Server | Key Needed | How to Get |
|--------|-----------|------------|
| github | `GITHUB_PERSONAL_ACCESS_TOKEN` | github.com/settings/tokens |
| neo-mcp | `NEO_SECRET_KEY` | app.heyneo.so |
| youtube | OAuth credentials | `npx @eat-pray-ai/yutu auth` |
| obsidian | Vault path | Set your Obsidian vault path |

## Testing

```powershell
# Test all MCP servers
python scripts/test-mcp-servers.py

# Test individual server
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python ~/.shokunin/memory/mcp-server.py
```

## Requirements

- **OpenCode** (opencode.ai)
- **Python 3.10+** with `pip`
- **Node.js 18+** with `npm`
- **Git**

## Credits

- [OpenCode](https://opencode.ai) - The AI development environment
- [Superpowers](https://github.com/obra/superpowers) - Agentic skills framework (231K stars)
- [ModelContextProtocol](https://modelcontextprotocol.io) - MCP server ecosystem
- [ChromaDB](https://www.trychroma.com) - Vector database for persistent memory

## License

MIT - Do whatever you want with it.
