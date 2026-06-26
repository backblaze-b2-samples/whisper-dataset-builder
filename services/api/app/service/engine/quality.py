"""Per-clip quality filtering (local compute, lazy imports).

Drops clips that are too short / too long, or whose estimated signal-to-noise
ratio falls below a threshold. SNR is estimated from the clip waveform itself:
the loud percentile approximates the speech level and the quiet percentile the
noise floor, so no separate noise reference is needed. numpy is the only
dependency and is already pulled in by the audio stack.
"""

import math


def estimate_snr_db(samples) -> float:
    """Estimate clip SNR in dB from its own loud-vs-quiet energy percentiles."""
    import numpy as np  # type: ignore

    if len(samples) == 0:
        return -math.inf

    # Frame the clip and take per-frame RMS so a few loud samples don't skew it.
    frame_len = max(1, len(samples) // 100)
    n_frames = max(1, len(samples) // frame_len)
    frames = samples[: n_frames * frame_len].reshape(n_frames, frame_len)
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1) + 1e-12)

    signal = float(np.percentile(rms, 90))
    noise = float(np.percentile(rms, 10))
    if noise <= 0:
        noise = 1e-9
    return 20.0 * math.log10(signal / noise)


def passes_filters(
    samples,
    sr: int,
    *,
    min_clip_sec: float,
    max_clip_sec: float,
    min_snr_db: float,
) -> tuple[bool, str | None, float]:
    """Return (kept, drop_reason, snr_db) for a candidate clip waveform."""
    duration = len(samples) / float(sr) if sr else 0.0
    if duration < min_clip_sec:
        return False, "too_short", 0.0
    if duration > max_clip_sec:
        return False, "too_long", 0.0

    snr = estimate_snr_db(samples)
    if snr < min_snr_db:
        return False, "low_snr", snr
    return True, None, snr
