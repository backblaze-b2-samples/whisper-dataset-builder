<!-- last_verified: 2026-06-26 -->
# Feature: Whisper transcription

## Purpose
Transcribe each retained clip with faster-whisper (CTranslate2 Whisper). Ungated — no token. *Local.*

## Used By
- Job: dataset build pipeline (`service/build.py`)

## Core Functions
- `services/api/app/service/engine/transcribe.py` — `load_model()`, `transcribe_clip()`
- `services/api/app/service/engine/device.py` — `select_whisper_device()`

## Canonical Files
- Transcription engine: `services/api/app/service/engine/transcribe.py`

## Inputs
- model_size: tiny | base | small (default base)
- samples: clip waveform (float32 mono @ 16kHz)
- language: "auto" or a language code

## Outputs
- `{"text": str, "language": str}` per clip

## Flow
- `load_model()` once per build on the auto-selected device + compute type
- `transcribe_clip()` runs faster-whisper with `beam_size=5`, joins segment text
- Clips that transcribe to empty text are dropped from the dataset

## Edge Cases
- ML stack absent → `MissingMLDependencies` with an install hint
- **MPS:** CTranslate2 has no MPS backend, so `select_whisper_device()` maps MPS → CPU(int8). CUDA uses float16; CPU/MPS use int8. pyannote (VAD step) still uses MPS where available.
- Empty transcription → clip dropped

## UX States
- Surfaced as the "transcribing" build-progress badge in the UI (with per-clip percentage)

## Verification
- Test files: `services/api/tests/test_engine.py` (`test_device_defaults_to_cpu_without_torch`, `test_whisper_maps_mps_to_cpu`)
- Required cases: CPU default with no torch, MPS→CPU mapping (full transcription needs the ML stack)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: device/engine tests green

## Related Docs
- [Quality filter](quality-filter.md)
- [Dataset packaging](dataset-packaging.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
