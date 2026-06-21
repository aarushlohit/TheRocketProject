"""Generate a sample WAV file for Nemotron audio validation."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


def main() -> None:
    output = Path("RocketLabs/nemotron/samples/audio.wav")
    output.parent.mkdir(parents=True, exist_ok=True)

    sample_rate = 16000
    duration_s = 2.0
    frequency = 440.0
    amplitude = 12000

    with wave.open(str(output), "wb") as wav_file:
      wav_file.setnchannels(1)
      wav_file.setsampwidth(2)
      wav_file.setframerate(sample_rate)

      frame_count = int(sample_rate * duration_s)
      for index in range(frame_count):
          sample = int(amplitude * math.sin(2 * math.pi * frequency * index / sample_rate))
          wav_file.writeframes(struct.pack("<h", sample))

    print(f"PASS audio sample generated -> {output}")


if __name__ == "__main__":
    main()
