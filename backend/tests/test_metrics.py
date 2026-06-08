"""
Issue #62: Export Google Cloud Run Dashboard Metrics for Analysis
TDD — RED Phase: Failing tests written before production code.
"""
import pytest
import csv
import io
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
import os


# ===========================
# Unit Tests: MetricsService
# ===========================

class TestMetricsService:
    """Tests for backend/app/services/metrics_service.py"""

    @pytest.mark.asyncio
    async def test_record_cron_run_stores_entry(self):
        """MetricsService.record_cron_run() ต้องบันทึก entry ลง repository"""
        from app.services.metrics_service import MetricsService

        mock_repo = AsyncMock()
        service = MetricsService(repo=mock_repo)

        await service.record_cron_run(
            routine_name="check_rain",
            duration_s=3.14,
            alerts_sent=2,
            locations_checked=5,
            errors=0,
        )

        mock_repo.record_cron_run.assert_called_once()
        call_kwargs = mock_repo.record_cron_run.call_args[1]
        assert call_kwargs["routine_name"] == "check_rain"
        assert call_kwargs["duration_s"] == pytest.approx(3.14)
        assert call_kwargs["alerts_sent"] == 2
        assert call_kwargs["locations_checked"] == 5
        assert call_kwargs["errors"] == 0

    @pytest.mark.asyncio
    async def test_record_cron_run_includes_timestamp(self):
        """record_cron_run() ต้อง pass run_at timestamp เป็น UTC datetime"""
        from app.services.metrics_service import MetricsService

        mock_repo = AsyncMock()
        service = MetricsService(repo=mock_repo)

        before = datetime.now(timezone.utc)
        await service.record_cron_run(
            routine_name="fetch_tmd_radar",
            duration_s=1.5,
            alerts_sent=0,
            locations_checked=0,
            errors=0,
        )
        after = datetime.now(timezone.utc)

        call_kwargs = mock_repo.record_cron_run.call_args[1]
        run_at = call_kwargs["run_at"]
        assert isinstance(run_at, datetime)
        assert before <= run_at <= after

    @pytest.mark.asyncio
    async def test_get_metrics_summary_returns_dict(self):
        """get_metrics_summary() ต้องคืน dict ที่มี key ครบถ้วน"""
        from app.services.metrics_service import MetricsService

        mock_repo = AsyncMock()
        mock_repo.get_cron_metrics.return_value = [
            {
                "routine_name": "check_rain",
                "run_at": datetime(2026, 6, 8, 3, 0, tzinfo=timezone.utc),
                "duration_s": 4.2,
                "alerts_sent": 3,
                "locations_checked": 7,
                "errors": 0,
            },
            {
                "routine_name": "check_rain",
                "run_at": datetime(2026, 6, 8, 3, 5, tzinfo=timezone.utc),
                "duration_s": 3.8,
                "alerts_sent": 0,
                "locations_checked": 7,
                "errors": 1,
            },
        ]

        service = MetricsService(repo=mock_repo)
        result = await service.get_metrics_summary(days=7)

        assert "routines" in result
        assert "generated_at" in result
        assert "period_days" in result
        assert result["period_days"] == 7

    @pytest.mark.asyncio
    async def test_get_metrics_summary_aggregates_correctly(self):
        """get_metrics_summary() ต้อง aggregate stats ต่อ routine ได้ถูกต้อง"""
        from app.services.metrics_service import MetricsService

        mock_repo = AsyncMock()
        mock_repo.get_cron_metrics.return_value = [
            {
                "routine_name": "check_rain",
                "run_at": datetime(2026, 6, 8, 3, 0, tzinfo=timezone.utc),
                "duration_s": 4.0,
                "alerts_sent": 2,
                "locations_checked": 5,
                "errors": 0,
            },
            {
                "routine_name": "check_rain",
                "run_at": datetime(2026, 6, 8, 3, 5, tzinfo=timezone.utc),
                "duration_s": 6.0,
                "alerts_sent": 1,
                "locations_checked": 5,
                "errors": 1,
            },
        ]

        service = MetricsService(repo=mock_repo)
        result = await service.get_metrics_summary(days=7)

        rain_stats = result["routines"]["check_rain"]
        assert rain_stats["total_runs"] == 2
        assert rain_stats["total_alerts_sent"] == 3
        assert rain_stats["total_errors"] == 1
        assert rain_stats["avg_duration_s"] == pytest.approx(5.0)
        assert rain_stats["min_duration_s"] == pytest.approx(4.0)
        assert rain_stats["max_duration_s"] == pytest.approx(6.0)

    @pytest.mark.asyncio
    async def test_get_metrics_summary_empty_returns_empty_routines(self):
        """get_metrics_summary() เมื่อไม่มีข้อมูลต้องคืน routines เป็น {} ไม่ใช่ error"""
        from app.services.metrics_service import MetricsService

        mock_repo = AsyncMock()
        mock_repo.get_cron_metrics.return_value = []

        service = MetricsService(repo=mock_repo)
        result = await service.get_metrics_summary(days=7)

        assert result["routines"] == {}
        assert result["period_days"] == 7


