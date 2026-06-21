"""Validate WAV to executable task."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from RocketLabs.nemotron.adapter import build_adapter


async def main() -> None:
    sample = Path("RocketLabs/nemotron/samples/audio.wav")
    if not sample.exists():
        raise SystemExit("Add RocketLabs/nemotron/samples/audio.wav first.")
    task = await build_adapter().process_audio(sample.read_bytes())
    Path("RocketLabs/nemotron/outputs/audio_task.txt").write_text(task, encoding="utf-8")
    print(f"PASS audio -> {task}")


if __name__ == "__main__":
    asyncio.run(main())
