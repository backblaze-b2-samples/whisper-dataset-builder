"""faster-whisper transcription (local compute, lazy imports).

Transcribes a single clip waveform with faster-whisper (CTranslate2 Whisper).
The model is loaded once per build via `load_model()` and reused across clips,
since clip-by-clip reloads would dominate runtime.

CTranslate2 has no MPS backend, so device selection (see engine/device.py)
maps MPS -> CPU(int8). pyannote VAD still uses MPS where available.

All heavy imports live inside the functions so importing this module is free
and the API boots without requirements-ml.txt.
"""

import logging

from app.config import settings
from app.service.engine.device import select_whisper_device
from app.service.engine.errors import MissingMLDependencies

logger = logging.getLogger(__name__)


def load_model(model_size: str | None = None):
    """Load a faster-whisper model on the auto-selected device.

    Returns an opaque model handle to pass to `transcribe_clip`. Raises
    MissingMLDependencies if faster-whisper is absent.
    """
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as e:
        raise MissingMLDependencies("Whisper transcription") from e

    device, compute_type = select_whisper_device(settings.device)
    size = model_size or settings.whisper_model
    logger.info(
        "Loading faster-whisper model=%s device=%s compute=%s",
        size,
        device,
        compute_type,
    )
    return WhisperModel(size, device=device, compute_type=compute_type)


def transcribe_clip(model, samples, language: str | None = None) -> dict:
    """Transcribe one clip waveform (float32 mono @ engine sample rate).

    ``language`` of None or "auto" lets Whisper detect the language. Returns
    ``{"text": str, "language": str}``.
    """
    lang = None if (language in (None, "auto")) else language
    segments, info = model.transcribe(samples, language=lang, beam_size=5)
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return {"text": text, "language": info.language}
