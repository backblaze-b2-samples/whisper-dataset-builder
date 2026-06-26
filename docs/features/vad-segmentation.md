<!-- last_verified: 2026-06-26 -->
# Feature: VAD segmentation

## Purpose
Split a long-form recording into voice-active clips using pyannote.audio's `segmentation-3.0` VAD (the showcased engine), with a token-free energy fallback.

## Used By
- Job: dataset build pipeline (`service/build.py`)
- API: indirectly via `POST /datasets/{id}/build`

## Core Functions
- `services/api/app/service/engine/vad.py` — `resolve_engine()`, `detect_voice_segments()`, `_pyannote_vad()`, `_energy_vad()`
- `services/api/app/service/engine/_torch_safe.py` — `allowlist_pyannote_globals()` (torch 2.6+ weights_only trap)
- `services/api/app/service/engine/device.py` — `select_torch_device()`

## Canonical Files
- VAD engine: `services/api/app/service/engine/vad.py`

## Inputs
- samples: float32 mono numpy waveform (16kHz)
- engine: resolved "pyannote" | "energy"

## Outputs
- list of `(start_sec, end_sec)` voice-active spans

## Flow
- `resolve_engine("auto")` → "pyannote" if `HF_TOKEN` is set, else "energy"
- **pyannote**: `Model.from_pretrained("pyannote/segmentation-3.0", use_auth_token=...)` → `VoiceActivityDetection` pipeline on the auto-selected device (CUDA → MPS → CPU) → timeline support spans
- **energy**: per-frame RMS over 30ms frames, adaptive threshold, gap-bridge, merge into spans (no token, numpy only)

## Edge Cases
- `HF_TOKEN` unset → energy fallback (app still runs end-to-end with B2 creds alone)
- ML stack absent → `MissingMLDependencies` with an install hint
- pyannote 4.x pulls a separately-gated `community-1` weight → pinned to `pyannote.audio>=3.3.2,<4`
- Empty / sub-frame signal → returns `[]`

## UX States
- Surfaced as the "detecting" build-progress badge in the UI

## Verification
- Test files: `services/api/tests/test_engine.py` (`test_resolve_vad_engine_auto`, `test_energy_vad_finds_voiced_spans`, `test_energy_vad_empty_signal`)
- Required cases: auto-resolution by token, energy VAD finds a voiced span, empty signal
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: engine tests green; `test_engine_imports_without_ml_stack` confirms lazy imports

## Related Docs
- [Quality filter](quality-filter.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
