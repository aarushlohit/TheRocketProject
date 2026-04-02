# Rocket Stage 0.5 Report

## Purpose

Stage 0.5 improves three areas of the Rocket Stage 0 backend:

1. observability
2. debugging clarity
3. execution safety and reliability

The backend is now much easier to inspect when AI inference goes wrong, when normalization changes an action, or when platform execution fails.

## Main Outcome

The system now:

- logs raw model output clearly
- logs parsed JSON clearly
- logs normalized intent clearly
- logs the execution plan before action handling
- never lets execution errors disappear silently
- returns structured error responses instead of crashing
- supports cross-platform app normalization for Linux, Windows, and macOS
- supports dry-run mode by default for safer debugging

## Files Added

### `agent/utils/app_map.py`

New cross-platform app normalization module.

Added:

- `APP_MAP` for Linux
- `WINDOWS_APP_MAP`
- `MACOS_APP_MAP`
- `normalize_app_name(name, platform_type="auto")`

This allows user-friendly names like:

- `calculator`
- `chrome`
- `google chrome`
- `spotify`
- `firefox`

to resolve into platform-specific launch names.

Examples:

- Linux:
  - `calculator -> gnome-calculator`
  - `chrome -> google-chrome-stable`

- Windows:
  - `calculator -> calc`
  - `chrome -> chrome`

- macOS:
  - `calculator -> Calculator`
  - `chrome -> Google Chrome`

## Files Updated

### `agent/core/nova_stage0.py`

Added mandatory logging inside `handle_drawing_image()`.

New logs:

#### 1. AI raw output

```python
logger.info("[AI RAW OUTPUT]")
logger.info(inference.raw_model_output)
```

#### 2. Parsed JSON

```python
logger.info("[PARSED INTENT]")
logger.info(inference.parsed_json)
```

#### 3. Normalized intent

```python
logger.info("[NORMALIZED]")
logger.info({
    "intent": inference.intent.action,
    "slots": inference.intent.parameters,
    "confidence": inference.intent.confidence,
})
```

#### 4. Execution plan

```python
logger.info("[EXECUTION PLAN]")
logger.info(f"Action: {inference.intent.action} | Params: {inference.intent.parameters}")
```

#### 5. Execution result

Added `_log_execution_result()` so the terminal clearly shows:

- success
- debug dry run
- error

This makes the execution path visible end to end.

### `agent/stage0/pipeline.py`

Expanded `InferenceResult` to carry more debugging context:

- `raw_model_output`
- `parsed_json`

The inference pipeline now returns:

- validated `Intent`
- normalized text
- raw model output
- parsed JSON object

This was necessary so `nova_stage0.py` could log the model output and parsed structure after inference completes.

### `agent/stage0/executor.py`

This file received the biggest reliability update.

#### Added app normalization before execution

If an intent includes `app`, it is normalized before platform execution:

```python
normalize_app_name(app, platform_type=self.platform_type)
```

#### Added `debug_mode`

The executor now accepts:

- `debug_mode`
- `platform_type`

When `debug_mode=True`, no actual action is executed.

Instead it logs:

```text
[DRY RUN]
Would execute: OPEN_APP with {'app': 'gnome-calculator'}
```

and returns:

```json
{
  "status": "debug",
  "message": "Dry run executed",
  "intent": "OPEN_APP"
}
```

Internally this is returned as a `Result(status="debug", ...)`, and the final mobile response stays structured.

#### Added safe execution wrapper

Execution is now wrapped in a single safe guard:

```python
except Exception as exc:
    logger.error("[EXECUTION ERROR]")
    logger.error(str(exc))
    return Result(
        status="error",
        message=str(exc),
        error_code="EXECUTION_ERROR",
    )
```

This ensures:

- no unhandled execution exceptions escape the executor
- no silent failure
- no app crash from platform action failures
- every failure becomes structured output

### `agent/utils/config.py`

Added:

- `debug_mode: bool = True`

Also wired config loading so `debug_mode` can be set in the config file:

```yaml
agent:
  host: 0.0.0.0
  port: 8765
  log_level: INFO
  debug_mode: true
```

Important behavior:

- default is now safe dry-run
- to allow real execution, set:

