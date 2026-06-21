"""Validate Braille text to executable task."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from RocketLabs.nemotron.adapter import build_adapter


async def main() -> None:
    sample = Path("RocketLabs/nemotron/samples/braille.txt")
    if not sample.exists():
        sample.write_text("open youtube search cats play first result", encoding="utf-8")
    task = await build_adapter().process_braille(sample.read_text(encoding="utf-8"))
    Path("RocketLabs/nemotron/outputs/braille_task.txt").write_text(task, encoding="utf-8")
    print(f"PASS braille -> {task}")


if __name__ == "__main__":
    asyncio.run(main())
