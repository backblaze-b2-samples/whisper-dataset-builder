<!-- last_verified: 2026-06-26 -->
# Feature: Dashboard

## Purpose
Provide an at-a-glance overview of dataset-builder activity on B2.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /datasets/stats`, `GET /datasets`, `GET /files/stats/activity`

## Core Functions
- `apps/web/src/components/dashboard/dataset-stats-cards.tsx` — 5 metric cards
- `apps/web/src/components/dashboard/recent-builds-table.tsx` — recent datasets
- `apps/web/src/components/dashboard/upload-chart.tsx` — recordings ingested per day
- `apps/web/src/lib/api-client.ts` — `getDatasetStats()`, `getDatasets()`, `getUploadActivity()`
- `services/api/app/runtime/datasets.py` — `GET /datasets/stats` handler
- `services/api/app/service/datasets.py` — `get_dashboard_stats()` business logic

## Canonical Files
- Dashboard metric cards: `apps/web/src/components/dashboard/dataset-stats-cards.tsx`
- Stats service logic: `services/api/app/service/datasets.py`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /datasets/stats` → `DatasetStatsSummary` (recordings_ingested, datasets_built, total_clips, total_clip_hours, avg_write_amplification)
- `GET /datasets` → `DatasetSummary[]` for the recent-builds table (newest-first)
- `GET /files/stats/activity?days=7` → `DailyUploadCount[]` for the chart

## Flow
- Page loads → parallel API calls (dataset stats, dataset list, ingest activity)
- Metric cards display recordings ingested, datasets built, total clips, total clip-hours, and **avg write-amplification (clips per recording)**
- Bar chart shows server-aggregated daily recordings ingested for the last 7 days
- Recent builds table shows the latest datasets with name, layout, clips, created, status

## Edge Cases
- API unavailable → inline error state with retry
- No datasets → empty chart/table messages
- Large object count → stats endpoints paginate using `ContinuationToken`

## UX States
- Loading: skeleton placeholders for cards and table
- Empty: "No datasets yet" / "No activity yet"
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_datasets.py` (`test_dashboard_stats_rollup`)
- Required cases: stats rollup with a built dataset, empty state
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
