# Rocket Bootstrap Plan

Scope: plan only. No installer or bootstrap code was implemented.

## Bootstrap Rule

Run once only.

Marker:

```text
rocket_initialized=true
```

Suggested marker location:

```text
data/rocket/bootstrap_state.json
```

## Terminal Output

```text
Rocket Bootstrap
Installing Memory...
Installing Skills...
Installing MCP...
Installing Prompts...
Collecting Profile...
OAuth Setup...
Done.
```

## Installation Order

1. Check marker.
2. Create Rocket data directory.
3. Create encrypted profile store.
4. Install prompt files.
5. Install Rocket custom skills.
6. Install memory layer.
7. Configure minimal MCP entries.
8. Configure OpenWork/OpenCode workspace.
9. Optional OAuth setup.
10. Write marker.

## Profile Collection

Collect once:

- Name
- Preferred name
- Email
- Phone
- Address
- Country
- Browser
- Editor
- Speech speed
- Accessibility mode
- Trust level

Storage target:

```text
data/rocket/RocketProfile.db
```

Encryption plan:

- Windows DPAPI for local key protection.
- AES-256 for profile rows.
- No plaintext profile export by default.

## Prompts

Create once:

```text
prompts/rocket_system.txt
prompts/rocket_intent.txt
```

`rocket_system.txt` policy:

- Blind-first.
- Less interruptions.
- Never chat.
- Prefer execution.
- Prefer local tools.
- Use memory.
- Use skills.
- Use MCP.
- Verify actions.
- Recover failures.
- Announce concise progress.
- Respect trust level.
- Never expose internals.

`rocket_intent.txt` maps task strings to execution domains:

- `Open Chrome` -> DesktopIntent
- `Search cats on YouTube` -> BrowserIntent
- `Install VSCode` -> InstallerIntent
- `Read PDF` -> DocumentIntent

## Skills

Create only curated Rocket skills:

```text
rocket_skills/
  accessibility_forms/
  browser_download/
  document_reader/
  emergency_stop/
  recovery/
  screen_describer/
  software_installer/
  verifier/
  winget/
```

Defer:

- Gmail
- Spotify
- Slack
- Calendar
- Broad third-party skill catalogs

## MCP

Install only:

- Playwright MCP
- pywinauto desktop automation MCP or thin Rocket wrapper
- Memory MCP, if Shokunin exposes it cleanly

Defer:

- GitHub MCP
- Google MCP
- Slack MCP
- Calendar MCP
- Filesystem MCP beyond approved Rocket workspace

## OAuth

Terminal-only prompts:

```text
Enable Gmail? [y/n]
Enable Spotify? [y/n]
Enable Calendar? [y/n]
```

If yes:

1. Open browser.
2. Complete OAuth.
3. Store token in encrypted profile/token store.
4. Confirm done.

## Bootstrap Safety

- Never run automatically after marker exists.
- Never install unpinned MCP packages.
- Never enable broad filesystem access without explicit profile trust.
- Never ask repeated setup questions after profile is collected.
