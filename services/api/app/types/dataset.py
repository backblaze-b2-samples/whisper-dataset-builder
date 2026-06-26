"""Pydantic models for the speech-dataset builder.

Pure data — no logic, no imports from other app layers (types is the bottom
layer). These are the contract shared with the frontend via
packages/shared/src/types.ts.
"""

from typing import Literal

from pydantic import BaseModel

# Build-job lifecycle, surfaced live in the UI via service/jobs.py.
JobStatus = Literal[
    "queued",
    "loading",
    "detecting",
    "filtering",
    "transcribing",
    "packaging",
    "done",
    "error",
]

VadEngine = Literal["auto", "pyannote", "energy"]
WhisperModel = Literal["tiny", "base", "small"]
Layout = Literal["ljspeech", "hf_audiofolder"]
DatasetStatus = Literal["draft", "building", "ready", "error"]


class DatasetConfig(BaseModel):
    """The build configuration for one dataset (editable while draft)."""

    source_key: str
    vad_engine: VadEngine = "auto"
    whisper_model: WhisperModel = "base"
    language: str = "auto"
    layout: Layout = "ljspeech"
    min_clip_sec: float = 1.0
    max_clip_sec: float = 20.0
    min_snr_db: float = 10.0


class Clip(BaseModel):
    """One segmented, filtered, transcribed clip in a dataset."""

    clip_id: str
    wav_key: str
    start: float
    end: float
    duration: float
    snr_db: float
    transcript: str


class DatasetStats(BaseModel):
    """Roll-up stats for a built dataset (stored in dataset.json)."""

    source_clips_detected: int = 0
    clips_kept: int = 0
    clips_dropped: int = 0
    total_clip_seconds: float = 0.0
    # The write-amplification story: kept clips per source recording.
    write_amplification: float = 0.0
    vad_engine_used: str = ""
    language: str | None = None


class Dataset(BaseModel):
    """Primary entity. The manifest persisted at datasets/<id>/dataset.json."""

    id: str
    name: str
    description: str = ""
    status: DatasetStatus = "draft"
    config: DatasetConfig
    stats: DatasetStats = DatasetStats()
    clips: list[Clip] = []
    error: str | None = None
    created_at: str
    updated_at: str


class DatasetSummary(BaseModel):
    """Lightweight dataset row for the list view (no per-clip detail)."""

    id: str
    name: str
    description: str = ""
    status: DatasetStatus
    source_key: str
    layout: Layout
    clips_kept: int = 0
    total_clip_seconds: float = 0.0
    write_amplification: float = 0.0
    created_at: str
    updated_at: str


class BuildJob(BaseModel):
    """Live, process-local build progress. Ephemeral — see service/jobs.py."""

    id: str
    dataset_id: str
    status: JobStatus
    progress: float = 0.0
    message: str | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class DatasetStatsSummary(BaseModel):
    """Dashboard metrics derived from B2 listings + manifests."""

    recordings_ingested: int
    datasets_built: int
    total_clips: int
    total_clip_hours: float
    avg_write_amplification: float


class SourceRecording(BaseModel):
    """An uploaded source recording selectable in the build form."""

    key: str
    filename: str
    size_bytes: int
    size_human: str
    uploaded_at: str
