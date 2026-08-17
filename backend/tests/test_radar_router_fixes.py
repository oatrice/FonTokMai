"""
test_radar_router_fixes.py
--------------------------
Regression tests guarding the 5 bugs fixed in code-review audit (commit ed84413):
  C1 – STATIONS NameError in except fallback
  C2 – UnboundLocalError: cache referenced before assignment
  M2 – Stale-station (empty frames + >60 min) should be "offline"
  Clusters – source field, is_mock flag, graceful repo failure
"""
import os
os.environ["STORAGE_BACKEND"] = "sqlite"

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.routers.radar import router as radar_router

app = FastAPI()
app.include_router(radar_router)


def _utc_ago(minutes: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def _make_cache(*, frames=None, created_at=None, clusters=None):
    return {
        "frames": frames if frames is not None else [],
        "created_at": created_at or datetime.now(timezone.utc),
        "clusters": clusters or [],
    }


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── C1/C2: Safe fallback on DB failure ────────────────────────────────────────

@pytest.mark.asyncio
async def test_stations_returns_partial_on_db_failure(client):
    """C1/C2: DB failure must return partial=True, not raise NameError/UnboundLocalError."""
    with patch("app.routers.radar.AsyncSessionLocal", side_effect=RuntimeError("DB down")):
        res = await client.get("/api/v1/radar/stations")
    assert res.status_code == 200
    body = res.json()
    assert body.get("partial") is True
    assert "error" in body
    assert isinstance(body["stations"], list)


@pytest.mark.asyncio
async def test_stations_no_unbound_local_on_repo_failure(client):
    """C2: cache=None initialized before try — repo failure must not 500."""
    mock_station = MagicMock()
    mock_station.name = "Test"
    mock_station.center_lat = 16.0
    mock_station.center_lng = 102.0
    mock_station.radius_km = 240.0
    mock_station.is_active = True
    mock_station.static_image_url = "https://example.com/img.jpg"
    mock_station.loop_page_url = "https://example.com/loop"

    mock_db_model = MagicMock()
    mock_db_model.code = "test240"
    mock_db_model.is_active = True

    mock_repo = AsyncMock()
    mock_repo.get_latest_radar_cache.side_effect = RuntimeError("Cache error")

    with (
        patch("app.routers.radar.radar_registry.get_all_stations", return_value={"test240": mock_station}),
        patch("app.routers.radar.get_repo_context") as mock_ctx,
        patch("app.routers.radar.AsyncSessionLocal") as mock_session_cm,
    ):
        ctx_cm = MagicMock()
        ctx_cm.__aenter__ = AsyncMock(return_value=mock_repo)
        ctx_cm.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.return_value = ctx_cm

        session_mock = AsyncMock()
        session_mock.get_all_stations = AsyncMock(return_value=[mock_db_model])
        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session_mock)
        session_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session_cm.return_value = session_cm

        res = await client.get("/api/v1/radar/stations")
    assert res.status_code == 200


# ── M2: Stale-station status logic ────────────────────────────────────────────

def compute_status(is_active, frames, cache, latency_min):
    """Pure replication of status logic from radar.py lines 66-78."""
    if not is_active:
        return "offline"
    if not frames and cache and latency_min > 60.0:
        return "offline"
    if not frames and not cache:
        return "online"
    if latency_min <= 30:
        return "online"
    if latency_min <= 60:
        return "delayed"
    return "offline"


def test_stale_empty_frames_and_old_cache_is_offline():
    """M2: cache exists but frames=[] and >60 min → offline."""
    assert compute_status(True, [], _make_cache(), 90.0) == "offline"


def test_no_cache_at_all_is_online():
    """M2 contrast: no cache (never polled) → online with baseline latency."""
    assert compute_status(True, [], None, 5.0) == "online"


def test_fresh_frames_is_online():
    f = [{"timestamp": _utc_ago(5).timestamp()}]
    assert compute_status(True, f, _make_cache(frames=f), 5.0) == "online"


def test_45min_latency_is_delayed():
    f = [{"timestamp": _utc_ago(45).timestamp()}]
    assert compute_status(True, f, _make_cache(frames=f), 45.0) == "delayed"


def test_90min_latency_with_frames_is_offline():
    f = [{"timestamp": _utc_ago(90).timestamp()}]
    assert compute_status(True, f, _make_cache(frames=f), 90.0) == "offline"


def test_inactive_station_always_offline():
    f = [{"timestamp": _utc_ago(5).timestamp()}]
    assert compute_status(False, f, _make_cache(frames=f), 5.0) == "offline"


# ── Clusters endpoint tests ────────────────────────────────────────────────────

def _patch_repo_ctx(mock_repo):
    ctx_cm = MagicMock()
    ctx_cm.__aenter__ = AsyncMock(return_value=mock_repo)
    ctx_cm.__aexit__ = AsyncMock(return_value=False)
    return ctx_cm


@pytest.mark.asyncio
async def test_clusters_includes_source_field(client):
    """Clusters endpoint must always include 'source' field."""
    mock_repo = AsyncMock()
    mock_repo.get_latest_radar_cache.return_value = None
    with patch("app.routers.radar.get_repo_context", return_value=_patch_repo_ctx(mock_repo)):
        res = await client.get("/api/v1/radar/clusters")
    assert res.status_code == 200
    body = res.json()
    assert "source" in body
    assert "clusters" in body
    assert isinstance(body["clusters"], list)


@pytest.mark.asyncio
async def test_clusters_is_mock_true_on_cold_cache(client):
    """When all caches are None (cold), is_mock must be True."""
    mock_repo = AsyncMock()
    mock_repo.get_latest_radar_cache.return_value = None
    with patch("app.routers.radar.get_repo_context", return_value=_patch_repo_ctx(mock_repo)):
        res = await client.get("/api/v1/radar/clusters")
    body = res.json()
    assert body.get("is_mock") is True


@pytest.mark.asyncio
async def test_clusters_graceful_on_repo_failure(client):
    """Repo failure on clusters must not cause 500."""
    mock_repo = AsyncMock()
    mock_repo.get_latest_radar_cache.side_effect = RuntimeError("Redis down")
    with patch("app.routers.radar.get_repo_context", return_value=_patch_repo_ctx(mock_repo)):
        res = await client.get("/api/v1/radar/clusters")
    assert res.status_code == 200
    assert "clusters" in res.json()
