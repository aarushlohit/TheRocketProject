# Rocket — Engineering Handoff

Audience: the next engineer/agent (e.g. GPT 5.5) continuing this project.
This is the single source of truth for current state. Read it fully before changing anything.

Rocket is a **blind-first autonomous desktop agent**. A Flutter phone app captures
voice / braille / drawing; a Python backend turns that into a goal and executes it on
a real Windows desktop through **OpenCode** (which drives MCP tools: Playwright,
computer-use, rocket-windows, etc.). Rocket verifies the result against observable
reality before reporting success.

```
Flutter app (voice / braille / drawing)
  -> WebSocket (agent/server/websocket_handler.py)
  -> Perception (agent/adapters: speech, vision, nemotron)
  -> Mission compile (agent/runtime/browser_state.py + mission_brief.py)
  -> RocketAdapter.execute (agent/runtime/adapter.py)
       -> OpenCode CLI (agent/runtime/opencode_cli_client.py)  [executes via PowerShell]
       -> Verifier (agent/runtime/verifier.py)                 [reality check]
       -> Recovery (agent/runtime/recovery.py)                 [heals on failure]
  -> Phone feedback (agent/runtime/phone_speech.py)            [natural speech only]
```

## Golden principle
**Rocket never trusts words. Rocket trusts reality.** OpenCode saying "done" is not
success — the verifier must confirm the goal in the real OS (process running, binary on
disk, radio actually on, page actually loaded). Unknown reality never passes.

---

## Current status (as of this handoff)

- **204 unit tests green.** `python -m unittest discover -s tests`
- **ruff clean** on `agent` and `tests`. **compileall clean.**
- Architecture is FROZEN by the product owner. Do not redesign. Only polish/fix/extend.
- The live backend has been run successfully; voice and drawing paths are wired.

### What works and is tested
1. **Verifier suite** (Slice 1) — Process/Window/Browser/Filesystem/Install/Bluetooth/Wifi,
   tri-state (True/False/None), fail-closed, zero false positives by design.
2. **Browser mission brief + policies** (Slice 2) — MISSION/CONTEXT/GOAL/DONE WHEN brief,
   window + cleanup policy.
3. **Browser runtime ownership** (Slice 2.5) — reuse/foreground/maximize/no-duplicate,
   injectable controller, singleton.
4. **First-launch bootstrap + encrypted prefs** (Slice 3) — DPAPI vault, markers, bundled
   component detection, runs once, reset option, never stores passwords.
5. **Installer missions + UAC** (Slice 4) — install proven by binary-on-disk only; UAC
   detect/announce/pause/resume; never false-completes.
6. **Verifier wired into execute()** (Slice 4.5) — verifier is authoritative for missions it
   can verify; defers to executor for the rest.
7. **Recovery engine + integration** (Slice 5 + PASS A) — ordered strategies, ask-user last,
   metrics; `run_with_recovery` loops execute->verify->recover->retry->reverify.
8. **Benchmark harness** (Slice 6) — 350-task suite, real verifier scoring, false-positive
   detection. Simulated executor for CI; **live executor** in `benchmark_live.py`.
9. **Phone speech sanitizer** (PASS B) — guarantees natural language, never JSON/internals.
10. **Speech-to-text** — `faster-whisper` (local Whisper) PRIMARY -> Google
    `speech_recognition` -> Riva -> Nemotron. Transcripts compile **locally** (no slow
    mission-compiler API call).
11. **Vision / drawing** — drawing images are sent **directly** to OpenCode's vision model
    (MIMO v2.5); no pre-extraction.
12. **OpenCode execution via PowerShell** (not cmd).

---

## Recent tuning (live-iteration fixes — IMPORTANT)

These were done while debugging the real device. Some live in code, some in the **global
OpenCode config** at `~/.config/opencode/opencode.json` (NOT in git).

### Code (committed)
- `agent/adapters/speech.py`: faster-whisper primary; robust audio handling; full fallback chain.
- `agent/adapters/nemotron.py`:
  - `process_audio`: transcript compiled **directly** via `_compile_task` (skips the
    `minimax-m3` mission compiler which was **hanging** and causing every voice command to fail).
  - `process_image`: **drawing-direct** mode (env `ROCKET_DRAWING_DIRECT`, default on) saves the
    image via `_save_drawing` and returns a `DRAWING` mission carrying `image_path`.
  - status key renamed `RivaSpeech` -> `Speech`.
- `agent/runtime/opencode_cli_client.py`:
  - `_powershell_wrap` runs `opencode` through `powershell.exe -NoProfile -Command`.
  - default command is `opencode` (PowerShell resolves it), not `opencode.cmd`.
  - DRAWING missions attach the image to `opencode run` via an extra `--file <image>` so MIMO sees it.
  - defaults: timeout 60s, persistent server ON, session reuse ON.
- `agent/server/task_quality.py`: **no longer scans `instructions`** for bad phrases. (Bug: our
  own instruction text "unambiguous" matched the bad-word "ambiguous" and rejected valid commands.)
- `agent/server/websocket_handler.py`: logs audio size/format; saves last audio to
  `~/Downloads/rocket_last_audio.wav` for debugging (consider removing for production).
- `agent/runtime/prompts.py`: **simplified** Manus-style system prompt (reuse windows, fullscreen,
  real Chrome default profile, handle popups/OTP autonomously, close after task unless media).
- `agent/runtime/opencode_runtime.py`: rocket-blind agent uses `model: opencode/mimo-v2.5-free`.
- `agent/runtime/memory.py`: added `RocketProfile.country` (fixed apply_profile AttributeError).

