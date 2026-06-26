# Rocket — Runbook

Operational commands. Companion to `HANDOFF.md` / `ARCHITECTURE.md`.
All paths assume repo root `C:\Users\Aarush\Myoffice\TheRocketProject\rocket`.
Use the venv Python (`.\.venv\Scripts\python.exe`) — that is where runtime deps are installed.

## Start the backend
```powershell
$env:NVIDIA_API_KEY="<key>"
.\.venv\Scripts\python.exe -m agent.main --host 0.0.0.0 --port 8765
```
Expect health: Nemotron / KimiVision / Speech = configured. WebSocket on ws://0.0.0.0:8765.

## Tests, lint, types
```powershell
python -m unittest discover -s tests          # 204 tests, must be OK
python -m ruff check agent tests              # must be: All checks passed!
python -m compileall agent tests              # no errors
python -m mypy agent --ignore-missing-imports # informational; pre-existing findings only
```

## Speech — isolated test (no app needed)
```powershell
.\.venv\Scripts\python.exe -c "from agent.adapters.speech import SpeechManager; s=SpeechManager(); print(s.transcribe(open(r'C:\Users\Aarush\Downloads\TEST.mp3','rb').read(), audio_format='mp3'))"
```

## Live benchmark (DESTRUCTIVE — drives the real desktop)
```powershell
$env:NVIDIA_API_KEY="<key>"; $env:ROCKET_LIVE_BENCHMARK="1"
.\.venv\Scripts\python.exe -m agent.runtime.benchmark_live
# Output: benchmark_live.json
.\.venv\Scripts\python.exe -c "import json;print(json.load(open('benchmark_live.json'))['overall'])"
```

## Fix Playwright config if it reverts to sandbox
```powershell
$cfg = Join-Path $env:USERPROFILE ".config\opencode\opencode.json"
$raw = Get-Content $cfg -Raw
$raw = $raw -replace '"npx",\s*"@playwright/mcp@latest"', '"npx", "@playwright/mcp@latest", "--browser", "chrome", "--user-data-dir", "C:\\Users\\Aarush\\AppData\\Local\\Google\\Chrome\\User Data"'
Set-Content $cfg $raw -Encoding UTF8
```

## Inspect enabled MCP servers
```powershell
$cfg = Join-Path $env:USERPROFILE ".config\opencode\opencode.json"
$j = Get-Content $cfg -Raw | ConvertFrom-Json
$j.mcp.PSObject.Properties.Name | ForEach-Object { if ($j.mcp.$_.enabled) { $_ } }
```
Expected enabled: rocket-windows, computer-use, claude-screen, playwright, shokunin-memory, google-workspace.

## Stop stuck processes
```powershell
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "benchmark_live|agent.main" } | ForEach-Object { $_.Terminate() } | Out-Null
```

## Git hygiene (CRITICAL)
- Never stage/commit `shokunin-opencode-powers/`. Verify before committing:
```powershell
git reset
git add <specific files>
git diff --cached --name-only   # confirm NO shokunin path, then commit
```
