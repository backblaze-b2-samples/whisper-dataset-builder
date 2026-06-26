"""Dataset build pipeline: one source recording fans out into many clips.

Flow (the write-amplification story — 1 recording -> N labeled clip pairs):

    sources/<rec>  --download-->  decode/resample -->
        pyannote VAD (or energy fallback) -> voice-active spans -->
        quality filter (SNR + duration) -> kept clips -->
        faster-whisper transcribe each clip -->
    write  datasets/<id>/wavs/<clip>.wav
           datasets/<id>/metadata.csv (LJSpeech) | metadata.jsonl (HF)
           datasets/<id>/dataset.json (manifest + stats)

This module owns NO boto3 — it calls the repo for all B2 I/O and the engine for
all local ML compute. The engine's heavy imports stay lazy, so importing this
module is cheap. Builds run in a background thread; progress is reported via the
ephemeral jobs registry.
"""

import io
import logging
import os
from datetime import UTC, datetime

from app.config import settings
from app.repo import get_object_bytes, put_bytes, put_json
from app.service import engine, jobs
from app.types import Clip, Dataset, DatasetStats

logger = logging.getLogger(__name__)


def manifest_key(dataset_id: str) -> str:
    return f"{settings.dataset_prefix}{dataset_id}/dataset.json"


def _wav_key(dataset_id: str, clip_id: str) -> str:
    return f"{settings.dataset_prefix}{dataset_id}/wavs/{clip_id}.wav"


def _metadata_key(dataset_id: str, layout: str) -> str:
    name = "metadata.csv" if layout == "ljspeech" else "metadata.jsonl"
    return f"{settings.dataset_prefix}{dataset_id}/{name}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def build_dataset(dataset: Dataset, job_id: str | None = None) -> Dataset:
    """Run the full pipeline for one dataset manifest and persist results to B2.

    Updates the live job registry as it advances when a job_id is given.
    Returns the updated manifest. Raises on engine / B2 failure (caller records
    the error on the job + manifest).
    """

    def progress(status, pct, message=None):
        if job_id:
            jobs.update_job(job_id, status=status, progress=pct, message=message)

    cfg = dataset.config
    suffix = os.path.splitext(cfg.source_key)[1]

    progress("loading", 0.05, "Downloading source recording from B2")
    media_bytes = get_object_bytes(cfg.source_key)
    samples, sr = engine.load_waveform(
        media_bytes, suffix, settings.target_sample_rate
    )

    vad_engine = engine.resolve_engine(cfg.vad_engine)
    progress("detecting", 0.2, f"Detecting voice activity ({vad_engine} VAD)")
    spans = engine.detect_voice_segments(samples, sr, vad_engine)

    progress("filtering", 0.4, "Filtering clips by SNR + duration")
    candidates = []
    dropped = 0
    for start, end in spans:
        clip_samples = engine.slice_samples(samples, sr, start, end)
        kept, _reason, snr = engine.passes_filters(
            clip_samples,
            sr,
            min_clip_sec=cfg.min_clip_sec,
            max_clip_sec=cfg.max_clip_sec,
            min_snr_db=cfg.min_snr_db,
        )
        if kept:
            candidates.append((start, end, clip_samples, snr))
        else:
            dropped += 1

    progress("transcribing", 0.5, f"Transcribing {len(candidates)} clips (Whisper)")
    model = engine.load_model(cfg.whisper_model)
    clips: list[Clip] = []
    detected_language: str | None = None
    rows_csv: list[str] = []
    rows_jsonl: list[dict] = []

    for i, (start, end, clip_samples, snr) in enumerate(candidates):
        clip_id = f"{dataset.id}_{i:04d}"
        result = engine.transcribe_clip(model, clip_samples, cfg.language)
        text = result["text"]
        detected_language = detected_language or result.get("language")
        if not text:
            dropped += 1
            continue

        wav_bytes = engine.encode_wav(clip_samples, sr)
        put_bytes(_wav_key(dataset.id, clip_id), wav_bytes, "audio/wav")
        duration = engine.duration_seconds(clip_samples, sr)
        clips.append(
            Clip(
                clip_id=clip_id,
                wav_key=_wav_key(dataset.id, clip_id),
                start=round(start, 3),
                end=round(end, 3),
                duration=round(duration, 3),
                snr_db=round(snr, 2),
                transcript=text,
            )
        )
        rows_csv.append(f"{clip_id}|{text}|{text}")
        rows_jsonl.append({"file_name": f"wavs/{clip_id}.wav", "transcription": text})

        if candidates:
            progress("transcribing", 0.5 + 0.4 * (i + 1) / len(candidates))

    progress("packaging", 0.92, "Writing dataset metadata + manifest to B2")
    _write_metadata(dataset.id, cfg.layout, rows_csv, rows_jsonl)

    total_seconds = sum(c.duration for c in clips)
    stats = DatasetStats(
        source_clips_detected=len(spans),
        clips_kept=len(clips),
        clips_dropped=dropped,
        total_clip_seconds=round(total_seconds, 2),
        # One source recording -> N kept clips. The headline B2 story.
        write_amplification=float(len(clips)),
        vad_engine_used=vad_engine,
        language=detected_language or (None if cfg.language == "auto" else cfg.language),
    )

    updated = dataset.model_copy(
        update={
            "status": "ready",
            "stats": stats,
            "clips": clips,
            "error": None,
            "updated_at": _now(),
        }
    )
    put_json(manifest_key(dataset.id), updated.model_dump())

    progress("done", 1.0, f"Built {len(clips)} clips ({stats.write_amplification:g}x)")
    logger.info(
        "Built dataset id=%s clips=%d dropped=%d engine=%s",
        dataset.id,
        len(clips),
        dropped,
        vad_engine,
    )
    return updated


def _write_metadata(
    dataset_id: str, layout: str, rows_csv: list[str], rows_jsonl: list[dict]
) -> None:
    """Write the transcript metadata file in the chosen layout."""
    import json

    key = _metadata_key(dataset_id, layout)
    if layout == "ljspeech":
        body = "\n".join(rows_csv).encode("utf-8")
        put_bytes(key, body, "text/csv")
    else:
        buf = io.StringIO()
        for row in rows_jsonl:
            buf.write(json.dumps(row, ensure_ascii=False) + "\n")
        put_bytes(key, buf.getvalue().encode("utf-8"), "application/x-ndjson")


def run_job(job_id: str, dataset: Dataset) -> None:
    """Background entrypoint: run the build, recording errors on job + manifest."""
    try:
        build_dataset(dataset, job_id=job_id)
    except Exception as e:  # surface any failure on the job + manifest
        logger.exception("Build job failed: dataset=%s", dataset.id)
        jobs.update_job(job_id, status="error", error=str(e))
        failed = dataset.model_copy(
            update={"status": "error", "error": str(e), "updated_at": _now()}
        )
        try:
            put_json(manifest_key(dataset.id), failed.model_dump())
        except Exception:  # best effort — the job already carries the error
            logger.exception("Failed to persist error manifest: %s", dataset.id)
