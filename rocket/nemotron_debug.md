# Nemotron Debug

Observed issue:

`Unauthorized`

Most likely causes:

- `NVIDIA_API_KEY` is missing in the shell that starts RocketTerminal.
- `.env` has not been loaded from the repository root.
- The key does not have access to NVIDIA Integrate hosted inference.
- The request is using a non-NVIDIA base URL.
- The model name is misspelled or not enabled for the account.
- The OpenAI-compatible SDK is too old.

Expected configuration:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)
```

Model:

`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`

Headers:

The OpenAI SDK sends `Authorization: Bearer <NVIDIA_API_KEY>`.

Phase 1 implementation:

- Uses `AsyncOpenAI`.
- Uses `base_url="https://integrate.api.nvidia.com/v1"`.
- Reads `NVIDIA_API_KEY`.
- Disables reasoning in the task parser call.
- Falls back to Pollinations `mistral-small-3.2` when Nemotron fails.
- Pollinations fallback reads `POLLINATIONS_API_KEY` and sends it as `?key=...` when available.

Validation result on this machine:

- Nemotron returned auth failure because `NVIDIA_API_KEY` was not present.
- Pollinations fallback returned `401 Unauthorized` without `POLLINATIONS_API_KEY`.
- The adapter paths are wired, but live model validation is blocked until credentials are provided.

Debug command:

```powershell
$env:NVIDIA_API_KEY="your_key"
python RocketLabs/nemotron/braille_test.py
```

If it still returns 401, regenerate or re-scope the NVIDIA key in NVIDIA Integrate and verify the model is available to the account.
