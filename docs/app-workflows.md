<!-- last_verified: 2026-06-26 -->
# App Workflows

User journeys inside the application.

## Upload a source recording

- User navigates to `/upload`
- Drops or selects an audio/video file in the dropzone
- Client validates file size (max 500MB) and type (audio/video only)
- Progress bar shows per-file upload status
- On success the recording lands under the `sources/` prefix on B2 and becomes selectable in the dataset create form
- See: [Source ingest](features/source-ingest.md)

## Create a dataset

- User navigates to `/datasets` and clicks **New dataset** (`/datasets/new`)
- Picks a source recording from a **Select** (populated from `sources/`)
- Chooses pipeline settings via selectors: VAD engine (auto/pyannote/energy), Whisper model (tiny/base/small), language, layout (LJSpeech / HF audiofolder), plus clip-length and SNR bounds
- Create-form defaults are shown as placeholder/description guidance (no autofill button), tuned for a quick no-token test run
- On save, a draft `datasets/<id>/dataset.json` manifest is written to B2 and the user lands on the detail page
- See: [Datasets explorer](features/datasets-explorer.md)

## Run a build (the write-amplification story)

- From the list or detail page the user clicks **Build**
- A background job runs: download source → pyannote VAD (or energy fallback) → quality filter (SNR + duration) → faster-whisper transcribe → package
- Live progress badges (loading → detecting → filtering → transcribing → packaging → done) update via polling
- On completion the dataset flips to **Ready** and shows clips kept, **write-amplification (clips per recording)**, total clip-time, and the VAD engine used
- See: [VAD segmentation](features/vad-segmentation.md), [Quality filter](features/quality-filter.md), [Whisper transcription](features/whisper-transcription.md), [Dataset packaging](features/dataset-packaging.md)

## Inspect and serve a dataset

- On `/datasets/[id]` the user sees stats, a copy-paste **load-from-B2** snippet, and the clip ↔ transcript pairs
- Each clip plays in-browser (presigned URL) next to its transcript
- See: [Serve from B2](features/serve-from-b2.md)

## Edit / delete a dataset

- **Edit** (`/datasets/[id]/edit`): rename/redescribe anytime; build config is editable only while the dataset is a draft (locked once clips exist)
- **Delete**: a confirm dialog removes the dataset record and every artifact under its `datasets/<id>/` prefix on B2 (scoped — never bucket-wide)

## Browse the whole bucket

- User navigates to `/files` (the kept full-bucket explorer): list, preview, download, delete any object — including `sources/` and `datasets/` prefixes
- See: [File Browser](features/file-browser.md)

## View dashboard

- User navigates to `/` (home)
- Builder metrics load: recordings ingested, datasets built, total clips, total clip-hours, avg write-amplification
- A bar chart shows recordings ingested over the last 7 days; a table lists recent builds
- See: [Dashboard](features/dashboard.md)
