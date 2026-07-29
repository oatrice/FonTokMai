"""
Tests for GCPBillingService (Issue #211).

Tests cover: schema validation, mock fallback behavior,
service aggregation logic, and API error fallback.
Uses strict TDD: RED → GREEN → REFACTOR.
"""
import pytest
from unittest.mock import patch


# ─── Task 5: GCPBillingService ───────────────────────────────────────────────

def test_gcp_cost_breakdown_dataclass_exists():
    """GCPCostBreakdown dataclass ต้อง importable และมี fields ครบ"""
    from app.services.gcp_billing import GCPCostBreakdown

    breakdown = GCPCostBreakdown(
        cloud_run_usd=10.50,
        cloud_storage_usd=2.30,
        egress_usd=0.80,
        other_usd=1.00,
        total_usd=14.60,
        period_start="2026-07-01",
        period_end="2026-07-31",
        currency="USD",
        is_mock=False,
    )
    assert breakdown.total_usd == pytest.approx(14.60)
    assert breakdown.is_mock is False
    assert breakdown.currency == "USD"


def test_gcp_billing_service_returns_mock_when_no_env():
    """ถ้าไม่มี GCP_PROJECT_ID ใน env ต้อง return mock data (is_mock=True)"""
    with patch.dict("os.environ", {}, clear=True):
        from app.services.gcp_billing import GCPBillingService

        svc = GCPBillingService()
        result = svc.get_mock_breakdown()

    assert result.is_mock is True
    assert result.total_usd > 0
    assert result.period_start != ""


def test_gcp_billing_aggregates_by_service():
    """_aggregate_by_service() ต้องรวมค่าใช้จ่ายตาม service name ถูกต้อง"""
    from app.services.gcp_billing import GCPBillingService

    svc = GCPBillingService()
    raw = [
        {"service_description": "Cloud Run", "cost": 10.5},
        {"service_description": "Cloud Run", "cost": 2.0},
        {"service_description": "Cloud Storage", "cost": 3.0},
        {"service_description": "Networking", "cost": 0.5},
        {"service_description": "Unknown Service", "cost": 1.0},
    ]
    result = svc._aggregate_by_service(raw)

    assert result["cloud_run_usd"] == pytest.approx(12.5)
    assert result["cloud_storage_usd"] == pytest.approx(3.0)
    assert result["egress_usd"] == pytest.approx(0.5)
    assert result["other_usd"] == pytest.approx(1.0)


def test_gcp_billing_fallback_on_api_error():
    """ถ้า _query_billing_api() throw exception ต้อง fallback กลับมาที่ mock"""
    with patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "GCP_BILLING_BIGQUERY_DATASET": "test-project.billing",
        "FORCE_GCP_REAL_DATA": "false",
    }):
        from app.services.gcp_billing import GCPBillingService

        with patch.object(GCPBillingService, "_query_billing_api", side_effect=Exception("API Error")):
            svc = GCPBillingService()
            result = svc.get_current_month_costs()

    assert result.is_mock is True


def test_gcp_billing_uses_mock_when_no_config():
    """get_current_month_costs() ต้อง return mock เมื่อ env ไม่ครบ"""
    with patch.dict("os.environ", {}, clear=True):
        from app.services.gcp_billing import GCPBillingService

        svc = GCPBillingService()
        result = svc.get_current_month_costs()

    assert result.is_mock is True
    assert result.total_usd > 0


# ─── Task 6: GET /api/v1/metrics/gcp-costs ───────────────────────────────────

def test_gcp_costs_endpoint_returns_breakdown(mocker):
    """GET /api/v1/metrics/gcp-costs ต้อง return breakdown ที่ถูก schema"""
    import os
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.gcp_billing import GCPCostBreakdown

    mocker.patch.dict(os.environ, {"CRON_SECRET": "test_secret_xyz"})
    mocker.patch(
        "app.routers.metrics.GCPBillingService.get_current_month_costs",
        return_value=GCPCostBreakdown(
            cloud_run_usd=8.4,
            cloud_storage_usd=1.2,
            egress_usd=0.6,
            other_usd=0.8,
            total_usd=11.0,
            period_start="2026-07-01",
            period_end="2026-07-24",
            is_mock=True,
        ),
    )

    client = TestClient(app)
    response = client.get(
        "/api/v1/metrics/gcp-costs",
        headers={"x-cron-secret": "test_secret_xyz"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "cloud_run_usd" in data
    assert "total_usd" in data
    assert "period_start" in data
    assert data["is_mock"] is True
    assert data["total_usd"] == pytest.approx(11.0)


def test_gcp_costs_endpoint_requires_auth():
    """GET /api/v1/metrics/gcp-costs ต้องการ x-cron-secret ที่ถูกต้อง"""
    import os
    from fastapi.testclient import TestClient
    from app.main import app

    with patch.dict(os.environ, {"CRON_SECRET": "real_secret"}):
        client = TestClient(app)
        response = client.get("/api/v1/metrics/gcp-costs")

    assert response.status_code == 401


def test_gcp_costs_endpoint_wrong_secret_rejected():
    """x-cron-secret ที่ผิดต้อง return 401"""
    import os
    from fastapi.testclient import TestClient
    from app.main import app

    with patch.dict(os.environ, {"CRON_SECRET": "real_secret"}):
        client = TestClient(app)
        response = client.get(
            "/api/v1/metrics/gcp-costs",
            headers={"x-cron-secret": "wrong_secret"},
        )

    assert response.status_code == 401
