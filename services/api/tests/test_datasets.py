"""Tests for the dataset CRUD, build-enqueue, stats, and sources endpoints.

These mock the repo so they run WITHOUT B2 or the ML stack installed — the
whole point of the lazy-import design + manifest-as-DB model.
"""

from datetime import UTC, datetime

import pytest

from app.service import datasets as datasets_service
from app.types import FileMetadata


def _source(key: str) -> FileMetadata:
    return FileMetadata(
        key=key,
        filename=key.split("/")[-1],
        folder="sources/",
        size_bytes=2048,
        size_human="2.0 KB",
        content_type="audio/wav",
        uploaded_at=datetime(2026, 6, 1, tzinfo=UTC),
        url=None,
    )


def _manifest(ds_id: str, status: str = "ready", clips: int = 5, amp: float = 5.0) -> dict:
    now = "2026-06-01T00:00:00+00:00"
    return {
        "id": ds_id,
        "name": f"Dataset {ds_id}",
        "description": "",
        "status": status,
        "config": {"source_key": "sources/a.wav", "layout": "ljspeech"},
        "stats": {
            "clips_kept": clips,
            "total_clip_seconds": 60.0,
            "write_amplification": amp,
        },
        "clips": [],
        "created_at": now,
        "updated_at": now,
    }


@pytest.mark.asyncio
async def test_list_sources(client, monkeypatch):
    monkeypatch.setattr(
        datasets_service,
        "list_files",
        lambda prefix, max_keys: [_source("sources/a.wav"), _source("sources/b.mp3")],
    )
    response = await client.get("/datasets/sources")
    assert response.status_code == 200
    keys = {s["key"] for s in response.json()}
    assert keys == {"sources/a.wav", "sources/b.mp3"}


@pytest.mark.asyncio
async def test_create_dataset(client, monkeypatch):
    saved = {}
    monkeypatch.setattr(
        datasets_service, "put_json", lambda key, obj: saved.update({key: obj})
    )
    response = await client.post(
        "/datasets",
        json={
            "name": "My set",
            "description": "demo",
            "config": {"source_key": "sources/a.wav", "layout": "ljspeech"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert body["config"]["source_key"] == "sources/a.wav"
    assert len(saved) == 1


@pytest.mark.asyncio
async def test_create_rejects_bad_source_key(client):
    response = await client.post(
        "/datasets",
        json={"name": "x", "config": {"source_key": "../etc/passwd"}},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_dataset_404(client, monkeypatch):
    monkeypatch.setattr(datasets_service, "get_json", lambda key: None)
    response = await client.get("/datasets/missing")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_stats_rollup(client, monkeypatch):
    monkeypatch.setattr(
        datasets_service,
        "list_files",
        lambda prefix, max_keys: [_source("sources/a.wav")],
    )
    monkeypatch.setattr(
        datasets_service, "list_keys", lambda prefix: ["datasets/d1/dataset.json"]
    )
    monkeypatch.setattr(
        datasets_service, "get_json", lambda key: _manifest("d1", clips=8, amp=8.0)
    )
    response = await client.get("/datasets/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["recordings_ingested"] == 1
    assert body["datasets_built"] == 1
    assert body["total_clips"] == 8
    assert body["avg_write_amplification"] == 8.0


@pytest.mark.asyncio
async def test_edit_config_locked_after_build(client, monkeypatch):
    monkeypatch.setattr(datasets_service, "get_json", lambda key: _manifest("d1", status="ready"))
    monkeypatch.setattr(datasets_service, "put_json", lambda key, obj: None)
    response = await client.patch(
        "/datasets/d1",
        json={"config": {"source_key": "sources/b.wav", "layout": "ljspeech"}},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_edit_name_allowed_after_build(client, monkeypatch):
    monkeypatch.setattr(datasets_service, "get_json", lambda key: _manifest("d1", status="ready"))
    saved = {}
    monkeypatch.setattr(datasets_service, "put_json", lambda key, obj: saved.update({key: obj}))
    response = await client.patch("/datasets/d1", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


@pytest.mark.asyncio
async def test_delete_dataset_scoped(client, monkeypatch):
    monkeypatch.setattr(datasets_service, "get_json", lambda key: _manifest("d1"))
    captured = {}

    def fake_delete_prefix(prefix):
        captured["prefix"] = prefix
        return 3

    monkeypatch.setattr(datasets_service, "delete_prefix", fake_delete_prefix)
    response = await client.delete("/datasets/d1")
    assert response.status_code == 200
    # Delete must be scoped to the dataset's own prefix, never bucket-wide.
    assert captured["prefix"] == "datasets/d1/"
    assert response.json()["objects"] == 3


@pytest.mark.asyncio
async def test_build_enqueues_job(client, monkeypatch):
    from app.runtime import datasets as datasets_router

    monkeypatch.setattr(datasets_service, "get_json", lambda key: _manifest("d1", status="draft"))
    monkeypatch.setattr(datasets_service, "put_json", lambda key, obj: None)
    called = {}
    monkeypatch.setattr(
        datasets_router, "run_job", lambda job_id, ds: called.update({"id": job_id})
    )
    response = await client.post("/datasets/d1/build")
    assert response.status_code == 200
    body = response.json()
    assert body["dataset_id"] == "d1"
    assert body["status"] == "queued"


def test_delete_prefix_refuses_unscoped(monkeypatch):
    """The repo guard must refuse an empty / root-level delete prefix."""
    from app.repo import dataset_store

    for bad in ("", "/", "datasets/"):
        with pytest.raises(ValueError):
            dataset_store.delete_prefix(bad)
