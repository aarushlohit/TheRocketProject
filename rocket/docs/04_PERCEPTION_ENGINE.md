# Perception Engine

Primary model:

`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`

Endpoint:

`https://integrate.api.nvidia.com/v1`

Environment:

`NVIDIA_API_KEY`

Fallback:

Pollinations chat completions with `mistral-small-3.2`.

Adapter contract:

- `process_image(bytes) -> str`
- `process_audio(bytes) -> str`
- `process_braille(str) -> str`

The returned string is the only Phase 1 artifact sent to RocketTerminal.
