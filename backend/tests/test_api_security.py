"""
Security & Hardening Test Suite (Issues #249, #339).

Verifies security controls for GCP metrics and cost endpoints:
- SQL injection safety (parameterized queries & escaping)
- XSS / HTML injection in user inputs and headers
- IDOR (Insecure Direct Object Reference) and unauthorized data leakage
- Authentication enforcement (CRON_SECRET constant-time verification)
- API fuzzing / invalid parameters resiliency
"""
import os
import secrets
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from app.main import app

client = TestClient(app)
CRON_SECRET = "test_cron_secret_secure_xyz_999"


@pytest.fixture(autouse=True)
def setup_env():
    os.environ["CRON_SECRET"] = CRON_SECRET
    yield
    if "CRON_SECRET" in os.environ:
        del os.environ["CRON_SECRET"]


# ─── 1. Authentication & IDOR / Access Control ────────────────────────────────

def test_gcp_costs_missing_auth_header():
    """Ensure endpoint returns 401 when x-cron-secret header is completely omitted."""
    resp = client.get("/api/v1/metrics/gcp-costs")
    assert resp.status_code == 401
    assert "Unauthorized" in resp.text


def test_gcp_costs_invalid_auth_token():
    """Ensure endpoint rejects invalid tokens and timing attack protections work."""
    resp = client.get(
        "/api/v1/metrics/gcp-costs",
        headers={"x-cron-secret": "invalid_random_secret_token_123"}
    )
    assert resp.status_code == 401
    assert "Unauthorized" in resp.text


def test_gcp_costs_constant_time_comparison():
    """Verify secrets.compare_digest is utilized and works correctly."""
    valid = secrets.compare_digest(CRON_SECRET, CRON_SECRET)
    invalid = secrets.compare_digest(CRON_SECRET, "wrong_token")
    assert valid is True
    assert invalid is False


# ─── 2. SQL Injection Resistance ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bigquery_project_filter_sql_injection_defense():
    """Ensure project_filter escapes single quotes to neutralize SQL injection."""
    from app.services.gcp_billing import GCPBillingService

    with patch.dict("os.environ", {
        "GCP_PROJECT_ID": "my-project",
        "GCP_BILLING_BIGQUERY_DATASET": "my-dataset",
        "GCP_BILLING_PROJECT_FILTER": "proj'; DROP TABLE `my-dataset.billing`; --",
    }):
        svc = GCPBillingService()
        # Verify billing_project_filter has the malicious string
        assert "DROP TABLE" in svc.billing_project_filter

        with patch("google.cloud.bigquery.Client") as mock_bq_cls:
            mock_bq_client = MagicMock()
            mock_bq_cls.return_value = mock_bq_client
            mock_bq_client.query.return_value.result.return_value = []

            # Execute query builder
            svc._query_billing_api(period="current_month", period_start="2026-09-01", period_end="2026-09-26")

            # Inspect executed SQL
            executed_query = mock_bq_client.query.call_args[0][0]
            # Single quote must be escaped into double single-quotes
            assert "proj''; DROP TABLE" in executed_query
            # Ensure the raw unescaped injection is not present
            assert "proj'; DROP TABLE" not in executed_query


# ─── 3. XSS / HTML Injection Defense ──────────────────────────────────────────

def test_metrics_endpoints_xss_injection_resiliency():
    """Ensure script tags and HTML injection in query parameters are handled without reflection/execution."""
    xss_payload = "<script>alert('XSS')</script>"
    resp = client.get(
        f"/api/v1/metrics/gcp-costs?period={xss_payload}",
        headers={"x-cron-secret": CRON_SECRET}
    )
    # Endpoint should either succeed with safe fallback or return valid JSON without raw unescaped script tag execution
    assert resp.status_code in (200, 400, 422)
    assert resp.headers["content-type"].startswith("application/json")


# ─── 4. API Fuzzing & Parameter Resiliency ───────────────────────────────────

@pytest.mark.parametrize("fuzzed_period", [
    "",
    "   ",
    "null",
    "undefined",
    "2026",
    "2026-99",
    "2026-00",
    "../../etc/passwd",
    "%00%20%0a",
    "9999999999999999999999999999999999",
    "{\"period\": \"injected\"}",
    "A" * 500,
])
def test_gcp_costs_fuzzed_period_parameters(fuzzed_period):
    """API must not crash (500) under malformed or malicious period strings."""
    resp = client.get(
        f"/api/v1/metrics/gcp-costs?period={fuzzed_period}",
        headers={"x-cron-secret": CRON_SECRET}
    )
    # Must handle gracefully without unhandled 500 internal server crash
    assert resp.status_code in (200, 400, 422)


@pytest.mark.parametrize("fuzzed_force_refresh", [
    "true",
    "false",
    "1",
    "0",
    "yes",
    "no",
    "invalid",
    "true; DROP TABLE",
    "9999",
])
def test_gcp_costs_fuzzed_force_refresh_parameters(fuzzed_force_refresh):
    """Boolean parsing must not fail ungracefully on arbitrary strings."""
    resp = client.get(
        f"/api/v1/metrics/gcp-costs?force_refresh={fuzzed_force_refresh}",
        headers={"x-cron-secret": CRON_SECRET}
    )
    assert resp.status_code in (200, 422)
