"""
Tests for GCPBillingService (Issue #211).

Tests cover: schema validation, mock fallback behavior,
service aggregation logic, and API error fallback.
Uses strict TDD: RED → GREEN → REFACTOR.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ─── Task 5: GCPBillingService ───────────────────────────────────────────────

def test_gcp_cost_breakdown_dataclass_exists():
    """GCPCostBreakdown dataclass ต้อง importable และมี fields ครบ"""
    from app.services.gcp_billing import GCPCostBreakdown

    breakdown = GCPCostBreakdown(
        cloud_run_thb=367.50,
        cloud_storage_thb=80.50,
        egress_thb=28.00,
        other_thb=35.00,
        total_thb=511.00,
        period_start="2026-07-01",
        period_end="2026-07-31",
        currency="THB",
        is_mock=False,
    )
    assert breakdown.total_thb == pytest.approx(511.00)
    assert breakdown.is_mock is False
    assert breakdown.currency == "THB"


def test_gcp_billing_service_returns_mock_when_no_env():
    """ถ้าไม่มี GCP_PROJECT_ID ใน env ต้อง return mock data (is_mock=True)"""
    with patch.dict("os.environ", {}, clear=True):
        from app.services.gcp_billing import GCPBillingService

        svc = GCPBillingService()
        result = svc.get_mock_breakdown()

    assert result.is_mock is True
    assert result.total_thb > 0
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

    assert result["cloud_run_thb"] == pytest.approx(12.5)
    assert result["cloud_storage_thb"] == pytest.approx(3.0)
    assert result["egress_thb"] == pytest.approx(0.5)
    assert result["other_thb"] == pytest.approx(1.0)


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
    assert result.total_thb > 0


def test_gcp_billing_requires_real_data_when_requested():
    """require_real_data=True ต้อง fail แทนการ fallback เป็น mock."""
    with patch.dict("os.environ", {}, clear=True):
        from app.services.gcp_billing import GCPBillingService

        svc = GCPBillingService()

        with pytest.raises(RuntimeError, match="GCP billing config is missing"):
            svc.get_current_month_costs(require_real_data=True)


@pytest.mark.asyncio
async def test_gcp_billing_local_false_can_defer_to_neon_true():
    """local env=false should defer to Neon override instead of forcing mock."""
    with patch.dict("os.environ", {
        "ENVIRONMENT": "development",
        "FORCE_GCP_REAL_DATA": "false",
        "DATABASE_URL": "postgresql://example",
    }):
        from app.services.gcp_billing import GCPBillingService

        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = "true"
        session.execute.return_value = execute_result

        session_cm = AsyncMock()
        session_cm.__aenter__.return_value = session
        session_cm.__aexit__.return_value = False

        with patch("app.services.gcp_billing.AsyncSessionLocal", return_value=session_cm):
            svc = GCPBillingService()
            resolved = await svc.resolve_force_real_data()

    assert resolved is True


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
            cloud_run_thb=294.0,
            cloud_storage_thb=42.0,
            egress_thb=21.0,
            other_thb=28.0,
            total_thb=385.0,
            period_start="2026-07-01",
            period_end="2026-07-24",
            currency="THB",
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
    assert "cloud_run_thb" in data
    assert "total_thb" in data
    assert "period_start" in data
    assert data["currency"] == "THB"
    assert data["is_mock"] is True
    assert data["total_thb"] == pytest.approx(385.0)


def test_gcp_costs_endpoint_requires_auth():
    """GET /api/v1/metrics/gcp-costs ต้องการ x-cron-secret ที่ถูกต้อง"""
    import os
    from fastapi.testclient import TestClient
    from app.main import app

    with patch.dict(os.environ, {"CRON_SECRET": "real_secret"}):
        client = TestClient(app)
        response = client.get("/api/v1/metrics/gcp-costs")

    assert response.status_code == 401


def test_gcp_costs_endpoint_supports_period_param(mocker):
    """GET /api/v1/metrics/gcp-costs?period=30d ต้องส่ง period ไปให้ GCPBillingService"""
    import os
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.gcp_billing import GCPCostBreakdown

    mocker.patch.dict(os.environ, {"CRON_SECRET": "test_secret_xyz"})
    mock_service = mocker.patch(
        "app.routers.metrics.GCPBillingService.get_current_month_costs",
        return_value=GCPCostBreakdown(
            cloud_run_thb=300.0,
            period_start="2026-07-01",
            period_end="2026-08-01",
            currency="THB",
            is_mock=True,
        ),
    )

    client = TestClient(app)
    response = client.get(
        "/api/v1/metrics/gcp-costs?period=30d",
        headers={"x-cron-secret": "test_secret_xyz"},
    )
    assert response.status_code == 200
    mock_service.assert_called_once_with(period="30d")


def test_gcp_billing_passes_thb_values_from_bigquery_directly():
    """BigQuery Billing Export already returns costs in THB (billing account currency).
    No conversion should happen — values must pass through as-is."""
    import os
    from app.services.gcp_billing import GCPBillingService

    with patch.dict(os.environ, {
        "GCP_PROJECT_ID": "test-proj",
        "GCP_BILLING_BIGQUERY_DATASET": "test-dataset",
    }):
        svc = GCPBillingService()
        mock_raw = [
            {
                "project_id": "test-proj",
                "service_description": "Cloud Run",
                "sku_description": "CPU Allocation Time",
                "cost": 350.0,
            },  # 350 THB direct from BQ
            {
                "project_id": "test-proj",
                "service_description": "Cloud Storage",
                "sku_description": "Standard Storage",
                "cost": 38.5,
            },  # 38.5 THB direct from BQ
        ]
        with patch.object(svc, "_query_billing_api", return_value=mock_raw):
            res = svc.get_current_month_costs(require_real_data=True)

    assert res.is_mock is False
    # Values must NOT be multiplied — BigQuery already returns THB
    assert res.cloud_run_thb == pytest.approx(350.0)
    assert res.cloud_storage_thb == pytest.approx(38.5)
    assert res.total_thb == pytest.approx(388.5)
    assert res.service_details["cloud_run_thb"][0] == {
        "project_id": "test-proj",
        "service": "Cloud Run",
        "sku": "CPU Allocation Time",
        "cost_thb": 350.0,
    }
    assert res.service_details["cloud_storage_thb"][0]["sku"] == "Standard Storage"
    # USD properties are informational only (THB / 35)
    assert res.total_usd == pytest.approx(388.5 / 35.0, rel=1e-3)


def test_gcp_billing_requires_real_data_on_api_error():
    """require_real_data=True ต้อง fail เมื่อ BigQuery query error เกิดขึ้น."""
    with patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-proj",
        "GCP_BILLING_BIGQUERY_DATASET": "test-dataset",
    }):
        from app.services.gcp_billing import GCPBillingService

        svc = GCPBillingService()
        with patch.object(svc, "_query_billing_api", side_effect=Exception("API Error")):
            with pytest.raises(RuntimeError, match="Failed to fetch real GCP billing data"):
                svc.get_current_month_costs(require_real_data=True)
