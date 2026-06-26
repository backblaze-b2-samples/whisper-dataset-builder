"""Audio decode / resample / clip-write helpers (local compute, lazy imports).

Decodes arbitrary source recordings to a mono float32 waveform at the target
sample rate, slices voice-active segments into clips, and encodes clips back to
16-bit PCM WAV bytes for upload to B2. All heavy imports (librosa, soundfile,
numpy) live inside the functions so importing this module is free and the API
boots without requirements-ml.txt.
"""

import io
import logging

from app.service.engine.errors import MissingMLDependencies

logger = logging.getLogger(__name__)


def load_waveform(media_bytes: bytes, suffix: str, target_sr: int):
    """Decode media bytes to a mono float32 numpy array at ``target_sr``.

    Returns (samples, sample_rate). Raises MissingMLDependencies if the audio
    stack is absent.
    """
    try:
        import librosa  # type: ignore
    except ImportError as e:
        raise MissingMLDependencies("Audio decoding") from e

    import os
    import tempfile

    fd, path = tempfile.mkstemp(suffix=suffix or ".bin", prefix="wdb_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(media_bytes)
        # librosa delegates to soundfile / audioread (ffmpeg) for decoding and
        # resamples to mono at target_sr in one call.
        samples, sr = librosa.load(path, sr=target_sr, mono=True)
        return samples, sr
    finally:
        import contextlib

        with contextlib.suppress(OSError):
            os.unlink(path)


def slice_samples(samples, sr: int, start_sec: float, end_sec: float):
    """Return the [start_sec, end_sec) slice of ``samples``."""
    a = max(0, int(start_sec * sr))
    b = min(len(samples), int(end_sec * sr))
    return samples[a:b]


def encode_wav(samples, sr: int) -> bytes:
    """Encode a mono float waveform to 16-bit PCM WAV bytes."""
    try:
        import soundfile as sf  # type: ignore
    except ImportError as e:
        raise MissingMLDependencies("WAV encoding") from e

    buf = io.BytesIO()
    sf.write(buf, samples, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def duration_seconds(samples, sr: int) -> float:
    """Length of a waveform in seconds."""
    return len(samples) / float(sr) if sr else 0.0
