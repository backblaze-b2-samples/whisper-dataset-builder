<!-- last_verified: 2026-06-26 -->
# Feature: Dataset packaging

## Purpose
Write clip wavs + transcript metadata + a manifest to B2 in LJSpeech or HuggingFace `audiofolder` layout, and surface the write-amplification stat (1 recording → N clips). *No external API.*

## Used By
- Job: dataset build pipeline (`service/build.py`)

## Core Functions
- `services/api/app/service/build.py` — `build_dataset()`, `_write_metadata()`, `manifest_key()`
- `services/api/app/repo/dataset_store.py` — `put_bytes()`, `put_json()`
- `services/api/app/service/engine/audio.py` — `encode_wav()`

## Canonical Files
- Build + packaging: `services/api/app/service/build.py`

## Inputs
- The kept clips (waveform + transcript + timing + SNR) from the pipeline
- layout: ljspeech | hf_audiofolder

## Outputs (on B2)
```
datasets/<id>/wavs/<clip_id>.wav     16kHz mono PCM16
datasets/<id>/metadata.csv           LJSpeech: id|transcript|normalized
datasets/<id>/metadata.jsonl         HF audiofolder: {file_name, transcription}
datasets/<id>/dataset.json           manifest: config + stats + clip index
```
Manifest stats include `clips_kept`, `clips_dropped`, `total_clip_seconds`, the VAD engine used, and **`write_amplification`** (kept clips per source recording).

## Flow
- For each kept clip: encode WAV → `put_bytes` to `wavs/` → append a metadata row
- Write `metadata.csv` (LJSpeech) or `metadata.jsonl` (HF) per the chosen layout
- Compute stats and write the `dataset.json` manifest with status `ready`

## Edge Cases
- No clips pass filters → empty metadata file, manifest still written (clips_kept 0)
- Build failure → manifest persisted with status `error` and the message
- B2 write failure → `RuntimeError`, recorded on the job + manifest

## UX States
- Surfaced as the "packaging" → "done" build-progress badges; stats render on the detail page

## Verification
- Test files: `services/api/tests/test_datasets.py` (build enqueue + manifest CRUD; full packaging needs the ML stack)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: dataset tests green

## Related Docs
- [Serve from B2](serve-from-b2.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
