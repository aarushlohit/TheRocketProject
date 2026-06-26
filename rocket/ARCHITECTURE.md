# Rocket — Architecture & Module Map

Companion to `HANDOFF.md`. Describes every module the next engineer will touch.
Architecture is FROZEN; this documents what exists.

## Data flow (one command)
1. **Phone** sends voice/braille/drawing over WebSocket.
2. **`agent/server/websocket_handler.py`** receives it, routes by type:
   - `audio` -> `adapter.process_audio`
   - `drawing` / binary -> `adapter.process_image`
   - `braille` -> `adapter.process_braille`
   - `profile` / `setup` / `permission_response` -> state updates
3. **Perception (`agent/adapters/`)** turns raw input into a compiled *mission* (JSON string):
   - `speech.py` `SpeechManager`: faster-whisper -> Google SR -> Riva. Returns transcript.
   - `vision.py` `VisionManager`: Kimi K2.6 (fallback extraction path only).
   - `nemotron.py` `NemotronAdapter`: orchestrates. For audio, compiles transcript directly.
     For drawing (direct mode), saves image + returns a `DRAWING` mission with `image_path`.
4. **Mission model (`agent/runtime/browser_state.py`)**: `compile_browser_mission`,
   `predict_browser_state`, `parse_mission`, `mission_to_task`, `task_display_text`.
   The mission JSON has: intent, context, mission, success_criteria, instructions,
   browser_state, predicted_browser_state, verifier, recovery, (optional) image_path.
5. **`agent/runtime/mission_brief.py`**: `build_mission_brief` (MISSION/CONTEXT/GOAL/DONE WHEN),
   `window_policy`, `cleanup_policy`.
6. **Quality gate (`agent/server/task_quality.py`)**: rejects vague/garbage before execution.
7. **Execution (`agent/runtime/adapter.py` `RocketAdapter.execute`)**:
   `run_with_recovery(task, opencode.execute, verifier_suite)`:
   - `OpenCodeCliClient.execute` runs `opencode` (via PowerShell) with the prompt + (for
     drawings) the image as `--file`.
   - `apply_verifier` runs the matching reality verifier; its verdict is authoritative.
   - On failure, `RecoveryEngine` picks the next strategy and retries + re-verifies.
8. **Feedback**: `agent/runtime/terminal_bridge.py` returns a dict to the websocket; the
   `speech` field is sanitized by `agent/runtime/phone_speech.py` (natural language only).

## Module reference
| Module | Responsibility |
|--------|----------------|
| `agent/main.py` | Entry point; boots bootstrap, first-launch, websocket server, dashboard |
| `agent/adapters/speech.py` | Speech-to-text chain (faster-whisper primary) |
| `agent/adapters/vision.py` | Kimi K2.6 vision extraction (fallback path) |
| `agent/adapters/nemotron.py` | Perception orchestrator (audio/image/braille -> mission) |
| `agent/adapters/pollinations.py` | Text fallback parser |
| `agent/runtime/browser_state.py` | Mission compilation + browser session model |
| `agent/runtime/mission_brief.py` | Human brief + window/cleanup policy |
| `agent/runtime/adapter.py` | RocketAdapter.execute, apply_verifier, run_with_recovery |
| `agent/runtime/opencode_cli_client.py` | Runs OpenCode via PowerShell; prompt build; desktop verify |
| `agent/runtime/opencode_runtime.py` | Syncs ~/.config/opencode (agent md, MCP, plugins, vault) |
| `agent/runtime/verifier.py` | Reality verifier suite (tri-state, fail-closed) |
| `agent/runtime/recovery.py` | Recovery decision engine |
| `agent/runtime/benchmark.py` | 350-task suite + scoring (simulated executor) |
| `agent/runtime/benchmark_live.py` | Live executor wiring (real RocketAdapter); inert until armed |
| `agent/runtime/first_launch.py` | First-launch onboarding, encrypted prefs, component detection |
| `agent/runtime/memory.py` | DPAPI-encrypted SQLite profile/kv store |
| `agent/runtime/vault.py` | DPAPI secret vault |
| `agent/runtime/security.py` | DPAPI protect/unprotect |
| `agent/runtime/phone_speech.py` | Natural-language speech sanitizer |
| `agent/runtime/terminal_bridge.py` | Bridges websocket execution to terminal + adapter |
| `agent/server/websocket_handler.py` | Authenticated WebSocket intake |
| `agent/server/task_quality.py` | Pre-execution quality gate |
| `agent/phase2/windows_mcp.py` | Rocket Windows MCP server (semantic desktop control) |
| `agent/phase2/memory_mcp.py`, `shokunin_mcp.py` | Memory MCP servers |

## Verifier dispatch (verifier.py `VerifierSuite._route`)
- install verb -> `InstallVerifier` (binary on disk only)
- "bluetooth" -> `BluetoothVerifier`; "wifi" -> `WifiVerifier`
- browser intents on known sites -> `BrowserVerifier`
- `OPEN_APP` with known context -> `ProcessVerifier`
- otherwise -> `None` => `can_verify` False => defer to executor result
Note `_is_install_request` matches install/installing/installation but NOT "installed"
(so compiled "Open installed X application" missions route to ProcessVerifier, not install).

## Test suite (204 tests)
`tests/test_verifier.py`, `test_mission_brief.py`, `test_browser_runtime.py`,
`test_first_launch.py`, `test_install_mission.py`, `test_verifier_wiring.py`,
`test_recovery.py`, `test_recovery_integration.py`, `test_benchmark.py`,
`test_benchmark_live.py`, `test_phone_speech.py`, `test_profile_migration.py`,
`test_vision_speech.py`, `test_nemotron_context.py`, `test_opencode_runtime.py`.
