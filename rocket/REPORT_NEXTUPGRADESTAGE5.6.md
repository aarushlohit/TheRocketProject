# REPORT_NEXTUPGRADESTAGE5.6

Date: 2026-04-04
Stage: 5.6
Status: Implemented
Audience: Engineers, future LLM agents, reviewers

## Goal

Upgrade Stage 5.5 into a stricter Stage 5.6 safety-first execution architecture:

1. Expand the canonical intent registry for broader OS control.
2. Add a mandatory pre-intent safety layer.
3. Emit deterministic `CONFIRMATION_REQUIRED` payloads before dangerous execution.
4. Attach accessibility-aware confirmation metadata from the user profile.
5. Preserve compatibility with the existing Stage 0 and Stage 3/5 pipeline layers.

## Summary of What Changed

### 1. Canonical Intent Registry Expanded

File:
- `agent/core/intent_system.py`

The intent system was upgraded from the older Stage 5 shape to a Stage 5.6 registry with:

- Expanded app control:
  - `RESTART_APP`
- Expanded browser control:
  - `GO_BACK`
  - `GO_FORWARD`
  - `BOOKMARK_PAGE`
- Expanded input control:
  - `UNDO`
  - `REDO`
- Expanded UI semantic control:
  - `DOUBLE_CLICK`
  - `RIGHT_CLICK`
  - `HOVER_ELEMENT`
  - `DRAG_AND_DROP`
- Expanded system control:
  - `SHUTDOWN`
  - `RESTART_SYSTEM`
  - `SLEEP`
  - `UNMUTE`
- Expanded file system control:
  - `COPY_FILE`
  - `PASTE_FILE`
  - `CREATE_FOLDER`
  - `DELETE_FOLDER`
- Expanded advanced control:
  - `LOOP`
  - `WAIT_FOR_ELEMENT`
  - `VERIFY_ELEMENT`
  - `RETRY`
  - `CONFIRMATION_REQUIRED` 

Compatibility was preserved by keeping legacy enums:

- `SCREENSHOT`
- `MINIMIZE`    
- `MAXIMIZE`
- `CLICK`

Current total valid intents:
- `65`

### 2. Validator Synced to Canonical Intents

File:
- `agent/core/json_validator.py`

Problem:
- The JSON validator had its own smaller hardcoded intent set, which could drift from the canonical system.

Fix:
- The validator now imports `VALID_INTENTS` and `REQUIRED_SLOTS` from `intent_system.py`.

Result:
- A Stage 5.6 intent cannot be valid in one layer and invalid in another.

### 3. Mandatory Pre-Intent Safety Layer Added

File:
- `agent/core/safety.py`

New capability:
- `pre_intent_safety_check(input_text, user_profile=None)`

This runs before normal intent interpretation and catches:

- destructive commands:
  - delete
  - remove
  - rm
  - format
  - erase
  - wipe
- dangerous system commands:
  - shutdown
  - restart system
  - reboot
  - lock screen
  - sleep
- file operations against sensitive system paths:
  - `C:\Windows`
  - `C:\Program Files`
  - `system32`
  - `/etc`
  - `/usr`
  - `/bin`
  - `/root`

Output contract:

```json
{
  "intent": "CONFIRMATION_REQUIRED",
  "reason": "dangerous_operation",
  "original_intent": "DELETE_FILE",
  "confidence": 1.0
}
```

Implementation detail:
- The actual payload also includes a `slots` object with:
  - `requires_confirmation`
  - `original_intent`
  - `original_slots`
  - `reason`
  - `confirmation_mode`
  - `confirmation_modes`
  - `accessibility`

This preserves internal compatibility while still exposing the strict top-level contract.

### 4. TYPE_TEXT Misuse Override Added

File:
- `agent/core/safety.py`

New capability:
- `override_type_text_misuse(intent, user_profile=None)`

Rule:
- If a `TYPE_TEXT` action contains dangerous command text or system paths, do not treat it as benign typing.
- Instead, escalate it to a safety response that behaves like a destructive file action.

Behavior:

Input:

```json
{
  "intent": "TYPE_TEXT",
  "slots": {
    "text": "rm -rf /"
  }
}
```

Output:

```json
{
  "intent": "CONFIRMATION_REQUIRED",
  "original_intent": "DELETE_FILE",
  "reason": "dangerous_operation"
}
```

Additional metadata preserved:
- `safety_override_from: "TYPE_TEXT"`
- `typed_text`

### 5. Accessibility-Aware Confirmation Metadata Added

Files:
- `agent/core/safety.py`
- existing reuse from `agent/core/user_profile.py`

New helper:
- `get_confirmation_accessibility(user_profile=None)`

Primary mode selection:
- Braille user -> `braille`
- Blind user who can hear -> `voice`
- Deaf / non-hearing user -> `haptic`
- Otherwise -> default profile feedback mode

Payload fields:
- `confirmation_mode`
- `confirmation_modes`
- `accessibility.blind`
- `accessibility.deaf`
- `accessibility.uses_braille`

This does not replace the fuller confirmation/accessibility subsystems already present in the repo.
It provides a deterministic Stage 5.6 contract at the safety decision boundary.

### 6. Intelligence Layer Reordered for Safety-First Execution

File:
- `agent/core/intelligence_layer.py`

New flow:

