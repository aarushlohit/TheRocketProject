"""Speech transcription manager.

Primary ASR: local faster-whisper only.
"""

from __future__ import annotations

import os
import tempfile

# Whisper model size - "base" is fast, "small" is accurate, "medium" is very accurate.
# "large-v3" is best but needs ~3GB RAM. Default to "base" for speed; override with env.
DEFAULT_WHISPER_MODEL = os.getenv("ROCKET_WHISPER_MODEL", "base")


class SpeechManager:
    """Primary speech-to-text path backed by local Whisper."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        language_code: str | None = None,
        asr_service: object | None = None,
        whisper_model: str | None = None,
    ) -> None:
        self._api_key = api_key
        self.language_code = language_code or os.getenv("ROCKET_POLLINATIONS_LANGUAGE", "auto")
        self._asr_service = asr_service
        self._whisper_model_name = whisper_model or DEFAULT_WHISPER_MODEL
        self._whisper_model = None
        self.status: str = "unchecked"

    @property
    def available(self) -> bool:
        """Whether Whisper can be attempted."""

        if os.getenv("ROCKET_DISABLE_SPEECH"):
            return False
        if self._asr_service is not None:
            return True
        try:
            from faster_whisper import WhisperModel  # noqa: F401

            return True
        except Exception:
            return False

    def transcribe(self, audio_bytes: bytes, *, audio_format: str = "wav") -> str:
        """Return the transcript for ``audio_bytes``.

        Chain: injected service (for tests) -> faster-whisper. Raises if both paths fail.
        """

        errors: list[str] = []

        if self._asr_service is not None:
            try:
                transcript = self._transcribe_injected_service(audio_bytes)
                if transcript:
                    self.status = "ok (injected)"
                    return transcript
                errors.append("injected: empty transcript")
            except Exception as e:
                errors.append(f"injected: {e}")

        # 2. faster-whisper (best accuracy, runs locally)
        try:
            transcript = self._transcribe_whisper(audio_bytes)
            if transcript:
                self.status = "ok (whisper-local)"
                return transcript
            errors.append("whisper: empty transcript")
        except Exception as e:
            errors.append(f"whisper: {e}")

        self.status = f"failed: {'; '.join(errors)}"
        raise RuntimeError(f"All speech-to-text paths failed: {'; '.join(errors)}")

    def _transcribe_whisper(self, audio_bytes: bytes) -> str:
        """Transcribe using faster-whisper (local Whisper model)."""

        from faster_whisper import WhisperModel

        if self._whisper_model is None:
            self._whisper_model = WhisperModel(
                self._whisper_model_name,
                device="cpu",
                compute_type="int8",
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            segments, _info = self._whisper_model.transcribe(
                tmp_path,
                beam_size=5,
                language=None,
                vad_filter=True,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        return text

    def _transcribe_injected_service(self, audio_bytes: bytes) -> str:
        service = self._asr_service
        if service is None:
            return ""
        config = getattr(service, "build_config", None)
        if callable(config):
            cfg = config(audio_bytes)
            response = service.offline_recognize(audio_bytes, cfg)
        else:
            response = service.offline_recognize(audio_bytes, None)
        return _first_transcript(response)

def _first_transcript(response: object) -> str:
    results = getattr(response, "results", None) or []
    for result in results:
        alternatives = getattr(result, "alternatives", None) or []
        if alternatives:
            transcript = getattr(alternatives[0], "transcript", "")
            if transcript:
                return str(transcript).strip()
    if isinstance(response, dict):
        text = response.get("text") or response.get("transcript") or ""
        if isinstance(text, str):
            return text.strip()
    return ""
