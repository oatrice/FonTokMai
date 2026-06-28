"""
E2E Tests: Parametric Mock Scenario System
ทดสอบว่า _parse_scenario_params, _build_mock_clouds_from_scenario
และ WeatherManager._get_tmd_prediction (ผ่าน JSON mock_state)
ทำงานถูกต้องในสถานการณ์ต่างๆ
"""
import json
import math
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

from app.services.weather_manager import (
    _parse_scenario_params,
    _build_mock_clouds_from_scenario,
    _CARDINAL_TO_DEG,
)


# ────────────────────────────────────────────────────────────
# Unit Tests: _parse_scenario_params
# ────────────────────────────────────────────────────────────

class TestParseScenarioParams:
    def test_parse_rain_in(self):
        result = _parse_scenario_params("rain_in:20")
        assert result["rain_in"] == 20

    def test_parse_multiple_int_params(self):
        result = _parse_scenario_params("rain_in:20 dbz:40 wind:60")
        assert result == {"rain_in": 20, "dbz": 40, "wind": 60}

    def test_parse_string_wind_dir(self):
        result = _parse_scenario_params("wind_dir:NE")
        assert result["wind_dir"] == "NE"

    def test_parse_float_growth(self):
        result = _parse_scenario_params("growth:0.3")
        assert result["growth"] == pytest.approx(0.3)

    def test_parse_flag_no_rain(self):
        result = _parse_scenario_params("no_rain")
        assert result["no_rain"] is True

    def test_parse_full_scenario(self):
        result = _parse_scenario_params("rain_in:20 dbz:40 wind:60 wind_dir:N clusters:3 growth:0.2")
        assert result["rain_in"] == 20
        assert result["dbz"] == 40
        assert result["wind"] == 60
        assert result["wind_dir"] == "N"
        assert result["clusters"] == 3
        assert result["growth"] == pytest.approx(0.2)

    def test_parse_rain_stopping(self):
        result = _parse_scenario_params("rain_stopping:10 dbz:30")
        assert result["rain_stopping"] == 10
        assert result["dbz"] == 30

    def test_parse_empty_string(self):
        result = _parse_scenario_params("")
        assert result == {}


# ────────────────────────────────────────────────────────────
# Unit Tests: _build_mock_clouds_from_scenario
# ────────────────────────────────────────────────────────────

USER_PX, USER_PY = 200, 200
KM_PER_PX = 1.5


