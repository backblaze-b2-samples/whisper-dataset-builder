<!-- last_verified: 2026-06-26 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with builder metrics (recordings ingested, datasets built, total clips, clip-hours, avg write-amplification) + recent builds
  - Datasets explorer (scoped) with full CRUD + run-with-live-progress and a clip↔transcript detail view with in-browser audio playback
  - Upload (drag-and-drop) — on-ramp for source recordings
  - Files (full-bucket explorer, kept from the starter)
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for source upload, dataset CRUD, build runs, stats
  - B2 S3 integration via boto3
  - Local ML engine (lazy-imported): pyannote VAD (with energy fallback) + faster-whisper transcription
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing + Prometheus-format metrics
- **packages/shared/** — TypeScript type definitions mirroring the Pydantic models

## Backend Layering

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic + ML engine — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer (`b2_client.py` + `dataset_store.py`)
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (Dataset, Clip, BuildJob, FileMetadata, …)
    config/                Settings loaded from environment (region-derived endpoint)
    repo/                  B2 S3 client + dataset_store (data access layer)
    service/               Business logic (datasets, build, jobs) + engine/
    service/engine/        Local ML — device, vad, quality, transcribe, audio (lazy imports)
    runtime/               FastAPI route handlers
  scripts/build_dataset.py Bulk CLI
  tests/                   pytest tests (structural + integration + engine guard)
```

## The ML Engine

`service/engine/` performs local compute on bytes the repo already fetched from B2. It owns no boto3 (ML is compute, not storage). Every heavy import (pyannote.audio, faster-whisper, torch, librosa, soundfile, numpy) is **lazy** — done inside functions — so the API boots and `pnpm test:api` / `pnpm check:structure` / `pnpm lint:api` all pass without `requirements-ml.txt`.

- **device.py** — auto-detect CUDA → MPS → CPU, default CPU. pyannote/torch use MPS; faster-whisper (CTranslate2) has no MPS backend so it maps MPS → CPU(int8).
- **vad.py** — pyannote `segmentation-3.0` VAD (gated, needs a free `HF_TOKEN`) with a token-free energy VAD fallback. `resolve_engine("auto")` picks pyannote when a token is set, else energy.
- **quality.py** — per-clip SNR + duration filtering.
- **transcribe.py** — faster-whisper transcription (loaded once per build).
- **audio.py** — decode/resample to 16kHz mono, slice clips, encode WAV.
- **_torch_safe.py** — torch 2.6+ `weights_only` allowlist for pyannote checkpoints.

## Boundary Invariants

- **No external SDK leakage**: `boto3` only in `app/repo/`.
- **No raw dicts at boundaries**: typed Pydantic models cross every layer.
- **Lazy ML**: heavy model libs never imported at module top level.
- **Never require a GPU**: device defaults to CPU with runtime autodetect.
- **Scoped deletes**: `dataset_store.delete_prefix` refuses an empty/root prefix, so a delete only ever targets one `datasets/<id>/` prefix.
- **Validated inputs**: all HTTP inputs validated by FastAPI/Pydantic; keys validated against path-traversal.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API). No application database — the `datasets/<id>/dataset.json` manifest is authoritative for each dataset; sources live under `sources/`.

On-B2 layout:
```
sources/<recording>.<ext>
datasets/<id>/dataset.json           manifest: config + stats + clip index
datasets/<id>/wavs/<clip_id>.wav     16kHz mono clips
datasets/<id>/metadata.csv           LJSpeech
datasets/<id>/metadata.jsonl         HF audiofolder
```

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently` (web `:3000`, API `:8000`). The pipeline is `deployment: local`: CPU-default, GPU auto-detected.
- **Railway** — two services from the same repo; see `infra/railway/README.md`.

## Data Flows

- **Upload (source)**: Browser -> `POST /upload` -> API validates -> service -> repo writes to `sources/`
- **Create dataset**: Browser -> `POST /datasets` -> service writes a draft `datasets/<id>/dataset.json`
- **Build (run)**: Browser -> `POST /datasets/{id}/build` -> background task: repo downloads source -> engine VAD -> filter -> transcribe -> repo writes clips + metadata + manifest. Progress streams via the ephemeral job registry, polled by the UI.
- **Read**: Browser -> `GET /datasets` / `GET /datasets/{id}` -> service reads manifests via repo. Clip playback uses presigned URLs.
- **Delete**: Browser -> `DELETE /datasets/{id}` -> service -> repo `delete_prefix("datasets/{id}/")` (scoped).

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware
- `/metrics` (Prometheus format) and `/health` (B2 connectivity)

## Canonical Files

- Layered API handler: `services/api/app/runtime/datasets.py`
- Build orchestration: `services/api/app/service/build.py`
- Dataset CRUD + stats: `services/api/app/service/datasets.py`
- ML engine: `services/api/app/service/engine/`
- B2 data access (repo): `services/api/app/repo/{b2_client,dataset_store}.py`
- Pydantic models: `services/api/app/types/dataset.py`
- Config: `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TS types: `packages/shared/src/types.ts`

## Core Features

- [Source ingest](docs/features/source-ingest.md)
- [VAD segmentation](docs/features/vad-segmentation.md)
- [Quality filter](docs/features/quality-filter.md)
- [Whisper transcription](docs/features/whisper-transcription.md)
- [Dataset packaging](docs/features/dataset-packaging.md)
- [Serve from B2](docs/features/serve-from-b2.md)
- [Datasets explorer](docs/features/datasets-explorer.md)
- [File Browser](docs/features/file-browser.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md)
- [docs/RELIABILITY.md](docs/RELIABILITY.md)
- [AGENTS.md](AGENTS.md)
