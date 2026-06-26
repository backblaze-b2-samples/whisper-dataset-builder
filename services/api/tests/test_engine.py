"""Engine tests that run WITHOUT the heavy ML stack installed.

These guard the lazy-import contract: importing the engine package and its
modules must not pull in pyannote/torch/faster-whisper. They also exercise the
pure-numpy paths (device autodetect, VAD-engine resolution) that don't need a
model download.
"""

import sys

import pytest


def test_engine_imports_without_ml_stack():
    """Importing the engine package must not import heavy ML modules."""
    import app.service.engine  # noqa: F401
    from app.service import build  # noqa: F401

    # None of the heavy deps should have been imported as a side effect.
    for heavy in ("torch", "pyannote", "faster_whisper", "librosa", "soundfile"):
        assert heavy not in sys.modules, f"{heavy} was eagerly imported"


def test_device_defaults_to_cpu_without_torch():
    """With torch absent, both device helpers report CPU (never require a GPU)."""
    from app.service.engine.device import (
        select_torch_device,
        select_whisper_device,
    )

    assert select_torch_device("auto") == "cpu"
    device, compute = select_whisper_device("auto")
    assert device == "cpu"
    assert compute == "int8"


def test_device_honors_explicit_override():
    from app.service.engine.device import select_torch_device

    assert select_torch_device("cuda") == "cuda"
    assert select_torch_device("mps") == "mps"


def test_whisper_maps_mps_to_cpu():
    """faster-whisper has no MPS backend; an MPS override collapses to CPU."""
    from app.service.engine.device import select_whisper_device

    device, compute = select_whisper_device("mps")
    assert device == "cpu"
    assert compute == "int8"


def test_resolve_vad_engine_auto(monkeypatch):
    """auto -> pyannote when a token is set, else the energy fallback."""
    from app.config import settings
    from app.service.engine import vad

    monkeypatch.setattr(settings, "hf_token", "")
    assert vad.resolve_engine("auto") == "energy"

    monkeypatch.setattr(settings, "hf_token", "hf_xxx")
    assert vad.resolve_engine("auto") == "pyannote"
    # Explicit choices are honored verbatim regardless of token.
    assert vad.resolve_engine("energy") == "energy"
    assert vad.resolve_engine("pyannote") == "pyannote"


def test_energy_vad_finds_voiced_spans():
    """The token-free energy VAD splits a silence/tone/silence signal."""
    np = pytest.importorskip("numpy")
    from app.service.engine.vad import _energy_vad

    sr = 16000
    silence = np.zeros(sr, dtype=np.float32)  # 1s
    tone = (0.5 * np.sin(2 * np.pi * 220 * np.arange(sr) / sr)).astype(np.float32)
    signal = np.concatenate([silence, tone, silence])

    spans = _energy_vad(signal, sr)
    assert len(spans) >= 1
    start, end = spans[0]
    # The voiced span should sit roughly in the middle (the tone region).
    assert 0.5 < start < 1.5
    assert 1.5 < end < 2.6


def test_energy_vad_empty_signal():
    np = pytest.importorskip("numpy")
    from app.service.engine.vad import _energy_vad

    assert _energy_vad(np.zeros(0, dtype=np.float32), 16000) == []


def test_quality_filter_rejects_short_clip():
    np = pytest.importorskip("numpy")
    from app.service.engine.quality import passes_filters

    sr = 16000
    tiny = np.ones(int(0.2 * sr), dtype=np.float32)  # 0.2s < min 1.0s
    kept, reason, _snr = passes_filters(
        tiny, sr, min_clip_sec=1.0, max_clip_sec=20.0, min_snr_db=10.0
    )
    assert kept is False
    assert reason == "too_short"
