# Build plan — `whisper-dataset-builder`

Built on **vibe-coding-starter-kit** (cloned fresh at
`.claude/scratch/vcsk-3c9a1dac-24ac-4800-93ab-f4d09f3d1e02/` — the ONLY source of truth).
Closest in-repo analog to mirror for the ML engine + media explorer:
`../whisperx-diarized-archive` (read it for patterns; do NOT copy its diarization/search
features — this app is a *dataset builder*, not an archive/search app).

---

## 1. Purpose

`whisper-dataset-builder` turns long-form audio stored on Backblaze B2 into a
**training-ready speech dataset** — clip + transcript pairs in a standard layout
(LJSpeech or HuggingFace `audiofolder`). ML engineers and speech researchers
building custom ASR/TTS models (and teams doing low-resource language data
collection from field recordings) upload a raw recording, the app runs
**pyannote.audio voice-activity detection** to split it into voice-active clips,
applies **quality filtering** (SNR + duration), **transcribes each clip with
Whisper**, and writes the packaged dataset back to B2. A single long recording
fans out into many labeled clips — the **write-amplification** story (1 source →
N labeled pairs) — and the resulting corpus is read directly from B2 by a
training pipeline. B2 is the storage layer for both the source audio and the
generated dataset, via the S3-compatible API with a custom user-agent and the
standard `B2_*` env vars. Runs on local OSS models — no paid second API key.

---

## 2. Architecture delta from vibe-coding-starter-kit

### KEEP (as-is — starter contract, do not strip/rename)
- **UI kit / design system** — `apps/web/src/components/ui/` (shadcn), design
  tokens in `apps/web/src/app/globals.css`, `/design` page. Restyle only via tokens.
