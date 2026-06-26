"""Dataset CRUD + dashboard aggregations derived from B2.

The dataset registry is the datasets/ prefix on B2: each dataset is a
datasets/<id>/dataset.json manifest. There is no application DB — the manifest
is authoritative. Dashboard stats roll up the same manifests.

No boto3 — everything goes through the repo. ML lives in the engine + build
module, not here.
"""

import logging
import uuid
from datetime import UTC, datetime

from app.config import settings
from app.repo import (
    delete_prefix,
    get_json,
    list_files,
    list_keys,
    put_json,
)
from app.service.build import manifest_key
from app.service.files import validate_key
from app.types import (
    Dataset,
    DatasetConfig,
    DatasetStatsSummary,
    DatasetSummary,
    SourceRecording,
)

logger = logging.getLogger(__name__)


class DatasetNotFound(Exception):
    """Raised when a dataset id has no manifest."""


class DatasetLocked(Exception):
    """Raised when editing build config on a non-draft dataset."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def list_sources() -> list[SourceRecording]:
    """List uploaded source recordings selectable in the build form."""
    out: list[SourceRecording] = []
    for f in list_files(prefix=settings.source_prefix, max_keys=1000):
        if f.key.endswith("/"):
            continue
        out.append(
            SourceRecording(
                key=f.key,
                filename=f.filename,
                size_bytes=f.size_bytes,
                size_human=f.size_human,
                uploaded_at=f.uploaded_at.isoformat(),
            )
        )
    return out


def _manifest_ids() -> list[str]:
    """Return every dataset id that has a manifest in B2."""
    keys = list_keys(prefix=settings.dataset_prefix)
    ids: list[str] = []
    for k in keys:
        if k.endswith("/dataset.json"):
            # datasets/<id>/dataset.json -> <id>
            ids.append(k[len(settings.dataset_prefix):].split("/", 1)[0])
    return ids


def list_datasets() -> list[DatasetSummary]:
    """List all datasets as lightweight summaries (newest first)."""
    summaries: list[DatasetSummary] = []
    for ds_id in _manifest_ids():
        obj = get_json(manifest_key(ds_id))
        if not obj:
            continue
        ds = Dataset(**obj)
        summaries.append(
            DatasetSummary(
                id=ds.id,
                name=ds.name,
                description=ds.description,
                status=ds.status,
                source_key=ds.config.source_key,
                layout=ds.config.layout,
                clips_kept=ds.stats.clips_kept,
                total_clip_seconds=ds.stats.total_clip_seconds,
                write_amplification=ds.stats.write_amplification,
                created_at=ds.created_at,
                updated_at=ds.updated_at,
            )
        )
    summaries.sort(key=lambda s: s.created_at, reverse=True)
    return summaries


def get_dataset(dataset_id: str) -> Dataset:
    """Fetch a dataset manifest. Raises DatasetNotFound if absent."""
    obj = get_json(manifest_key(dataset_id))
    if obj is None:
        raise DatasetNotFound(dataset_id)
    return Dataset(**obj)


def create_dataset(name: str, description: str, config: DatasetConfig) -> Dataset:
    """Create a new draft dataset manifest in B2."""
    validate_key(config.source_key)
    now = _now()
    ds = Dataset(
        id=uuid.uuid4().hex[:12],
        name=name.strip() or "Untitled dataset",
        description=description.strip(),
        status="draft",
        config=config,
        created_at=now,
        updated_at=now,
    )
    put_json(manifest_key(ds.id), ds.model_dump())
    logger.info("Created dataset id=%s source=%s", ds.id, config.source_key)
    return ds


def update_dataset(
    dataset_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    config: DatasetConfig | None = None,
) -> Dataset:
    """Rename / redescribe a dataset; edit build config only while draft."""
    ds = get_dataset(dataset_id)
    updates: dict = {"updated_at": _now()}
    if name is not None:
        updates["name"] = name.strip() or ds.name
    if description is not None:
        updates["description"] = description.strip()
    if config is not None:
        if ds.status != "draft":
            raise DatasetLocked(dataset_id)
        validate_key(config.source_key)
        updates["config"] = config
    updated = ds.model_copy(update=updates)
    put_json(manifest_key(dataset_id), updated.model_dump())
    return updated


def delete_dataset(dataset_id: str) -> int:
    """Delete a dataset's manifest + all artifacts, SCOPED to its own prefix."""
    # Confirm it exists (raises if not) so callers get a clean 404.
    get_dataset(dataset_id)
    prefix = f"{settings.dataset_prefix}{dataset_id}/"
    deleted = delete_prefix(prefix)
    logger.info("Deleted dataset id=%s objects=%d", dataset_id, deleted)
    return deleted


def mark_building(dataset_id: str) -> Dataset:
    """Flip a dataset to 'building' before a run (so the UI reflects it)."""
    ds = get_dataset(dataset_id)
    updated = ds.model_copy(update={"status": "building", "updated_at": _now()})
    put_json(manifest_key(dataset_id), updated.model_dump())
    return updated


def get_dashboard_stats() -> DatasetStatsSummary:
    """Roll up builder metrics for the dashboard."""
    sources = [
        f for f in list_files(prefix=settings.source_prefix, max_keys=1000)
        if not f.key.endswith("/")
    ]
    datasets = list_datasets()
    built = [d for d in datasets if d.status == "ready"]
    total_clips = sum(d.clips_kept for d in built)
    total_seconds = sum(d.total_clip_seconds for d in built)
    amps = [d.write_amplification for d in built if d.write_amplification > 0]
    avg_amp = round(sum(amps) / len(amps), 2) if amps else 0.0
    return DatasetStatsSummary(
        recordings_ingested=len(sources),
        datasets_built=len(built),
        total_clips=total_clips,
        total_clip_hours=round(total_seconds / 3600.0, 2),
        avg_write_amplification=avg_amp,
    )


def serve_snippet(dataset: Dataset) -> str:
    """A copy-paste snippet to load the dataset directly from B2."""
    base = settings.b2_public_url_base or "https://s3.<region>.backblazeb2.com/<bucket>"
    prefix = f"{settings.dataset_prefix}{dataset.id}/"
    if dataset.config.layout == "hf_audiofolder":
        return (
            "from datasets import load_dataset\n"
            f'ds = load_dataset("audiofolder", data_dir="{base}/{prefix}")'
        )
    return (
        "# LJSpeech layout: stream metadata.csv + wavs/ from B2 over the S3 API\n"
        f'# bucket prefix: {prefix}\n'
        f'#   {prefix}metadata.csv   (id|transcript|normalized)\n'
        f'#   {prefix}wavs/<clip>.wav'
    )
