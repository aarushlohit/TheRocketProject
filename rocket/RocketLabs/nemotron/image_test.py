"""Validate PNG to executable task."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from RocketLabs.nemotron.adapter import build_adapter


async def main() -> None:
    sample = Path(r"C:\Users\Aarush\Downloads\sample.jpeg")
    if not sample.exists():
        raise SystemExit(r"Add C:\Users\Aarush\Downloads\sample.jpeg first.")

    image = Image.open(sample)
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGB")

    output = Path("RocketLabs/nemotron/samples/sample_normalized.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG")

    task = await build_adapter().process_image(output.read_bytes(), mime_type="image/png")
    Path("RocketLabs/nemotron/outputs/image_task.txt").write_text(task, encoding="utf-8")
    print(f"PASS image -> {task}")


if __name__ == "__main__":
    asyncio.run(main())
