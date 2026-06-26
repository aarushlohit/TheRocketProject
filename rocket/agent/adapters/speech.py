"""Speech transcription manager.

Primary ASR: NVIDIA Riva ``whisper-large-v3`` served through
``grpc.nvcf.nvidia.com`` (gRPC). Multilingual auto-detection is enabled by
using the ``multi`` language code.

Local fallback: Python ``speech_recognition`` library using Google's free web
speech API. No API key needed. Works when Riva is unavailable or returns empty.

Final fallback: Nemotron Omni audio path in :mod:`agent.adapters.nemotron`.
"""

from __future__ import annotations

import io
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
        """Whether any speech-to-text path can be attempted.

        Always True when ``speech_recognition`` is installed (local fallback).
        """

        if os.getenv("ROCKET_DISABLE_SPEECH"):
            return False
        if self._asr_service is not None:
            return True
        if self._api_key:
            try:
                import riva.client  # noqa: F401
                return True
            except Exception:
                pass
        # Local fallback via speech_recognition
        try:
            import speech_recognition  # noqa: F401
            return True
        except Exception:
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

        Primary: local speech_recognition (Google free API, fast, reliable).
        Fallback: Riva (if API key set and library installed).
        Raises only if ALL paths fail.
        """

        # Primary: local speech_recognition (always try first, fastest)
        try:
            transcript = self._transcribe_local(audio_bytes, audio_format)
            if transcript:
                self.status = "ok (local)"
                return transcript
        except Exception:
            pass

        # Fallback: Riva if available
        if self._riva_available():
            try:
                transcript = self._transcribe_riva(audio_bytes)
                if transcript:
                    self.status = "ok (riva)"
                    return transcript
            except Exception:
                pass

        raise RuntimeError("All speech-to-text paths failed (local + Riva).")

    def _riva_available(self) -> bool:
        if self._asr_service is not None:
            return True
        if not self._api_key:
            return False
        try:
            import riva.client  # noqa: F401
            return True
        except Exception:
            return False

    def _transcribe_riva(self, audio_bytes: bytes) -> str:
        service = self._ensure_service()
        config = self._build_config(audio_bytes)
        response = service.offline_recognize(audio_bytes, config)
        return _first_transcript(response)

    def _transcribe_local(self, audio_bytes: bytes, audio_format: str = "wav") -> str:
        """Transcribe using Python speech_recognition (Google free API)."""

        import speech_recognition as sr

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = False

        audio_file = io.BytesIO(audio_bytes)
        try:
            with sr.AudioFile(audio_file) as source:
                audio_data = recognizer.record(source)
        except Exception:
            # If the audio can't be read as-is, try wrapping raw PCM as WAV
            audio_data = self._raw_to_audio_data(audio_bytes)
            if audio_data is None:
                return ""

        try:
            text = recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            return ""
        return str(text).strip() if text else ""

    @staticmethod
    def _raw_to_audio_data(audio_bytes: bytes):
        """Try to interpret raw bytes as 16-bit mono 16kHz PCM and wrap for SR."""

        try:
            import speech_recognition as sr
            import struct
            import wave

            # Wrap raw PCM into a WAV in memory
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_bytes)
            buf.seek(0)
            with sr.AudioFile(buf) as source:
                recognizer = sr.Recognizer()
                return recognizer.record(source)
        except Exception:
            return None

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
