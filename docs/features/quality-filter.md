<!-- last_verified: 2026-06-26 -->
# Feature: Quality filter

## Purpose
Drop candidate clips that are too short/long or below an SNR threshold, and report kept-vs-dropped counts. *Local, numpy only.*

## Used By
- Job: dataset build pipeline (`service/build.py`)

## Core Functions
- `services/api/app/service/engine/quality.py` — `passes_filters()`, `estimate_snr_db()`

## Canonical Files
- Quality filter: `services/api/app/service/engine/quality.py`

## Inputs
- samples: clip waveform (float32 mono)
- min_clip_sec / max_clip_sec / min_snr_db (from the dataset config)

## Outputs
- `(kept: bool, drop_reason: str | None, snr_db: float)`

## Flow
- Reject if clip duration < min or > max (`too_short` / `too_long`)
- Estimate SNR from the clip's own loud (P90) vs quiet (P10) per-frame RMS percentiles
- Reject if SNR < threshold (`low_snr`); otherwise keep
- The build records `clips_kept` / `clips_dropped` in the manifest stats

## Edge Cases
- Empty clip → SNR `-inf`, dropped
- Silent clip → low SNR, dropped
- ML stack absent → numpy import inside the function raises only when actually run

## UX States
- Surfaced as the "filtering" build-progress badge in the UI

## Verification
- Test files: `services/api/tests/test_engine.py` (`test_quality_filter_rejects_short_clip`)
- Required cases: too-short rejection (happy-path kept clips covered end-to-end by the build)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: quality tests green

## Related Docs
- [VAD segmentation](vad-segmentation.md)
- [Whisper transcription](whisper-transcription.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