- **Bucket Explorer (Files)** — `/files`, `apps/web/src/app/files/`,
  `apps/web/src/components/files/`. **NON-NEGOTIABLE keep** (full-bucket browse).
  Its sidebar entry stays. (Note: this app *also* adds a scoped Datasets explorer —
  see ADD. The two coexist: Files = whole bucket, Datasets = sample's own prefixes.)
- **Upload** — `/upload`, `apps/web/src/components/upload/`. Becomes the on-ramp for
  **source recordings**, writing to the `sources/` prefix.
- **Backend layering** `types → config → repo → service → runtime`, structural
  boundary tests (`tests/test_structure.py`), `repo/`-only boto3, lazy ML imports.
- **Data-fetching contract** — TanStack Query hooks in `lib/queries.ts`; no bare
  `useEffect + fetch`. New endpoint = 3 files (`runtime/<r>.py`, `lib/api-client.ts`,
  `lib/queries.ts`).
- Sidebar shell + Settings + Design System link + theme/header chrome.

### TRIM (remove from starter)
- **Image/PDF metadata extraction** — `service/metadata.py`, its Pillow/PyPDF2
  deps, `tests` for it, and `docs/features/metadata-extraction.md`. Irrelevant to
  audio. (Mirror what whisperx-diarized-archive trimmed.)
- Dashboard's generic file-upload widgets get **adapted**, not kept verbatim
  (see ADD/dashboard).
- Any image-thumbnail-only branches in `file-preview.tsx` — keep audio playback,
  drop image-only assumptions where they conflict.

### ADD (new for whisper-dataset-builder)
- **Datasets explorer (sample-specific, scoped)** — `/datasets` (list) and
  `/datasets/[id]` (detail). Scoped to the app's own `datasets/` + per-dataset
  prefixes. This is the mandated sample-specific asset explorer (alongside the
  kept full-bucket Files explorer). Mirror whisperx's `app/library/` + `app/library/[...key]/`
  and `components/library/` structure.
- **Backend**: `repo/dataset_store.py` (boto3, B2 dataset read/write), engine layer
  `service/engine/` (VAD, transcribe, quality, audio, device, _torch_safe, errors),
  `service/datasets.py` (build orchestration + CRUD), `service/jobs.py` (ephemeral
  build-progress registry — mirror whisperx), `runtime/datasets.py` (routes),
  `types/dataset.py` (Pydantic models).
- **Bulk CLI** — `services/api/scripts/build_dataset.py` (mirror
  `whisperx-diarized-archive/services/api/scripts/batch_transcribe.py`): build
  datasets for un-processed sources from the terminal. Wire `pnpm build:dataset`.
- **Two requirements files** — `requirements.txt` (base; API boots + all tests
  pass WITHOUT ML) and `requirements-ml.txt` (heavy local ML stack, lazy-imported).

### ADAPT
- **Dashboard** (`/`, `components/dashboard/`) → dataset metrics: recordings
  ingested, datasets built, total clips, total clip-hours, **avg
  write-amplification (clips per recording)**; recent builds table. Flows through
  `runtime → service → repo` + `lib/queries.ts`.
- **Settings** (`/settings`, `components/settings/settings-form.tsx`) → pipeline
  defaults (VAD engine, Whisper model, device, clip length bounds, SNR threshold,
  default layout). Keep it as the **form-UX exemplar** for the create/edit forms.
- **Header `pageTitles` map** (`components/layout/header.tsx`) — add entries for
  `/datasets` ("Datasets"). Detail route title derives from path (fine).
- **Sidebar nav** (`components/layout/app-sidebar.tsx`) — add a **Datasets** entry
  (icon e.g. `Database`/`AudioLines`) between Upload and Files. Keep Dashboard/
  Upload/Files/Settings/Design System.

---

## 3. B2 surface (S3-compatible only — no b2-native)

All via boto3 S3 client in `repo/` with `user_agent_extra="whisper-dataset-builder"`:
- `put_object` — upload source recordings (`sources/`), write clip wavs + metadata
  + manifest (`datasets/<id>/...`).
- `get_object` — fetch source for processing; fetch clips for in-browser preview.
- `list_objects_v2` (paginated) — list sources, list datasets, list a dataset's clips.
- `head_object` — object metadata.
- `delete_object` / `delete_objects` — **delete a dataset scoped to its own
  `datasets/<id>/` prefix** (never bucket-wide; honor the local safety rule).
- `generate_presigned_url` — in-browser audio playback + downloads.

No b2-native API anywhere. **Justified deviation: none.**

**On-B2 layout**
```
sources/<recording>.<ext>                     # uploaded long-form audio
datasets/<id>/dataset.json                     # manifest: config + stats + clip index
datasets/<id>/wavs/<clip_id>.wav               # segmented, filtered clips (16kHz mono)
datasets/<id>/metadata.csv                      # LJSpeech: id|transcript|normalized
datasets/<id>/metadata.jsonl                    # HF audiofolder: {file_name, transcription}
```
(LJSpeech writes `metadata.csv`; HF layout writes `metadata.jsonl` — chosen per build.)

---

## 4. Key features

Each feature seeds the README list + a `docs/features/<feature>.md` stub.

1. **Source ingest (`source-ingest`)** — upload long-form recordings to B2
   `sources/`; appear in Files (bucket) + selectable in the build form.
   *No external API.*
2. **pyannote VAD segmentation (`vad-segmentation`)** — split a recording into
   voice-active clips with pyannote.audio.
   - **Provider/model:** pyannote.audio `pyannote/segmentation-3.0` via
     `pyannote.audio.pipelines.VoiceActivityDetection` (the showcased engine).
   - **`deployment: local`** — CPU-default, autodetect CUDA → MPS → CPU (pyannote/
     torch support MPS). Inherits the CPU-default/GPU-autodetect hard rule.
   - **Key env var:** `HF_TOKEN` (free Hugging Face token — **weights-download
     gate only, NOT a paid inference API**). `pyannote/segmentation-3.0` is gated;
     the token + one-time terms acceptance is required to use the pyannote engine.
   - **Cost for one demo run:** $0 (local compute; HF token is free).
   - **Graceful degradation (resolves the "B2 credentials only" tension):** when
     `HF_TOKEN` is unset, fall back to a **token-free energy/`webrtcvad`-based VAD**
     so the app runs end-to-end with B2 credentials alone. `vad_engine="auto"` →
     pyannote if token present else fallback. README states pyannote is the
     recommended/showcased engine and names the fallback honestly. (See §note.)
3. **Quality filtering (`quality-filter`)** — drop clips below an SNR threshold and
   outside min/max duration; report kept-vs-dropped counts. *Local, numpy/soundfile.*
4. **Whisper transcription (`whisper-transcription`)** — transcribe each retained
   clip with Whisper.
   - **Provider/model:** `faster-whisper` (CTranslate2 Whisper), default model
     `base`, `compute_type=int8`. **Ungated, no token.**
   - **`deployment: local`** — CPU-default; autodetect CUDA → CPU. **MPS note:**
     CTranslate2 has no MPS backend, so on Apple Silicon faster-whisper maps
     MPS → CPU (int8). This is the documented per-library MPS-weakness fallback the
     autodetect rule allows; pyannote (step 2) still uses MPS.
   - **Cost for one demo run:** $0 (local).
5. **Dataset packaging (`dataset-packaging`)** — write clip wavs + transcript
   metadata + manifest to B2 in LJSpeech (`metadata.csv`) or HF audiofolder
   (`metadata.jsonl`) layout. Surfaces the **write-amplification** stat
   (1 recording → N clips). *No external API.*
6. **Serve / read-from-B2 (`serve-from-b2`)** — dataset detail previews clip↔
   transcript pairs (audio playback + text) and shows a copy-paste snippet to load
   the dataset **directly from B2** in a training pipeline
   (`datasets.load_dataset("audiofolder", ...)` / boto3 streaming over the S3
   endpoint). *No external API.*

**No external/paid provider. No Genblaze** — the description names no Genblaze /
`genblaze-*` stack, so AI calls are NOT routed through the Genblaze SDK; pyannote +
faster-whisper run as bare local OSS in `service/engine/` (lazy-imported).

### Primary-entity lifecycle — entity: **Dataset**
The single primary resource the app manages. DEFAULT = all lifecycle verbs in the UI:

| Verb | UI | Where |
|------|----|-------|
| **create** | ✅ | `/datasets` "New dataset" → create form (dialog or `/datasets/new`). Fields below. |
| **read** | ✅ | `/datasets` (list) + `/datasets/[id]` (detail: clips, transcripts, stats, layout preview, serve snippet). |
| **edit** | ✅ | Edit form pre-filled — rename/redescribe; build config editable only while status is `draft` (pre-build), locked after a successful build (clips already materialized). |
| **delete** | ✅ | Delete dataset record + **scoped** `datasets/<id>/` B2 prefix (confirm dialog; mirror starter `danger-zone`/`alert-dialog`). |
| **run** | ✅ | Run / re-run the build pipeline (VAD → filter → transcribe → package) with **live progress** via `service/jobs.py` (mirror whisperx transcribe-with-progress). |

`omitted_ui_verbs`: **none** — all five are built.

### Form UX conventions (create + edit forms)
Exemplar: `apps/web/src/components/settings/settings-form.tsx` (does selectors +
defaults already). For the Dataset create/edit forms:

(a) **Finite-value fields → selectors** (`Select`/`RadioGroup`), never free text:
- `source_key` — `Select` populated from the `sources/` listing (the uploaded recordings).
- `vad_engine` — `Select`: `auto` | `pyannote` | `energy`.
- `whisper_model` — `Select`: `tiny` | `base` | `small`.
- `language` — `Select`: `auto` | `en` | `es` | … (a short curated list).
- `layout` — `RadioGroup`/`Select`: `ljspeech` | `hf_audiofolder`.
- Free-text only for: `name`, `description`, and numeric bounds (number inputs).

(b) **CREATE form safe defaults as placeholder / `FormDescription` guidance**
(guidance only — never an autofill button), tuned for a sound test run:
- `vad_engine`: `auto` (uses pyannote if `HF_TOKEN` set, else energy fallback).
- `whisper_model`: `base`; `language`: `auto`.
- `min_clip_sec`: `1.0`; `max_clip_sec`: `20.0`; `min_snr_db`: `10`.
- `layout`: `ljspeech`.
The edit form opens pre-filled with the real resource (no default hints).

---

## 5. Doc transforms

- **Rewrite**: `docs/features/dashboard.md` → dataset metrics. `docs/features/file-upload.md`
  → source ingest (`source-ingest.md`). `docs/features/file-browser.md` → keep
  (Files/bucket explorer) but note the added scoped Datasets explorer.
- **Delete**: `docs/features/metadata-extraction.md` (trimmed feature).
- **New stubs** (use `docs/features/_template.md`): `vad-segmentation.md`,
  `quality-filter.md`, `whisper-transcription.md`, `dataset-packaging.md`,
  `serve-from-b2.md`, `datasets-explorer.md`.
- **README.md** — rewrite around the dataset-builder workflow; **honestly document
  the HF-token model**: "pyannote VAD (the showcased engine) needs a *free* Hugging
  Face token to download gated weights — accept the terms once. It is not a paid
  API. Without it, the app falls back to a built-in energy VAD so you can run
  end-to-end with B2 credentials alone." Document `pip install -r requirements-ml.txt`
  + ffmpeg + CPU-default/GPU notes.
- **AGENTS.md / ARCHITECTURE.md** — update repo map, realized contract (keep/add/
  adapt/trim), engine invariants (lazy ML, boto3 only in repo, no whisperx — pyannote
  + faster-whisper direct), commands (`pnpm build:dataset`).
- **`.env.example`** — Standard #3 names (see §6) + `HF_TOKEN=` (commented:
  free, optional, enables pyannote VAD) + pipeline knob defaults. Placeholders only.

