# Rocket Stage 0.9 Report

## Overview

This update upgrades the Rocket Stage 0 backend into a Stage 1 reliability-oriented pipeline.

The main objective of this pass was not adding new user-facing features. It was making the system safer, more observable, and much harder to misuse when AI output is wrong or handwriting is rotated or unclear.

The backend now:

- preprocesses images before inference
- evaluates multiple orientations instead of trusting one image
- applies a strict intent guard after AI parsing
- refuses low-confidence or suspicious app predictions
- supports `UNKNOWN` intent safely
- checks app availability before launch
- stays fully observable in terminal logs
- keeps dry-run behavior for safe debugging
- supports app normalization and availability checks for Windows, Linux, and macOS

## Goal Achieved

The Stage 1 reliability system now follows these principles:

- never blindly trust AI
- always validate and correct intent
- handle rotated handwriting
- never crash on execution failures
- expose the full reasoning path in terminal logs

## Key Files Updated

### `agent/stage0/pipeline.py`

This is the biggest Stage 1 upgrade.

Changes made:

- added PIL-based preprocessing
- created 3 variants per input image:
  - original
  - rotated 90
  - rotated 270
- saved each variant to disk under the variants directory
- ran inference on all variants
- kept both model passes:
  - `gemini-fast`
  - `qwen-vision`
- logged every variant attempt
- collected all inference candidates
- added `select_best_result(results)`
- returned safe `UNKNOWN` when all valid candidates fail

New data structures:

- `InferenceCandidate`
  - one model run on one image variant

- `InferenceResult`
  - final selected candidate plus candidate history

### `agent/stage0/validation.py`

This file now performs stricter intent validation and safety correction.

Changes made:

- added `UNKNOWN` to allowed intents
- added `KNOWN_APPS`:
  - `chrome`
  - `firefox`
  - `calculator`
  - `terminal`
  - `vscode`
- added `guard_intent(intent)`
- added `build_unknown_intent(...)`
- canonicalized app names before execution

Reliability behavior:

- if app is not in `KNOWN_APPS`
  - confidence is reduced to `0.5`
  - result is treated as uncertain

- if confidence drops below `0.6`
  - result becomes `UNKNOWN`
  - message becomes `Uncertain intent`

- if AI already returns `UNKNOWN`
  - result remains non-executable
  - confidence is kept low

This means the backend no longer trusts any app prediction just because it parses correctly.

### `agent/core/nova_stage0.py`

This file now exposes the whole inference and selection flow clearly.

New logs added:

- `[INPUT IMAGE]`
- `[AI RAW OUTPUT]`
- `[PARSED JSON]`
- `[SELECTED RESULT]`
- `[NORMALIZED INTENT]`
- `[EXECUTION PLAN]`
- `[EXECUTION RESULT]`

Also added:

- safe short-circuit for `UNKNOWN`
- no execution happens when intent is uncertain
- structured response is returned instead of a wrong action

### `agent/stage0/executor.py`

Execution safety was improved significantly.

Changes made:

- platform-aware app normalization before execution
- app availability check before `OPEN_APP`
- kept no-crash execution wrapper
- preserved dry-run mode
- added cross-platform `is_available(cmd, platform_type)`

Execution safety behavior:

- normalize app first
- if the app cannot be found:
  - return:
    - `status: error`
    - `message: App not installed`
- do not call platform execution in that case

Dry-run behavior remains:

- if debug mode is enabled:
  - do not execute
  - log `[DRY RUN]`
  - return structured debug result

### `agent/utils/app_map.py`

This file was expanded into a Stage 1 app-normalization layer.

Added:

- canonical app mapping
- platform-specific normalization
- support for:
  - Linux
  - Windows
  - macOS

Canonical user-facing names now support:

- calculator
- chrome / google chrome
- firefox
- spotify
- terminal
- vscode / vs code / visual studio code / code

Cross-platform normalized launch targets now include:

### Linux

- `calculator -> gnome-calculator`
- `chrome -> google-chrome-stable`
- `firefox -> firefox`
- `spotify -> spotify-launcher`
- `terminal -> x-terminal-emulator`
- `vscode -> code`

### Windows

- `calculator -> calc`
- `chrome -> chrome`
- `firefox -> firefox`
- `spotify -> spotify`
- `terminal -> wt`
- `vscode -> code`

### macOS

- `calculator -> Calculator`
- `chrome -> Google Chrome`
- `firefox -> Firefox`
- `spotify -> Spotify`
- `terminal -> Terminal`
- `vscode -> Visual Studio Code`

## Prompt Hardening

The system prompt in `agent/stage0/pipeline.py` was strengthened.

It now explicitly tells the model:

- handwriting may be rotated 90 or 270 degrees
- never hallucinate app names or intent
- lower confidence if unclear
- prefer `UNKNOWN` when uncertain
- return strict JSON only

This improves both safety and rotation robustness.

## Stage 1 Runtime Behavior