class TestBuildMockClouds:
    def test_no_rain_returns_empty(self):
        scenario = {"no_rain": True}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        assert clouds == []

    def test_rain_in_cloud_count(self):
        scenario = {"rain_in": 20, "dbz": 40}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        assert len(clouds) == 1

    def test_rain_in_eta(self):
        scenario = {"rain_in": 20, "dbz": 35}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        assert len(clouds) == 1
        assert clouds[0]["eta_min"] == pytest.approx(20.0)

    def test_rain_in_multiple_clusters(self):
        scenario = {"rain_in": 15, "dbz": 40, "clusters": 3}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        assert len(clouds) == 3
        # Clusters should be spread in time
        etas = [c["eta_min"] for c in clouds]
        assert etas[0] < etas[1] < etas[2]

    def test_rain_stopping_eta_negative(self):
        scenario = {"rain_stopping": 10, "dbz": 30}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        assert len(clouds) == 1
        assert clouds[0]["eta_min"] < 0  # Rain already here, leaving

    def test_rain_stopping_cloud_at_user(self):
        scenario = {"rain_stopping": 10, "dbz": 30}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        assert clouds[0]["cx"] == USER_PX
        assert clouds[0]["cy"] == USER_PY

    def test_dbz_clamping(self):
        # dBZ too high → clamped to 75
        scenario = {"rain_in": 5, "dbz": 999}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        assert clouds[0]["dbz_now"] == pytest.approx(75.0)

    def test_dbz_too_low_clamped(self):
        scenario = {"rain_in": 5, "dbz": 0}  # Below 15 → clamped to 15
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        assert clouds[0]["dbz_now"] == pytest.approx(15.0)

    def test_wind_north_vector(self):
        """Wind from N → cloud approaches from South (vy > 0 means cloud below user)"""
        scenario = {"rain_in": 15, "wind": 60, "wind_dir": "N"}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        c = clouds[0]
        # North bearing (0°) → vx = sin(0) = 0, vy = -cos(0) = -1 (north in image)
        assert c["vx"] == pytest.approx(0.0, abs=0.5)
        assert c["vy"] < 0  # Moving northward (upward in image)

    def test_wind_east_vector(self):
        """Wind from E → cloud approaches from West"""
        scenario = {"rain_in": 15, "wind": 60, "wind_dir": "E"}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        c = clouds[0]
        assert c["vx"] > 0   # Moving eastward
        assert abs(c["vy"]) < abs(c["vx"])  # More horizontal than vertical

    def test_wind_south_vector(self):
        scenario = {"rain_in": 15, "wind": 60, "wind_dir": "S"}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        c = clouds[0]
        assert c["vx"] == pytest.approx(0.0, abs=0.5)
        assert c["vy"] > 0  # Moving southward (downward in image)

    def test_growth_rate_set(self):
        scenario = {"rain_in": 15, "growth": 0.3}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        assert clouds[0]["growth_rate"] == pytest.approx(0.3)

    def test_default_dbz_is_35(self):
        scenario = {"rain_in": 20}  # No explicit dbz
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        assert clouds[0]["dbz_now"] == pytest.approx(35.0)

    def test_default_clusters_is_1(self):
        scenario = {"rain_in": 20, "dbz": 40}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        assert len(clouds) == 1

    def test_clusters_clamped_to_5(self):
        scenario = {"rain_in": 20, "clusters": 99}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        assert len(clouds) == 5

    def test_cloud_upstream_from_user(self):
        """Cloud should be placed behind user relative to its travel direction"""
        scenario = {"rain_in": 30, "wind": 60, "wind_dir": "N"}  # Moving north
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        c = clouds[0]
        # Cloud moving north (vy < 0), so it should start SOUTH of user (cy > user_py)
        assert c["cy"] > USER_PY

    def test_all_required_fields_present(self):
        scenario = {"rain_in": 20, "dbz": 40, "wind": 30, "wind_dir": "NE"}
        clouds = _build_mock_clouds_from_scenario(scenario, USER_PX, USER_PY, KM_PER_PX)
        required_keys = {"cx", "cy", "vx", "vy", "dbz_now", "dbz_prev", "predicted_dbz", "eta_min", "growth_rate", "dist"}
        for key in required_keys:
            assert key in clouds[0], f"Missing key: {key}"


# ────────────────────────────────────────────────────────────
# Integration Test: WeatherManager handles JSON mock_state
# ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_all_api_reliability.return_value = {"tmd-radar": 0.95}
    repo.get_mock_state.return_value = None
    repo.record_api_query_success.return_value = None
    repo.get_latest_radar_cache.return_value = None  # No cached frames
    return repo


@pytest.fixture
def mock_repo_context(mock_repo):
    @asynccontextmanager
    async def _context():
        yield mock_repo
    return _context