### Global OpenCode config (`~/.config/opencode/opencode.json`) — NOT in git, machine-local
- `model`: `opencode/mimo-v2.5-free`, `small_model`: `opencode/north-mini-code-free`.
- MCP servers ENABLED: `rocket-windows`, `computer-use`, `claude-screen`, `playwright`,
  `shokunin-memory`, `google-workspace`. Others disabled to cut latency.
- `playwright` command: `npx @playwright/mcp@latest --browser chrome --user-data-dir
  "C:\Users\Aarush\AppData\Local\Google\Chrome\User Data"` (real Chrome, default profile,
  no sandbox).
- **WARNING:** something occasionally re-serializes this file and drops the Playwright flags.
  If Playwright launches a sandbox/blank Chrome again, re-apply the `--browser chrome
  --user-data-dir` flags. A permanent fix is to have `OpenCodeRuntimeManager.ensure_ready()`
  own and enforce the Playwright MCP entry. See "Next steps".

---

## How to run

### Backend (use the venv Python — packages were installed there)
```powershell
cd C:\Users\Aarush\Myoffice\TheRocketProject\rocket
$env:NVIDIA_API_KEY="<key>"
.\.venv\Scripts\python.exe -m agent.main --host 0.0.0.0 --port 8765
```
Health table should show Nemotron / KimiVision / Speech = configured. Scan the QR from the app.

### Tests / lint
```powershell
python -m unittest discover -s tests
python -m ruff check agent tests
python -m compileall agent tests
```

### Live benchmark (drives the REAL desktop — destructive: installs apps, toggles radios)
```powershell
$env:NVIDIA_API_KEY="<key>"
$env:ROCKET_LIVE_BENCHMARK="1"
.\.venv\Scripts\python.exe -m agent.runtime.benchmark_live   # writes benchmark_live.json
```
It is INERT unless armed (`RocketAdapterExecutor(armed=True)` / the env gate). 350 tasks,
~real metrics, no fabricated numbers.

---

## Key environment variables
| Var | Default | Purpose |
|-----|---------|---------|
| `NVIDIA_API_KEY` | — | Required for OpenCode models + Kimi/Riva |
| `ROCKET_DRAWING_DIRECT` | `1` | Send drawing image straight to OpenCode (no text extraction) |
| `ROCKET_WHISPER_MODEL` | `base` | faster-whisper size: base/small/medium/large-v3 |
| `ROCKET_DISABLE_SPEECH` | — | Disable all speech-to-text |
| `ROCKET_OPENCODE_TIMEOUT_SECONDS` | `60` | Per-task OpenCode timeout (0/none = infinite) |
| `ROCKET_OPENCODE_PERSISTENT_SERVER` | `1` | Reuse one OpenCode server across tasks |
| `ROCKET_OPENCODE_REUSE_SESSION` | `1` | Reuse OpenCode session |
| `ROCKET_OPENCODE_MODELS` | (5-model list) | Comma list; first is primary (MIMO) |
| `ROCKET_RECOVERY_ENABLED` | `1` | Enable recovery loop in execute() |
| `ROCKET_RECOVERY_MAX_RETRIES` | `1` | Adapter-level recovery retries |
| `ROCKET_VERIFIER_ENABLED` | `1` | Verifier authority over OpenCode result |

---

## Known issues / honest limitations
1. **Global opencode.json is not owned by code.** Manual edits get reset. Make the runtime
   manager enforce the Playwright/MCP config.
2. **Browser-page verification is partial.** `WindowsRealityProbe` has no live `browser_state`
   source (would need Playwright/CDP), so BrowserVerifier defers for live browser missions.
   Process/install/bluetooth/wifi are fully reality-verified.
3. **Debug artifacts:** `websocket_handler.py` writes `~/Downloads/rocket_last_audio.wav` every
   voice command. Remove before shipping.
4. **mypy:** ~29 findings, almost all pre-existing in frozen modules (windows_mcp, memory_mcp,
   opencode_runtime) + missing stubs. Not blocking. Not addressed (frozen code).
5. **`RocketMemory` SQLite connections** are not explicitly closed (`with sqlite3.connect`
   commits but doesn't close). Harmless in the long-lived backend; tests use
   `TemporaryDirectory(ignore_cleanup_errors=True)`.
6. **Live benchmark latency:** each task is a full OpenCode run; expect tens of seconds each.
   Persistent server + trimmed MCP set help, but 350 live tasks is still hours.

---

## Next steps (suggested, not started)
- Make `OpenCodeRuntimeManager.ensure_ready()` own the Playwright MCP entry (flags + enabled
  set) so manual config edits stop getting lost.
- Add a real `browser_state` probe (via Playwright CDP or the computer-use tool) so
  BrowserVerifier can verify live browser missions.
- Remove the debug audio dump in `websocket_handler.py`.
- Pin `ruff`, `mypy`, `faster-whisper`, `SpeechRecognition` into `requirements-dev.txt`.
- Run the keyed live benchmark, capture `benchmark_live.json`, and analyze false positives.
- Remaining product items: MSIX installer, blind-user studies, accessibility validation, GUI.

---

## Repo conventions
- `shokunin-opencode-powers/` is a vendored directory — **leave it untracked, never commit it.**
- Commit per logical change; verify the staged set excludes shokunin before every commit.
- Keep tests green and ruff/compileall clean on every change.

See also: `ARCHITECTURE.md` (module map) and `RUNBOOK.md` (operational commands).
