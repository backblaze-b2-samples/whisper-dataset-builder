<!-- last_verified: 2026-06-26 -->
# Feature: Serve / read-from-B2

## Purpose
Preview clip↔transcript pairs in the browser and show a copy-paste snippet to load the dataset directly from B2 in a training pipeline. *No external API.*

## Used By
- UI: `/datasets/[id]` detail page
- API: `GET /datasets/{id}/snippet`, `GET /datasets/{id}/clips/{clip_id}/preview`

## Core Functions
- `apps/web/src/components/datasets/dataset-detail.tsx` — stats, snippet, clip list
- `apps/web/src/components/datasets/clip-row.tsx` — in-browser `<audio>` playback per clip
- `services/api/app/service/datasets.py` — `serve_snippet()`
- `services/api/app/runtime/datasets.py` — snippet + clip-preview endpoints
- `services/api/app/service/files.py` — `get_preview_url()` (presigned URL)

## Canonical Files
- Detail view: `apps/web/src/components/datasets/dataset-detail.tsx`

## Inputs
- dataset id, clip id

## Outputs
- `GET /datasets/{id}/snippet` → `{ snippet: string }` (a `datasets.load_dataset("audiofolder", ...)` or boto3-streaming snippet)
- `GET /datasets/{id}/clips/{clip_id}/preview` → `{ url: string }` (presigned WAV URL)

## Flow
- Detail page renders stats + the load-from-B2 snippet (for ready datasets)
- Each clip row lazily fetches a presigned URL and plays the WAV inline next to its transcript
- The snippet shows how to read the dataset directly from the B2 S3 endpoint in training

## Edge Cases
- Draft dataset (no clips) → empty state prompting a build
- Missing clip → 404
- Presigned URL fetch fails → loading spinner / inline message

## UX States
- Loading: skeletons; per-clip "Loading audio…" spinner
- Empty: "No clips yet"
- Loaded: stats cards, snippet block, playable clip rows

## Verification
- Test files: `services/api/tests/test_datasets.py`
- Required cases: snippet for a ready dataset, clip preview 404 for unknown clip
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: dataset tests green; build passes

## Related Docs
- [Dataset packaging](dataset-packaging.md)
- [Datasets explorer](datasets-explorer.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