```yaml
agent:
  debug_mode: false
```

### `agent/core/result.py`

Added support for:

- `status="debug"`

This was necessary so dry-run responses remain first-class structured results rather than hacks or overloaded success/error responses.

### `agent/utils/logger.py`

Improved log coloring when `loguru` is available.

Configured:

- `INFO` as blue
- `ERROR` as red
- `SUCCESS` remains available through `logger.success(...)`

This improves terminal readability while debugging.

## Platform Support

This Stage 0.5 update explicitly adds app normalization support for:

- Linux
- Windows
- macOS

### Linux

Normalized names are suitable for executable-style launching:

- `gnome-calculator`
- `google-chrome-stable`
- `spotify-launcher`
- `firefox`

### Windows

Normalized names are suitable for Windows command-style launching:

- `calc`
- `chrome`
- `spotify`
- `firefox`

### macOS

Normalized names are suitable for `open -a` application names:

- `Calculator`
- `Google Chrome`
- `Spotify`
- `Firefox`

This means the backend can normalize the same user intent differently depending on the active platform.

## New Runtime Behavior

### Example log flow

For a command like handwritten:

`opn calc`

the backend now produces a much clearer terminal trace:

```text
[AI RAW OUTPUT]
{ raw model content here }

[PARSED INTENT]
{"intent":"OPEN_APP","slots":{"app":"calculator"},"confidence":0.90,"normalized_text":"open calculator"}

[NORMALIZED]
{'intent': 'OPEN_APP', 'slots': {'app': 'gnome-calculator'}, 'confidence': 0.9}

[EXECUTION PLAN]
Action: OPEN_APP | Params: {'app': 'gnome-calculator'}

[DRY RUN]
Would execute: OPEN_APP with {'app': 'gnome-calculator'}

[EXECUTION RESULT]
DRY RUN
Dry run executed
```

When dry-run is disabled and execution works:

```text
[EXECUTION RESULT]
SUCCESS
Opened Gnome-Calculator
```

When execution fails:

```text
[EXECUTION ERROR]
could not launch gnome-calculator

[EXECUTION RESULT]
could not launch gnome-calculator
```

## Reliability Improvements

### Before Stage 0.5

- execution failures could bubble up from platform code
- normalization was missing
- raw AI output was not visible in the main Stage 0 handler
- parsed JSON was not visible in the main Stage 0 handler
- debugging cross-platform app launch names was difficult

### After Stage 0.5

- every execution failure is trapped and returned as structured output
- dry-run mode makes debugging safe
- platform-specific app names are normalized consistently
- raw model output is visible
- parsed JSON is visible
- normalized intent is visible
- execution plan is visible
- execution result is visible

## Verification Performed

Executed successfully:

- `PYTHONPATH=. .venv/bin/pytest tests -q`
  - result: `13 passed`

- `PYTHONPATH=. .venv/bin/python -m compileall agent`
  - result: success

Added new test coverage for:

- Linux app normalization
- Windows app normalization
- macOS app normalization
- dry-run result behavior
- safe executor error handling

## Important Note

### Real execution is now disabled by default

This is intentional for safer debugging.

To enable real OS execution, set:

```yaml
agent:
  debug_mode: false
```

Without that change, the backend will:

- infer intent normally
- normalize intent normally
- log everything normally
- return a structured debug response
- not perform the OS action

## Files Added or Changed in Stage 0.5

### Added

- `agent/utils/app_map.py`
- `report_stage0.5.md`
- `tests/test_app_map.py`

### Updated

- `agent/core/nova_stage0.py`
- `agent/stage0/pipeline.py`
- `agent/stage0/executor.py`
- `agent/utils/config.py`
- `agent/core/result.py`
- `agent/utils/logger.py`
- `tests/test_stage0_executor.py`

## Final Summary

Stage 0.5 does not change the product goal. It changes how safe and observable the backend is while reaching that goal.

The backend now gives you:

- visible AI reasoning artifacts
- visible normalization
- visible execution plans
- visible execution outcomes
- structured error returns
- dry-run debugging
- cross-platform app normalization support

This makes Rocket Stage 0 significantly easier to debug and much safer to run during development and testing.