1. `pre_intent_safety_check(input_text, user_profile)`
2. consensus / validation
3. context priority
4. search normalization
5. multi-step shaping
6. semantic UI normalization
7. self-correction
8. final safety escalation with `apply_safety_filter`

Important behavior:
- Dangerous raw input is intercepted before normal intent optimization.
- Final safety pass still guards shaped intents and multi-step plans.
- `TYPE_TEXT` misuse is overridden even if it reaches the post-classification layer.

`apply_safety_filter` now returns:
- `CONFIRMATION_REQUIRED`

instead of the older conditional wrapper shape.

### 7. Stage 0 Runtime Path Interception Added

File:
- `agent/core/nova_stage0.py`

Problem:
- The intelligence-layer function existed, but Stage 0 orchestration could still continue into execution after OCR/intent inference.

Fix:
- `NovaStageZeroAgent.handle_drawing_image()` now runs `pre_intent_safety_check()` against `inference.normalized_text` before it sends the command into the intelligent pipeline.

If intercepted:
- the method returns a mobile-ready blocked payload
- includes confirmation/accessibility metadata
- execution planning does not begin

### 8. Intelligent Pipeline Compatibility for Confirmation Payloads

File:
- `agent/core/intelligent_pipeline.py`

New behavior:
- If `intent_data["intent"] == "CONFIRMATION_REQUIRED"`, the pipeline exits early with a blocked result instead of treating it like an ordinary intent.

This gives the runtime a safe early exit if other components pass a confirmation payload directly into the pipeline.

## Confirmation Payload Contract

Current Stage 5.6 confirmation payload shape:

```json
{
  "intent": "CONFIRMATION_REQUIRED",
  "slots": {
    "requires_confirmation": true,
    "reason": "dangerous_operation",
    "original_intent": "DELETE_FILE",
    "original_slots": {
      "path": "C:\\Windows\\System32\\drivers\\etc\\hosts"
    },
    "confirmation_mode": "voice",
    "confirmation_modes": ["voice"],
    "accessibility": {
      "mode": "voice",
      "modes": ["voice"],
      "blind": true,
      "deaf": false,
      "uses_braille": false
    }
  },
  "reason": "dangerous_operation",
  "original_intent": "DELETE_FILE",
  "confidence": 1.0,
  "confirmation_mode": "voice",
  "confirmation_modes": ["voice"],
  "accessibility": {
    "mode": "voice",
    "modes": ["voice"],
    "blind": true,
    "deaf": false,
    "uses_braille": false
  }
}
```

## Tests Updated

Files:
- `tests/test_intent_system.py`
- `tests/test_safety_stage5.py`
- `tests/test_intelligence_layer.py`

Coverage added or updated for:

- expanded Stage 5.6 intent counts and sets
- new dangerous/system intent checks
- mandatory pre-intent interception
- confirmation payload shape
- accessibility-aware confirmation modes
- TYPE_TEXT misuse override
- intelligence-layer pre-intent safety interception
- `CONFIRMATION_REQUIRED` replacing the previous conditional wrapper

## Practical Notes

### What Is Fully Implemented Now

- Canonical Stage 5.6 intent registry
- Canonical validator synchronization
- Raw text danger interception
- System path detection
- Deterministic confirmation payloads
- Accessibility metadata attachment
- TYPE_TEXT misuse override
- Stage 0 execution-path interception
- Pipeline-level confirmation-aware early exit

### What Remains a Good Next Upgrade

1. Move pre-intent safety even earlier in the OCR flow.
   - Today it runs on normalized text before execution/planning.
   - A future Stage 5.7 can separate OCR extraction from intent classification and run safety between them.

2. Teach planner/executor native implementations for the new intents.
   - Some Stage 5.6 intents are currently canonical and validated, but not all have deep executor implementations yet.
   - Priority candidates:
     - `RESTART_APP`
     - `GO_BACK`
     - `GO_FORWARD`
     - `BOOKMARK_PAGE`
     - `UNDO`
     - `REDO`
     - `DOUBLE_CLICK`
     - `RIGHT_CLICK`
     - `HOVER_ELEMENT`
     - `DRAG_AND_DROP`
     - `COPY_FILE`
     - `PASTE_FILE`
     - `CREATE_FOLDER`
     - `DELETE_FOLDER`
     - `WAIT_FOR_ELEMENT`
     - `VERIFY_ELEMENT`
     - `RETRY`

3. Unify prompt contracts across all model-call paths.
   - Some repo paths still carry older Stage 4/5 prompt wording.
   - They should converge on a shared Stage 5.6 prompt constant.

4. Connect confirmation payloads directly into the existing confirmation manager.
   - The current work exposes deterministic metadata.
   - A deeper integration can auto-dispatch the exact confirmation event through the WebSocket confirmation subsystem.

5. Extend guardrails to understand the expanded Stage 5.6 enums directly.
   - Current runtime safety is secure because dangerous commands are intercepted before planning.
   - The guardrails layer should still learn the new enums for defense in depth.

## Recommended Follow-Up Work Order

1. Shared Stage 5.6 prompt constant
2. Planner support for new enums
3. Executor support for new enums
4. Guardrail upgrade for new enums
5. OCR-before-classifier safety split
6. Confirmation manager deep integration

## Final State

The repo now has a Stage 5.6-compatible safety-first architecture:

- broader intent coverage
- deterministic confirmation-required escalation
- accessibility-aware confirmation metadata
- raw-input danger interception before planning/execution

This is a solid base for the next executor/planner upgrade pass.
