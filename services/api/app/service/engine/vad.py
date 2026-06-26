"""Voice-activity detection (local compute, lazy imports).

The showcased engine is pyannote.audio's `segmentation-3.0` VAD pipeline. It is
HF-gated, so it needs a FREE HuggingFace token (weights-download gate only, not
a paid inference API). Graceful degradation is a hard requirement: when no
token is configured we fall back to a token-free energy-based VAD so the whole
pipeline runs end-to-end with B2 credentials alone.

`resolve_engine("auto")` -> "pyannote" if a token is present, else "energy".
Both engines return a list of (start_sec, end_sec) voice-active spans.

Heavy imports (pyannote, torch) stay lazy so importing this module is free and
the API boots without requirements-ml.txt. The energy fallback uses only numpy
(already pulled in by the audio stack).
"""

import logging

from app.config import settings
from app.service.engine._torch_safe import allowlist_pyannote_globals
from app.service.engine.device import select_torch_device
from app.service.engine.errors import MissingMLDependencies

logger = logging.getLogger(__name__)


def pyannote_available() -> bool:
    """True only if a HuggingFace token is configured for gated weights."""
    return bool(settings.hf_token.strip())


def resolve_engine(requested: str) -> str:
    """Map a requested engine ('auto'|'pyannote'|'energy') to a concrete one."""
    if requested == "pyannote":
        return "pyannote"
    if requested == "energy":
        return "energy"
    # auto
    return "pyannote" if pyannote_available() else "energy"


def detect_voice_segments(samples, sr: int, engine: str) -> list[tuple[float, float]]:
    """Return voice-active (start_sec, end_sec) spans for the waveform.

    ``engine`` must already be resolved to 'pyannote' or 'energy'.
    """
    if engine == "pyannote":
        return _pyannote_vad(samples, sr)
    return _energy_vad(samples, sr)


def _pyannote_vad(samples, sr: int) -> list[tuple[float, float]]:
    """pyannote/segmentation-3.0 VAD. Requires the ML stack + HF_TOKEN."""
    try:
        import torch  # type: ignore
        from pyannote.audio import Model  # type: ignore
        from pyannote.audio.pipelines import (  # type: ignore
            VoiceActivityDetection,
        )
    except ImportError as e:
        raise MissingMLDependencies("pyannote VAD") from e

    allowlist_pyannote_globals()
    device = select_torch_device(settings.device)
    logger.info("Loading pyannote VAD model=%s device=%s", settings.segmentation_model, device)
    model = Model.from_pretrained(
        settings.segmentation_model, use_auth_token=settings.hf_token
    )
    pipeline = VoiceActivityDetection(segmentation=model)
    # Sensible defaults for segmentation-3.0's powerset VAD.
    pipeline.instantiate(
        {
            "min_duration_on": settings.min_clip_sec,
            "min_duration_off": 0.25,
        }
    )
    pipeline.to(torch.device(device))

    waveform = torch.from_numpy(samples).unsqueeze(0)
    annotation = pipeline({"waveform": waveform, "sample_rate": sr})
    return [(seg.start, seg.end) for seg in annotation.get_timeline().support()]


def _energy_vad(samples, sr: int) -> list[tuple[float, float]]:
    """Token-free energy-based VAD over short frames.

    Computes per-frame RMS energy, marks frames above an adaptive threshold as
    voiced, and merges contiguous voiced frames into spans. No model download,
    no HF token — the guaranteed-runnable fallback.
    """
    import numpy as np  # type: ignore

    if len(samples) == 0:
        return []

    frame_ms = 30
    frame_len = max(1, int(sr * frame_ms / 1000))
    n_frames = len(samples) // frame_len
    if n_frames == 0:
        return []

    frames = samples[: n_frames * frame_len].reshape(n_frames, frame_len)
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1) + 1e-12)

    # Adaptive threshold: floor (noise) plus a fraction of the dynamic range.
    floor = float(np.percentile(rms, 10))
    peak = float(np.percentile(rms, 95))
    threshold = floor + 0.15 * max(peak - floor, 1e-6)
    voiced = rms > threshold

    spans: list[tuple[float, float]] = []
    start: int | None = None
    # Bridge gaps shorter than 250ms so words inside a phrase don't split.
    gap_frames = max(1, int(250 / frame_ms))
    silence_run = 0
    for i, is_voiced in enumerate(voiced):
        if is_voiced:
            if start is None:
                start = i
            silence_run = 0
        elif start is not None:
            silence_run += 1
            if silence_run >= gap_frames:
                end = i - silence_run + 1
                spans.append((start * frame_ms / 1000, end * frame_ms / 1000))
                start = None
                silence_run = 0
    if start is not None:
        spans.append((start * frame_ms / 1000, n_frames * frame_ms / 1000))
    return spans
