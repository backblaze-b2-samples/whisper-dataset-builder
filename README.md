<!-- last_verified: 2026-06-26 -->
# Whisper Dataset Builder

Turn long-form audio stored on **[Backblaze B2](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-whisper-dataset-builder)** into a **training-ready speech dataset** — clip + transcript pairs in a standard layout (LJSpeech or HuggingFace `audiofolder`). Upload a raw recording, run the pipeline, and a single long file fans out into many labeled clips written back to B2, ready to be read directly by a training pipeline.

Built for ML engineers and speech researchers building custom ASR/TTS models, and teams doing low-resource language data collection from field recordings.

**The pipeline (all local OSS — no paid inference API):**
1. **Source ingest** — upload long-form recordings to B2 (`sources/`).
2. **pyannote VAD segmentation** — split a recording into voice-active clips with [pyannote.audio](https://github.com/pyannote/pyannote-audio).
3. **Quality filtering** — drop clips outside duration bounds or below an SNR threshold.
4. **Whisper transcription** — transcribe each retained clip with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
5. **Dataset packaging** — write clip wavs + transcript metadata + a manifest to B2.
6. **Serve from B2** — load the dataset directly from B2 in a training pipeline.

The headline B2 story is **write-amplification**: one source recording → N labeled clip/transcript pairs, all stored on B2 over the S3-compatible API.

## The Hugging Face token (honest version)

pyannote VAD is the **showcased, recommended engine**. Its `segmentation-3.0` weights are gated, so to use it you need a **free** Hugging Face token and a one-time terms acceptance:

1. Create a token at <https://huggingface.co/settings/tokens>.
2. Accept the model terms at <https://huggingface.co/pyannote/segmentation-3.0>.
3. Put the token in `.env` as `HF_TOKEN=...`.

**This is a weights-download gate, not a paid inference API — it is never billed.**

**Don't have a token? The app still runs end-to-end with B2 credentials alone.** When `HF_TOKEN` is unset, the builder falls back to a built-in **token-free energy VAD**. Set `VAD_ENGINE=auto` (the default) to use pyannote when a token is present and the energy fallback otherwise. faster-whisper transcription is ungated and needs no token either way.

## On-B2 layout

```
sources/<recording>.<ext>            # uploaded long-form audio
datasets/<id>/dataset.json           # manifest: config + stats + clip index
datasets/<id>/wavs/<clip_id>.wav     # segmented, filtered clips (16kHz mono)
datasets/<id>/metadata.csv           # LJSpeech: id|transcript|normalized
datasets/<id>/metadata.jsonl         # HF audiofolder: {file_name, transcription}
```
(LJSpeech writes `metadata.csv`; the HF layout writes `metadata.jsonl` — chosen per build.)

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.11, `ffmpeg` on PATH, and a free **[Backblaze B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-whisper-dataset-builder)**.

**1. Install JS dependencies**

```bash
pnpm install
```

**2. Set up the backend**

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt           # API boots + all tests pass with just this
cd ../..
```

**3. (Optional, to run the pipeline) install the ML stack + ffmpeg**

```bash
cd services/api && source .venv/bin/activate
pip install -r requirements-ml.txt        # pyannote.audio, faster-whisper, torch, librosa, …
# macOS:  brew install ffmpeg
# Debian: sudo apt-get install ffmpeg
cd ../..
```

The heavy ML deps are lazy-imported, so the API and `pnpm test:api` / `pnpm check:structure` / `pnpm lint:api` all work **without** `requirements-ml.txt`.

**4. Add your B2 credentials**

```bash
cp .env.example .env
```

Then in the [Backblaze B2 dashboard](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-whisper-dataset-builder):

1. **Create a bucket** → paste its name into `B2_BUCKET_NAME` and its region into `B2_REGION` (the S3 endpoint is derived from the region — no endpoint URL to copy).
2. **Create an application key** with `Read and Write` → paste **keyID** into `B2_APPLICATION_KEY_ID` and **applicationKey** into `B2_APPLICATION_KEY` *(only shown once)*.
3. *(Optional)* add a free `HF_TOKEN` to enable the pyannote VAD engine.

**5. Run it**

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000`. Upload a recording, then go to **Datasets → New dataset** and run a build.

**Device note:** the engine auto-detects the best device (CUDA → Apple MPS → CPU) and **defaults to CPU** — no GPU required. pyannote/torch use MPS where available; faster-whisper (CTranslate2) has no MPS backend, so on Apple Silicon it maps MPS → CPU (int8).

### Bulk build from the terminal

```bash
pnpm build:dataset                          # build a dataset for every source recording
pnpm build:dataset -- --source sources/x.wav --layout hf_audiofolder
```

## Features

- [Source ingest](docs/features/source-ingest.md) — upload long-form recordings to B2
- [VAD segmentation](docs/features/vad-segmentation.md) — pyannote VAD (with energy fallback)
- [Quality filter](docs/features/quality-filter.md) — SNR + duration filtering
- [Whisper transcription](docs/features/whisper-transcription.md) — faster-whisper, local
- [Dataset packaging](docs/features/dataset-packaging.md) — LJSpeech / HF audiofolder + manifest
- [Serve from B2](docs/features/serve-from-b2.md) — load the dataset straight from B2
- [Datasets explorer](docs/features/datasets-explorer.md) — scoped explorer for the app's own datasets
- [File browser](docs/features/file-browser.md) — full-bucket explorer (kept from the starter)
- [Design System](docs/design-system.md) — tokens, primitives, loader, error/empty states (`/design`)

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, Recharts
- TanStack Query — caching, dedup, retry for every fetch
- Python 3.11+, FastAPI, boto3, Pydantic v2
- Local ML (lazy-imported): pyannote.audio (VAD), faster-whisper (transcription), torch, librosa, soundfile
- Backblaze B2 (S3-compatible object storage)
- pnpm workspaces (monorepo)

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm dev` | Start frontend + backend |
| `pnpm dev:web` / `pnpm dev:api` | Frontend / backend only |
| `pnpm build` | Build frontend |
| `pnpm lint` / `pnpm lint:api` | Lint frontend / backend (ruff) |
| `pnpm test:api` | Run backend tests (no ML stack needed) |
| `pnpm check:structure` | Verify layering rules |
| `pnpm build:dataset` | Bulk-build datasets from B2 sources (needs the ML stack) |
| `pnpm test:e2e` | Playwright e2e tests (`pnpm --filter @whisper-dataset-builder/web exec playwright install chromium` once first) |

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, data flows |
| [docs/features/](docs/features/) | Feature docs |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows and testing |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |

## License

MIT License - see [LICENSE](LICENSE) for details.
