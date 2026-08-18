"""
test_radar_security.py
-----------------------
API security tests for the public radar endpoints.
Tests: unauthenticated access, input validation, SQL injection resilience,
large payload handling, and malformed input graceful handling.

NOTE: These endpoints are currently public (no auth required). Tests document
      this as an observed state. A separate issue should enforce auth.
"""
import os
os.environ["STORAGE_BACKEND"] = "sqlite"

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.routers.radar import router as radar_router

app = FastAPI()
app.include_router(radar_router)


@pytest_asyncio.fixture
async def client():
    """Unauthenticated HTTP client — no auth headers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _cold_repo():
    mock_repo = AsyncMock()
    mock_repo.get_latest_radar_cache.return_value = None
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_repo)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ── Unauthenticated access (document current posture) ─────────────────────────

@pytest.mark.asyncio
async def test_stations_accessible_without_auth(client):
    """
    SECURITY POSTURE (documented): /api/v1/radar/stations is publicly accessible.
    This test records the current state; auth enforcement is a future ticket.
    """
    with patch("app.routers.radar.AsyncSessionLocal", side_effect=RuntimeError("DB down")):
        res = await client.get("/api/v1/radar/stations")
    # Must return 200 partial OR valid stations — not 401/403
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_clusters_accessible_without_auth(client):
    """SECURITY POSTURE: /api/v1/radar/clusters is publicly accessible."""
    with patch("app.routers.radar.get_repo_context", return_value=_cold_repo()):
        res = await client.get("/api/v1/radar/clusters")
    assert res.status_code == 200


# ── SQL Injection resilience ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stations_sql_injection_in_path_returns_404_not_500(client):
    """SQL injection attempt in URL path should be rejected by router (404), not 500."""
    res = await client.get("/api/v1/radar/stations'; DROP TABLE users; --")
    assert res.status_code in (404, 422), \
        f"SQL injection in path should be 404/422, got {res.status_code}"


@pytest.mark.asyncio
async def test_clusters_sql_injection_in_query_params(client):
    """SQL injection in query param must not cause 500."""
    with patch("app.routers.radar.get_repo_context", return_value=_cold_repo()):
        res = await client.get("/api/v1/radar/clusters?code='; DROP TABLE radar_cache; --")
    assert res.status_code in (200, 422), \
        f"SQL injection in query param should be 200/422, got {res.status_code}"
    if res.status_code == 200:
        body = res.json()
        assert "clusters" in body


# ── Large payload protection ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stations_rejects_huge_body(client):
    """POST with enormous body to GET endpoint — should be 405 (method not allowed)."""
    huge_payload = {"data": "x" * 100_000}
    res = await client.post("/api/v1/radar/stations", json=huge_payload)
    assert res.status_code == 405, \
        f"POST to GET endpoint should be 405 Method Not Allowed, got {res.status_code}"


@pytest.mark.asyncio
async def test_clusters_rejects_huge_body(client):
    """POST with enormous body to GET endpoint — should be 405."""
    huge_payload = {"data": "y" * 100_000}
    res = await client.post("/api/v1/radar/clusters", json=huge_payload)
    assert res.status_code == 405


# ── Error response information disclosure ─────────────────────────────────────

@pytest.mark.asyncio
async def test_stations_error_does_not_leak_stack_trace(client):
    """
    SECURITY: error responses must not expose internal stack traces or
    unhandled exception details to the client.
    """
    with patch("app.routers.radar.AsyncSessionLocal", side_effect=RuntimeError("secret_internal_host:5432")):
        res = await client.get("/api/v1/radar/stations")

    assert res.status_code == 200  # partial response, not 500
    body = res.json()
    body_str = str(body)
    # Internal host details should NOT be in the error message exposed to client
    assert "secret_internal_host" not in body_str, \
        "Internal error details must not be leaked in API response"


@pytest.mark.asyncio
async def test_stations_error_message_is_generic(client):
    """Error message in partial response should be generic, not expose internals."""
    with patch("app.routers.radar.AsyncSessionLocal", side_effect=RuntimeError("DB down")):
        res = await client.get("/api/v1/radar/stations")
    body = res.json()
    # error message should be present and generic
    assert "error" in body
    error_msg = body["error"].lower()
    assert len(error_msg) < 200, "Error message should be short and generic"


# ── Response headers security ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stations_response_content_type_is_json(client):
    """Endpoints must return application/json, not HTML (guards against XSS via content-type sniffing)."""
    with patch("app.routers.radar.AsyncSessionLocal", side_effect=RuntimeError("DB down")):
        res = await client.get("/api/v1/radar/stations")
    ct = res.headers.get("content-type", "")
    assert "application/json" in ct, f"Content-Type must be JSON, got: {ct}"


@pytest.mark.asyncio
async def test_clusters_response_content_type_is_json(client):
    """Clusters endpoint must return JSON content-type."""
    with patch("app.routers.radar.get_repo_context", return_value=_cold_repo()):
        res = await client.get("/api/v1/radar/clusters")
    ct = res.headers.get("content-type", "")
    assert "application/json" in ct
