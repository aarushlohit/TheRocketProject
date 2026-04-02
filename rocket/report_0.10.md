# Rocket Stage 0.10 Report

## Stage 0.11 Addendum (Chat Completions Migration)

Stage 0 was upgraded from the legacy `gen.pollinations.ai/text/...` GET path to the Pollinations Chat Completions API for true multimodal OCR behavior.

New model call behavior in `agent/stage0/pipeline.py`:

- endpoint: `POST https://gen.pollinations.ai/v1/chat/completions`
- model: `gemini-fast`
- user content:
  - text: `decode and extract text`
  - image_url: uploaded Pollinations media URL

Legacy logic removed:

- URL prompt-length guard and prompt path encoding logic
- `/text` endpoint debug curl builder
- data-URL conversion helper used by older path assumptions

Pipeline behavior preserved:

- OCR text normalization remains backend-owned (`strip/lower/newline cleanup`)
- backend parser still maps text like `open chrome` to `OPEN_APP` with app extraction
- candidate ranking and safe blocking behavior remain in place

Tests in `tests/test_stage0_pipeline_api.py` were updated to validate the new POST request body/headers and failure handling for non-200 responses.

## Overview

This update stabilizes the Rocket Stage 0 backend around the real Pollinations API behavior and fixes the concrete failure mode that was breaking inference: oversized prompt strings in the `gen.pollinations.ai/text/...` URL path.

The backend now uses:

- a short Pollinations-compatible prompt
- backend-side JSON recovery instead of prompt-side schema forcing
- official Pollinations media upload for image hosting
- GET-only model inference requests
- text-first intent parsing
- candidate-based ranking and safe blocking
- full trace logging through the draw-to-action flow

## What Changed

### 1. Pollinations request path was simplified

The model prompt in `agent/stage0/pipeline.py` is now:

`extract handwritten command and return 3 possible interpretations as json`

This is intentionally short so the encoded prompt stays within a safe URL-path budget.

Added guard:

- if encoded prompt length is greater than `300`
- backend raises `StageZeroValidationError("Prompt too long for Pollinations")`

This directly addresses the 404 issue caused by oversized path prompts.

### 2. Parsing responsibility moved into the backend

The backend no longer relies on a long prompt to force perfectly formatted JSON.

Added helpers in `agent/stage0/pipeline.py`:

- `safe_json_parse(raw_text)`
- `fallback_parse(raw_text)`

Flow now is:

1. call model
2. try safe JSON parse
3. if parsing fails, fall back to plain-text candidate extraction
4. continue through validation and ranking

This makes the system more tolerant of messy or partially structured model output.

### 3. Correct API split is now enforced

The working Pollinations split in the backend is now:

- `media.pollinations.ai/upload` via `POST` for image hosting
- `gen.pollinations.ai/text/{prompt}` via `GET` for model inference

This is the production-safe combination currently implemented in the codebase.

### 4. Text-first inference remains the execution source of truth

Even when the model returns candidate objects, execution does not blindly trust model intent fields.

The backend still derives actionable intent from extracted text and then validates it before execution.

Examples:

- `open vscod` can normalize to `vscode`
- unknown apps are downgraded and blocked
- uncertain results return `UNKNOWN` and do not execute

### 5. Candidate-based reasoning was preserved

The Stage 0.10 pipeline still:

- creates image variants
  - original
  - rotated_90
  - rotated_270
- calls both models
  - `gemini-fast`
  - `qwen-vision`
- combines all candidates
- ranks them
- blocks execution if no candidate clears threshold

### 6. Trace logging was retained and aligned

Trace logs now cover:

- `INPUT IMAGE`
- `VARIANTS`
- `FINAL PROMPT`
- `MODEL REQUEST URL`
- `MODEL STATUS`
- `MODEL RAW RESPONSE`
- `ALL CANDIDATES`
- `TEXT EXTRACTED`
- `DERIVED INTENT`
- `APP DETECTED`
- `RANKING SCORES`
- `FINAL SELECTION`
- `EXECUTION PLAN`
- `FINAL RESULT`

API keys remain masked in trace output.

## Files Changed

### `agent/stage0/pipeline.py`

Main Stage 0.10 work happened here.

Implemented:

- short prompt for Pollinations URL compatibility
- prompt-length safety check
- backend JSON recovery helpers
- official media upload path
- GET model requests
- trace logging for prompt/request/response lifecycle
- preserved candidate-based multi-variant inference

### `agent/stage0/validation.py`

Kept text-first parsing and tightened safety behavior:

- URL-like extracted text remains `OPEN_URL`
- invalid app detections are nulled in debug info
- unknown `OPEN_APP` targets degrade safely to `UNKNOWN`

### `agent/core/nova_stage0.py`

Retained the safer Stage 1 behavior:

- blocked responses for uncertain intent
- dry-run aware execution flow
- final result trace logging
- context memory for previously opened app

### `agent/stage2/ranker.py`

Kept candidate ranking in place and used it as the final selection layer.

### `requirements.txt`

Updated runtime dependency list to include:

- `requests==2.33.1`

### Tests Added / Updated

- `tests/test_stage0_pipeline_api.py`
- `tests/test_nova_stage0.py`

Updated coverage now validates:

- GET model call shape
- prompt-length safety guard
- official media upload flow
- backend parse fallback
- blocked result for unknown intent

## Verification

### Automated

Executed:

- `PYTHONPATH=. .venv/bin/pytest -q`
  - result: `51 passed`

- `PYTHONPATH=. .venv/bin/python -m compileall agent`
  - result: success

### Live smoke checks

Executed live checks against Pollinations using the local API key:

1. short prompt + real model endpoint
   - result: `200`
   - confirms the prompt-path 404 issue is fixed

2. official media upload + short prompt
   - upload succeeded
   - model request returned `200`

Important note:

- On the synthetic handwritten smoke image, the upstream model response was generic rather than a clean OCR candidate list.
- That means URL compatibility is fixed, but handwriting interpretation quality still depends on upstream model behavior.
- The Rocket backend now handles that safely by parsing candidates conservatively and blocking uncertain execution.

## Outcome

Stage 0.10 fixes the concrete Pollinations request failure while keeping the backend safer and more observable than before.

The backend is now stronger in three practical ways:

1. it no longer breaks on oversized prompt URLs
2. it recovers from imperfect model formatting in backend code
3. it keeps uncertain handwriting from executing dangerous actions

## Future Scope

The next improvements that would most increase real-world reliability are:

- calibrate image preprocessing for OCR-specific handwriting inputs
- compare `gemini-fast` vs `qwen-vision` on real user scribbles
- capture structured telemetry for candidate failure reasons
- optionally cache uploaded media URLs for replay/debugging
- add an OCR fallback before Pollinations for stubborn handwritten samples