### 1. Input image handling

When a drawing arrives:

1. save original image
2. create rotated variants
3. upload each variant
4. run inference on each
5. parse and validate each response
6. apply strict guard rules
7. select the best valid result
8. execute only if safe and not `UNKNOWN`

### 2. Selection logic

`select_best_result(results)` now:

- filters valid candidates only
- sorts by confidence descending
- returns the best valid result

If nothing valid remains:

- return `UNKNOWN`
- confidence `0.4`
- message `Could not determine intent`

### 3. Wrong app protection

If AI predicts an app outside the known allowlist, execution is not trusted.

Example:

- AI says: `OPEN_APP -> spotify`
- `spotify` is not in `KNOWN_APPS`
- confidence forced to `0.5`
- result converted to `UNKNOWN`
- no execution occurs

This intentionally prioritizes false negatives over dangerous false positives.

### 4. Unknown intent behavior

When the backend is uncertain, it now returns a safe structured result instead of guessing.

Example:

```json
{
  "status": "error",
  "intent": "UNKNOWN",
  "message": "Could not determine intent",
  "confidence": 0.4
}
```

Or for guarded low-confidence cases:

```json
{
  "status": "error",
  "intent": "UNKNOWN",
  "message": "Uncertain intent",
  "confidence": 0.5
}
```

## Logging Output

The terminal output is now much more observable.

A typical successful debug flow now looks like:

```text
[INPUT IMAGE]
data/stage0/drawings/received/drawing_....png

[VARIANT TEST]
original

[AI RAW OUTPUT]
{ raw text from model }

[PARSED JSON]
{ parsed JSON object }

[SELECTED RESULT]
{ variant, model, confidence, message }

[NORMALIZED INTENT]
{ intent, slots, confidence }

[EXECUTION PLAN]
Action: OPEN_APP | Params: {'app': 'chrome'}

[DRY RUN]
Would execute: OPEN_APP with {'app': 'google-chrome-stable'}

[EXECUTION RESULT]
Dry run executed
```

This makes debugging and failure diagnosis much easier.

## No-Crash Policy

This update preserves and strengthens the no-crash policy.

Current behavior:

- execution errors are caught
- invalid model responses are caught
- low-confidence results become `UNKNOWN`
- missing apps return structured errors
- non-executable results do not reach platform execution
- the backend does not raise runtime exceptions from the executor path

## Cross-Platform Support

This update explicitly improves support for:

- Windows
- Linux
- macOS

Important note:

- Stage 1 reliability support is cross-platform
- app normalization is cross-platform
- app-availability checking is cross-platform
- safe error returns are cross-platform

Platform-specific execution depth still varies by adapter:

- `OPEN_APP` and `OPEN_URL` are currently the strongest cross-platform paths
- some advanced window-management actions still remain Linux-first or safely stubbed on other OSes
- when unsupported on Windows/macOS, execution errors are still safely captured and returned as structured errors

This means Windows is now supported as a primary reliability target for app normalization and launch safety, even where some non-launch actions remain partially implemented.

## Tests Added and Updated

### Added

- `tests/test_stage1_pipeline.py`
  - verifies best-result selection
  - verifies all-invalid case returns no selected valid candidate

### Expanded

- `tests/test_stage0_validation.py`
  - unknown-intent builder
  - known-app guard downgrade behavior

- `tests/test_stage0_executor.py`
  - app-not-installed safety case
  - dry-run behavior
  - safe execution failure handling

- `tests/test_app_map.py`
  - canonical app mapping coverage

## Verification Run

Executed successfully:

- `PYTHONPATH=. .venv/bin/pytest tests -q`
  - result: `19 passed`

- `PYTHONPATH=. .venv/bin/python -m compileall agent`
  - result: success

## Success Criteria Mapping

### Case 1: Rotated `open chrome`

Now supported through:

- rotated image variants
- multi-result selection
- cross-platform normalization

Expected path:

- multiple rotations tested
- highest-confidence valid result selected
- `OPEN_APP` selected
- normalized app used for target OS

### Case 2: Messy unclear drawing

Now protected through:

- strict confidence guard
- allowlisted apps
- `UNKNOWN` fallback

Expected path:

- candidate confidence drops
- result becomes `UNKNOWN`
- no wrong execution

### Case 3: App not installed

Now protected through:

- pre-execution availability check

Expected path:

- normalize app
- detect missing executable/app
- return:
  - `status: error`
  - `message: App not installed`

## Final Summary

Stage 0.9 transforms the backend from a single-pass inference executor into a safer Stage 1 reliability system.

The most important improvements are:

- rotated multi-pass inference
- best-result selection
- strict intent guarding
- safe `UNKNOWN` fallback
- pre-execution app availability checks
- detailed full-path terminal observability
- cross-platform normalization for Windows, Linux, and macOS

This makes the backend substantially safer against wrong AI output and much easier to debug in real-world handwritten input conditions.