---

## 6. Rename table

| From (starter) | To (`whisper-dataset-builder`) |
|---|---|
| `vibe-coding-starter-kit` / `oss-starter-kit` (pkg, dirs, slugs) | `whisper-dataset-builder` |
| `APP_NAME = "OSS Starter Kit"` (`lib/app-config.ts`) | `"Whisper Dataset Builder"` |
| `APP_DESCRIPTION` | `"Build training-ready speech datasets from B2 audio with pyannote VAD + Whisper"` |
| root `package.json` `name`, `apps/web` + `services` pkg names | `whisper-dataset-builder*` (snake/kebab as each file requires) |
| `user_agent_extra="b2ai-oss-start"` (`repo/b2_client.py`) | `user_agent_extra="whisper-dataset-builder"` |
| UTM `utm_content=b2ai-oss-start` (`app-sidebar.tsx` footer) | `utm_content=whisper-dataset-builder` |
| infra/railway service name + image tags | `whisper-dataset-builder` |
| Title Case display strings ("OSS Starter Kit") | "Whisper Dataset Builder" |
| **Env var renames (Standard #3 — hard requirement; starter ships non-standard)** | |
| `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` |
| `B2_ENDPOINT` (hardcoded URL) | derive from `B2_REGION` (port whisperx `settings.py`: `b2_endpoint` property from region) |
| (add) | `B2_PUBLIC_URL_BASE` |
| `B2_APPLICATION_KEY`, `B2_BUCKET_NAME` | unchanged (already standard) |

> **Settings note:** port `whisperx-diarized-archive/services/api/app/config/settings.py`
> verbatim-in-spirit: Standard #3 names, region-derived `b2_endpoint` (no hardcoded
> region/endpoint string anywhere), plus the pipeline knobs. Align `repo/b2_client.py`
> reads to those names (`settings.b2_application_key_id`, `settings.b2_application_key`,
> `settings.b2_public_url_base`).

