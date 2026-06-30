"""Validate WAV to executable task."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from labs.nemotron.adapter import build_adapter

_SAMPLES_DIR = Path(__file__).parent / "samples"
_OUTPUTS_DIR = Path(__file__).parent / "outputs"


async def main() -> None:
    sample = _SAMPLES_DIR / "audio.wav"
    if not sample.exists():
        raise SystemExit(f"Add {sample} first. Run generate_audio_sample.py to create a synthetic one.")
    task = await build_adapter().process_audio(sample.read_bytes())
    _OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (_OUTPUTS_DIR / "audio_task.txt").write_text(task, encoding="utf-8")
    print(f"PASS audio -> {task}")


if __name__ == "__main__":
    asyncio.run(main())
