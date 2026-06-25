"""Speech transcription manager.

Primary ASR: NVIDIA Riva ``whisper-large-v3`` served through
``grpc.nvcf.nvidia.com`` (gRPC). Multilingual auto-detection is enabled by
using the ``multi`` language code. The Nemotron Omni audio path remains the
fallback and lives in :mod:`agent.adapters.nemotron`.

``nvidia-riva-client`` is an optional dependency. If it is not installed or no
API key is present, :attr:`SpeechManager.available` is ``False`` and the caller
falls back to Nemotron Omni transparently.
"""

from __future__ import annotations

import os

RIVA_SERVER = "grpc.nvcf.nvidia.com:443"
RIVA_FUNCTION_ID = "b702f636-f60c-4a3d-a6f4-f3568c13bd7d"


class SpeechManager:
    """Primary speech-to-text path backed by Riva Whisper large-v3."""

    def __init__(
        self,
        *,
        server: str = RIVA_SERVER,
        function_id: str | None = None,
        api_key: str | None = None,
        language_code: str | None = None,
        asr_service: object | None = None,
    ) -> None:
        self.server = server
        self.function_id = function_id or os.getenv("ROCKET_RIVA_FUNCTION_ID", RIVA_FUNCTION_ID)
        self._api_key = api_key if api_key is not None else os.getenv("NVIDIA_API_KEY", "")
        # "multi" enables Riva automatic language detection.
        self.language_code = language_code or os.getenv("ROCKET_RIVA_LANGUAGE", "multi")
        self._asr_service = asr_service
        self.status: str = "unchecked"

    @property
    def available(self) -> bool:
        """Whether the primary Riva path can be attempted."""

        if os.getenv("ROCKET_DISABLE_RIVA_SPEECH"):
            return False
        if self._asr_service is not None:
            return True
        if not self._api_key:
            return False
        try:
            import riva.client  # noqa: F401
        except Exception:
            return False
        return True

    def _ensure_service(self):
        if self._asr_service is None:
            import riva.client

            auth = riva.client.Auth(
                uri=self.server,
                use_ssl=True,
                metadata_args=[
                    ["function-id", self.function_id],
                    ["authorization", f"Bearer {self._api_key}"],
                ],
            )
            self._asr_service = riva.client.ASRService(auth)
        return self._asr_service

    def transcribe(self, audio_bytes: bytes, *, audio_format: str = "wav") -> str:
        """Return the transcript for ``audio_bytes``.

        Audio must be mono 16-bit PCM in WAV/FLAC/OPUS. Raises on any failure so
        the caller can fall back to Nemotron Omni.
        """

        del audio_format  # Riva detects the container from the audio header.
        service = self._ensure_service()
        config = self._build_config(audio_bytes)
        response = service.offline_recognize(audio_bytes, config)
        transcript = _first_transcript(response)
        if not transcript:
            raise RuntimeError("Riva returned an empty transcript.")
        self.status = "ok"
        return transcript

    def _build_config(self, audio_bytes: bytes):
        try:
            import riva.client
        except Exception:
            return None
        config = riva.client.RecognitionConfig(
            language_code=self.language_code,
            max_alternatives=1,
            enable_automatic_punctuation=True,
        )
        try:
            riva.client.add_audio_file_specs_to_config(config, audio_bytes)
        except Exception:
            pass
        return config


def _first_transcript(response: object) -> str:
    results = getattr(response, "results", None) or []
    for result in results:
        alternatives = getattr(result, "alternatives", None) or []
        for alternative in alternatives:
            transcript = getattr(alternative, "transcript", "")
            if transcript and transcript.strip():
                return transcript.strip()
    return ""
