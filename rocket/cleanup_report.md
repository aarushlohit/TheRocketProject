# Cleanup Report

## Deleted Files

Major deleted architecture:

- `agent/core/`
- `agent/stage0/`
- `agent/stage2/`
- `agent/platform/`
- `agent/skills/`
- `agent/nlu/`
- `agent/server/http_api.py`
- `tests/`
- `scripts/`
- `mobile_app/nova/`
- `mobile_app/lib/services/backend_api_service.dart`
- `mobile_app/lib/widgets/confirmation_overlay.dart`
- `WINDOW_CONTROL_REPORT.md`

Important deleted files:

- `agent/core/autonomous_os.py`
- `agent/core/planner.py`
- `agent/core/execution_engine.py`
- `agent/core/execution_controller.py`
- `agent/core/execution_verifier.py`
- `agent/core/verification_layer.py`
- `agent/core/feedback_manager.py`
- `agent/core/intent_system.py`
- `agent/core/intent_refiner.py`
- `agent/core/intelligent_pipeline.py`
- `agent/core/unified_pipeline.py`
- `agent/core/hardened_pipeline.py`
- `agent/core/nova_stage0.py`
- `agent/core/websocket_contract.py`
- `agent/stage0/executor.py`
- `agent/stage0/pairing.py`
- `agent/stage0/pipeline.py`
- `agent/stage0/validation.py`
- `agent/stage2/ranker.py`
- `agent/platform/window_control.py`
- `agent/platform/windows.py`
- `agent/platform/windows_ui.py`
- `agent/platform/audio_control.py`
- `agent/platform/input_safe.py`
- `agent/skills/registry.py`
- `agent/skills/skill_open_app.py`
- `agent/nlu/parser.py`
- `agent/nlu/gesture_recognizer.py`

## Deleted Classes And Services

- `NovaStageZeroAgent`
- Stage 0 pipeline classes and helpers
- Autonomous OS processor and intent router
- Execution engine/controller/verifier
- Confirmation manager
- Feedback manager
- Trust and verification layers
- Semantic UI generator
- Platform adapters for Windows, Linux, and macOS control
- Skill registry and skill executor abstractions
- HTTP `/process`, `/confirm`, and `/status` API
- Flutter HTTP backend service
- Flutter confirmation overlay

## Deleted Modules

- Deterministic planner modules
- Legacy executor modules
- Verification modules
- Stage 0, Stage 1-style, and Stage 2 remnants
- Task routing and intent refinement modules
- OpenClaw/autonomous OS remnants
- Duplicate nested Flutter app in `mobile_app/nova`
- Obsolete tests that validated removed automation behavior

## Deleted Imports

Removed active imports of:

- `agent.core.*`
- `agent.stage0.*`
- `agent.stage2.*`
- `agent.platform.*`
- `agent.skills.*`
- `agent.nlu.*`
- `pyautogui`
- `pywinauto`
- `pywin32`
- `pyttsx3`
- `comtypes`
- `pycaw`
- Flutter `http`
- Flutter `provider`

## Dependency Graph

```text
mobile_app
  -> NovaSocketService
  -> websocket
  -> RocketWebSocketServer
  -> NemotronAdapter
      -> NVIDIA Integrate OpenAI-compatible API
      -> PollinationsAdapter fallback
  -> RocketTerminal
      -> Rich display
      -> generated task only

RocketLabs/nemotron
  -> NemotronAdapter
  -> isolated sample validation

external/openwork
  -> vendored only
  -> no imports
  -> no build
  -> no runtime integration
```

## Preserved

- Active Flutter app.
- Drawing canvas.
- Voice feedback through `flutter_tts`.
- Haptics.
- Braille user flow.
- QR scanner.
- Pairing store.
- Websocket communication.
- Pollinations fallback.
- Accessibility onboarding helpers.

## Potential Risks

- Nemotron multimodal audio/image content format may need adjustment if NVIDIA changes OpenAI-compatible payload support.
- A valid `NVIDIA_API_KEY` is required for primary model validation.
- Pollinations fallback can only infer a task from text context when the primary multimodal call fails.
- The old automation tests were removed with the automation layer; new end-to-end hardware/mobile tests should be added after Phase 2 boundaries are approved.
- Windows case-insensitive filesystems may show the requested `report.md` as a modification to the previously tracked `REPORT.md`.
