"""Runtime device selection for the local ML engine.

`deployment: local` rule: default to CPU and auto-detect the best available
accelerator (CUDA -> Apple MPS -> CPU). Never hard-require a GPU.

Two helpers because the two engines have different backend support:

* `select_torch_device()` — for pyannote / torch, which DO support MPS.
* `select_whisper_device()` — for faster-whisper (CTranslate2), which has NO
  MPS backend, so MPS maps to CPU(int8). This is the documented per-library
  MPS-weakness fallback the autodetect rule allows.

All torch imports are lazy so importing this module is free and the API boots
without the ML stack installed. With torch absent, both helpers report "cpu".
"""

import logging

logger = logging.getLogger(__name__)


def _detect_torch_device() -> str:
    """Best available torch device: cuda -> mps -> cpu. 'cpu' if torch absent."""
    try:
        import torch  # type: ignore
    except ImportError:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def select_torch_device(override: str = "auto") -> str:
    """Device for pyannote/torch. Honors a non-auto override verbatim."""
    if override and override != "auto":
        return override
    device = _detect_torch_device()
    logger.info("Auto-selected torch device: %s", device)
    return device


def select_whisper_device(override: str = "auto") -> tuple[str, str]:
    """Return (device, compute_type) for faster-whisper.

    CTranslate2 has no MPS backend, so an auto/MPS selection collapses to
    CPU with int8. CUDA keeps the configured compute type; CPU/MPS use int8.
    Returns the compute type the caller should pass to faster-whisper.
    """
    chosen = select_torch_device(override)
    if chosen == "mps":
        logger.info(
            "faster-whisper has no MPS backend; mapping MPS -> CPU (int8)."
        )
        return "cpu", "int8"
    if chosen == "cuda":
        return "cuda", "float16"
    return "cpu", "int8"