# ===========================
# Unit Tests: Repository
# ===========================

class TestRepositoryMetricsMethods:
    """Tests for record_cron_run / get_cron_metrics ใน repository"""

    @pytest.mark.asyncio
    async def test_base_repository_has_record_cron_run(self):
        """LocationRepository ต้องมี abstract method record_cron_run"""
        from app.repositories.base import LocationRepository
        import inspect

        abstract_methods = LocationRepository.__abstractmethods__
        assert "record_cron_run" in abstract_methods

    @pytest.mark.asyncio
    async def test_base_repository_has_get_cron_metrics(self):
        """LocationRepository ต้องมี abstract method get_cron_metrics"""
        from app.repositories.base import LocationRepository

        abstract_methods = LocationRepository.__abstractmethods__
        assert "get_cron_metrics" in abstract_methods


# ===========================
# Integration Tests: API Endpoint
# ===========================

class TestMetricsExportEndpoint:
    """Tests for GET /api/v1/metrics/export"""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        os.environ["CRON_SECRET"] = "test_secret_123"
        from app.main import app
        self.client = TestClient(app)
        self.secret = "test_secret_123"

    def test_metrics_export_unauthorized_no_server_secret(self):
        """ถ้าไม่ได้ set CRON_SECRET ที่ฝั่ง server ต้อง reject เสมอ"""
        if "CRON_SECRET" in os.environ:
            del os.environ["CRON_SECRET"]
        response = self.client.get(
            "/api/v1/metrics/export",
            headers={"X-Cron-Secret": "test_secret_123"}
        )
        assert response.status_code == 401

    def test_metrics_export_unauthorized_no_header(self):
        """ไม่มี header → ต้องได้ 401"""
        response = self.client.get("/api/v1/metrics/export")
        assert response.status_code == 401

    def test_metrics_export_unauthorized_wrong_secret(self):
        """header ผิด → ต้องได้ 401"""
        response = self.client.get(
            "/api/v1/metrics/export",
            headers={"X-Cron-Secret": "wrong_secret_xyz"}
        )
        assert response.status_code == 401

    @patch("app.routers.metrics.get_repo_context")
    def test_metrics_export_json_format(self, mock_get_repo_context):
        """GET /api/v1/metrics/export → ต้อง return JSON ที่มี key ครบ"""
        from contextlib import asynccontextmanager

        mock_repo = AsyncMock()
        mock_repo.get_cron_metrics.return_value = []

        @asynccontextmanager
        async def mock_context():
            yield mock_repo

        mock_get_repo_context.side_effect = mock_context

        response = self.client.get(
            "/api/v1/metrics/export",
            headers={"X-Cron-Secret": self.secret}
        )
        assert response.status_code == 200
        data = response.json()
        assert "routines" in data
        assert "generated_at" in data
        assert "period_days" in data

    @patch("app.routers.metrics.get_repo_context")
    def test_metrics_export_csv_format(self, mock_get_repo_context):
        """GET /api/v1/metrics/export?format=csv → ต้อง return CSV text/csv"""
        from contextlib import asynccontextmanager

        mock_repo = AsyncMock()
        mock_repo.get_cron_metrics.return_value = [
            {
                "routine_name": "check_rain",
                "run_at": datetime(2026, 6, 8, 3, 0, tzinfo=timezone.utc),
                "duration_s": 4.2,
                "alerts_sent": 3,
                "locations_checked": 7,
                "errors": 0,
            }
        ]

        @asynccontextmanager
        async def mock_context():
            yield mock_repo

        mock_get_repo_context.side_effect = mock_context

        response = self.client.get(
            "/api/v1/metrics/export?format=csv",
            headers={"X-Cron-Secret": self.secret}
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

        # Parse CSV และตรวจว่ามี header columns ถูกต้อง
        content = response.text
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) >= 1
        assert "routine_name" in reader.fieldnames
        assert "duration_s" in reader.fieldnames
        assert "alerts_sent" in reader.fieldnames

    @patch("app.routers.metrics.get_repo_context")
    def test_metrics_export_filter_by_routine(self, mock_get_repo_context):
        """GET /api/v1/metrics/export?routine=check_rain → ต้องกรองเฉพาะ routine ที่ระบุ"""
        from contextlib import asynccontextmanager

        mock_repo = AsyncMock()
        mock_repo.get_cron_metrics.return_value = []

        @asynccontextmanager
        async def mock_context():
            yield mock_repo

        mock_get_repo_context.side_effect = mock_context

        response = self.client.get(
            "/api/v1/metrics/export?routine=check_rain",
            headers={"X-Cron-Secret": self.secret}
        )
        assert response.status_code == 200

        # in JSON format, filtering happens in the router after fetching all metrics
        data = response.json()
        assert "routines" in data

    @patch("app.routers.metrics.get_repo_context")
    def test_metrics_export_custom_days(self, mock_get_repo_context):
        """GET /api/v1/metrics/export?days=30 → ต้อง return period_days=30"""
        from contextlib import asynccontextmanager

        mock_repo = AsyncMock()
        mock_repo.get_cron_metrics.return_value = []

        @asynccontextmanager
        async def mock_context():
            yield mock_repo

        mock_get_repo_context.side_effect = mock_context

        response = self.client.get(
            "/api/v1/metrics/export?days=30",
            headers={"X-Cron-Secret": self.secret}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 30


# ===========================
# Integration Tests: Scheduler Timing
# ===========================

class TestSchedulerMetricsIntegration:
    """ตรวจว่า scheduler_tasks บันทึก metrics หลัง routine เสร็จ"""

    @pytest.mark.asyncio
    @patch("app.scheduler_tasks.MetricsService")
    @patch("app.scheduler_tasks.WeatherManager")
    @patch("app.scheduler_tasks.send_telegram_message", new_callable=AsyncMock)
    @patch("app.scheduler_tasks.fetch_tmd_radar_routine", new_callable=AsyncMock)
    @patch("app.scheduler_tasks.get_repo_context")
    async def test_check_rain_records_metrics_after_run(
        self,
        mock_get_repo_context,
        mock_fetch_routine,
        mock_send_msg,
        mock_weather_mgr_cls,
        mock_metrics_svc_cls,
    ):
        """check_rain_and_alert() ต้อง call MetricsService.record_cron_run() หลัง run เสร็จ"""
        from contextlib import asynccontextmanager
        from app.scheduler_tasks import check_rain_and_alert

        mock_repo = AsyncMock()

        @asynccontextmanager
        async def mock_context():
            yield mock_repo

        mock_get_repo_context.side_effect = mock_context
        
        # Provide one active location so it doesn't return early
        from app.models import UserLocation
        loc1 = UserLocation(
            chat_id=123,
            name="home",
            latitude=13.0,
            longitude=100.0,
            last_alerted_at=None
        )
        mock_repo.get_active_locations.return_value = [loc1]

        mock_wm_instance = mock_weather_mgr_cls.return_value
        base_time = datetime.now(timezone.utc)
        mock_wm_instance.predict_rain = AsyncMock(return_value={
            "predictions": [
                {"time": base_time.isoformat(), "rain": 0.1}
            ],
            "max_rain": 0.1
        })

        mock_metrics_instance = AsyncMock()
        mock_metrics_svc_cls.return_value = mock_metrics_instance

        await check_rain_and_alert()

        mock_metrics_instance.record_cron_run.assert_called_once()
        call_kwargs = mock_metrics_instance.record_cron_run.call_args[1]
        assert call_kwargs["routine_name"] == "check_rain"
        assert "duration_s" in call_kwargs
        assert call_kwargs["duration_s"] >= 0
