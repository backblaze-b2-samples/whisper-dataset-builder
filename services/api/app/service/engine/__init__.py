"""Local ML inference engine for the dataset-builder pipeline.

Everything here is LAZY: heavy dependencies (pyannote.audio, faster-whisper,
torch, librosa, soundfile, numpy) are imported *inside the functions*, never at
module top level. That keeps the API bootable and `pnpm test:api` /
`pnpm check:structure` green without requirements-ml.txt installed.

This package performs local compute on bytes already pulled from B2 by the repo
layer. It deliberately does NOT touch boto3 — the boto3-only-in-repo invariant
stays intact (ML inference is compute, not storage).

A MissingMLDependencies error is raised with an actionable message when the
heavy stack is absent, so callers can surface a clear "install
requirements-ml.txt" hint instead of an opaque ImportError.
"""

from app.service.engine.audio import (
    duration_seconds,
    encode_wav,
    load_waveform,
    slice_samples,
)
from app.service.engine.device import (
    select_torch_device,
    select_whisper_device,
)
from app.service.engine.errors import MissingMLDependencies
from app.service.engine.quality import estimate_snr_db, passes_filters
from app.service.engine.transcribe import load_model, transcribe_clip
from app.service.engine.vad import (
    detect_voice_segments,
    pyannote_available,
    resolve_engine,
)

__all__ = [
    "MissingMLDependencies",
    "detect_voice_segments",
    "duration_seconds",
    "encode_wav",
    "estimate_snr_db",
    "load_model",
    "load_waveform",
    "passes_filters",
    "pyannote_available",
    "resolve_engine",
    "select_torch_device",
    "select_whisper_device",
    "slice_samples",
    "transcribe_clip",
]