---

## Notes / tensions (recorded per skill requirements)

- **pyannote gating vs "B2 credentials only".** `pyannote/segmentation-3.0` is
  HF-gated; the description promises "no second API key, B2 credentials only."
  Resolution: pyannote.audio is the **showcased, default-when-token-present** VAD
  engine (vendor fidelity — the trending OSS is pyannote.audio, per the
  vendor-fidelity rule), and a **token-free energy/webrtcvad fallback** guarantees
  the app runs end-to-end with B2 creds alone. The HF token is a *free
  weights-download gate*, not a paid inference API — README says so explicitly.
  This mirrors the proven graceful-degradation pattern in whisperx-diarized-archive
  (where HF_TOKEN gated only the optional diarization). For autonomous verify, the
  energy fallback means a green run needs **no** HF token.
- **Bucket Explorer kept + scoped explorer added** — both present, no tension to
  resolve beyond the mandated coexistence; recorded here for completeness.
- **No whisperx** — we use pyannote.audio *directly* for VAD (so VAD is a visible,
  standalone pipeline step, true to the description) and faster-whisper directly
  for transcription. This keeps the two trending tools cleanly separated and avoids
  whisperx bundling its own VAD (which would obscure the pyannote demonstration).
  Reuse `_torch_safe.py::allowlist_pyannote_globals()` (torch 2.6+ weights_only)
  before any pyannote checkpoint load. Pin `pyannote.audio>=3.3.2,<4` (4.x pulls a
  separately-gated community-1 weight → 403; see whisperx sample's requirements-ml.txt).