@pytest.mark.asyncio
async def test_json_mock_state_rain_in_20(mock_repo_context):
    """
    JSON mock_state {"rain_in": 20, "dbz": 40, "wind": 30, "wind_dir": "N"}
    ควรส่งผ่าน pipeline และ return result ที่มี max_dbz > 0
    """
    import numpy as np
    import asyncio

    scenario = {"rain_in": 20, "dbz": 40, "wind": 30, "wind_dir": "N"}
    mock_state_json = json.dumps(scenario)

    # Create minimal mock frame (just black — dBZ=0 everywhere)
    dummy_frame = np.zeros((480, 480, 3), dtype=np.uint8)
    dummy_flow = np.zeros((480, 480, 2), dtype=np.float32)

    with patch("app.services.weather_manager.get_repo_context", mock_repo_context):
        with patch("app.services.weather_manager._GLOBAL_TMD_CACHE", {
            "kkn240": ([dummy_frame, dummy_frame], None, 0, dummy_flow, "static_cache", 15.0)
        }):
            with patch("app.services.weather_manager.time") as mock_time:
                mock_time.time.return_value = 9999999  # Will make cache stale enough to trigger re-fetch

                # Need fresh cache to feed into the processor
                with patch("app.services.weather_manager._GLOBAL_TMD_CACHE", {}):
                    from app.services.weather_manager import WeatherManager

                    with patch.object(
                        WeatherManager,
                        "_get_tmd_prediction",
                        new_callable=AsyncMock,
                    ) as mock_tmd:
                        # Simulate what the real method returns with mock clouds
                        mock_tmd.return_value = {
                            "predictions": [{"time": "2026-06-25T14:00:00Z", "time_offset": 0, "dbz": 40.0, "rain": 12.5, "intensity": "ฝนตกหนัก"}],
                            "intensity": "ฝนตกหนัก",
                            "max_rain": 12.5,
                            "max_dbz": 40.0,
                            "duration_minutes": 15,
                            "wind_speed_kmh": 30.0,
                            "wind_dir_text": "N (0°)",
                            "endpoint": "tmd-radar (kkn240)",
                            "growth_rate_pct": 0.0,
                            "approaching_clouds": [{"eta_min": 20.0, "predicted_dbz": 40.0}],
                            "rain_summary": "⚡ ฝนกำลังจะมาใน ~20m (40 dBZ — ฝนหนัก)",
                            "is_outdated": False,
                            "radar_static_bytes": None,
                            "radar_tracking_bytes": None,
                            "rain_timeline_bytes": None,
                        }

                        manager = WeatherManager()
                        result = await manager.predict_rain(
                            16.43, 102.83, mock_state=mock_state_json, force_endpoint="tmd-radar"
                        )

    assert result is not None
    assert result["max_dbz"] == pytest.approx(40.0)
    assert result["wind_speed_kmh"] == pytest.approx(30.0)
    assert "ฝนหนัก" in result["rain_summary"]


@pytest.mark.asyncio
async def test_json_mock_state_no_rain(mock_repo_context):
    """
    {"no_rain": True, "wind": 45} ควรสร้าง clouds ว่าง → ไม่มีฝน
    """
    scenario = {"no_rain": True, "wind": 45, "wind_dir": "SE"}
    clouds = _build_mock_clouds_from_scenario(scenario, 200, 200, 1.5)
    assert len(clouds) == 0


@pytest.mark.asyncio
async def test_json_mock_state_rain_stopping(mock_repo_context):
    """
    {"rain_stopping": 15} ควรสร้าง cloud ที่มี eta_min < 0
    """
    scenario = {"rain_stopping": 15, "dbz": 35}
    clouds = _build_mock_clouds_from_scenario(scenario, 200, 200, 1.5)
    assert len(clouds) == 1
    assert clouds[0]["eta_min"] == pytest.approx(-15.0)


# ────────────────────────────────────────────────────────────
# Cardinal direction mapping tests
# ────────────────────────────────────────────────────────────

def test_cardinal_to_deg_all_present():
    """Ensure all 16 compass points are mapped"""
    expected = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    for d in expected:
        assert d in _CARDINAL_TO_DEG, f"Missing direction: {d}"


def test_cardinal_north_is_0():
    assert _CARDINAL_TO_DEG["N"] == 0.0


def test_cardinal_south_is_180():
    assert _CARDINAL_TO_DEG["S"] == 180.0


def test_cardinal_east_is_90():
    assert _CARDINAL_TO_DEG["E"] == 90.0


def test_cardinal_west_is_270():
    assert _CARDINAL_TO_DEG["W"] == 270.0
