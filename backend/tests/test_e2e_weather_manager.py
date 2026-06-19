"""
E2E Test: Weather Manager Fallback Chain
ทดสอบว่า WeatherManager.predict_rain() ทำงานถูกต้องใน 3 สถานการณ์:
1. Force specific endpoint: force_endpoint="tomorrow" ต้องไม่ crash และ parse ค่าได้ถูกต้อง
2. Auto-fallback: ถ้า endpoint หนึ่งพัง ให้ fallback ไปตัวถัดไปจาก reliability score
3. All-fail: ถ้าทุก API พัง ต้องคืน {"endpoint": "error"} ไม่ใช่ NameError หรือ KeyError
"""
import pytest
import respx
import httpx
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.weather_manager import WeatherManager


# ────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_repo():
    """Mock Firestore repo ให้ predict_rain ดึง reliability scores ได้"""
    repo = AsyncMock()
    repo.get_all_api_reliability.return_value = {
        "tomorrow": 0.9,
        "xweather": 0.85,
        "open-meteo": 0.6,
    }
    repo.get_mock_state.return_value = None
    repo.record_api_query_success.return_value = None
    return repo


@pytest.fixture
def mock_repo_context(mock_repo):
    @asynccontextmanager
    async def _context():
        yield mock_repo
    return _context


# ────────────────────────────────────────────────────────────
# 1. Forced endpoint: tomorrow.io
# ────────────────────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_force_tomorrow_endpoint_parse(mock_repo_context, monkeypatch):
    """
    ถ้าเรียก predict_rain(force_endpoint='tomorrow') มันต้อง:
    - เรียก tomorrow.io API
    - parse response ให้ถูกต้อง (max_rain, endpoint)
    - ไม่ crash
    """
    monkeypatch.setenv("TOMORROW_API_KEY", "mock-key")

    # Mock Tomorrow.io HTTP response
    tomorrow_payload = {
        "data": {
            "timelines": [
                {
                    "timestep": "1m",
                    "intervals": [
                        {
                            "startTime": "2026-06-19T10:00:00Z",
                            "values": {
                                "precipitationIntensity": 7.5,
                                "windSpeed": 15.0,
                                "windDirection": 90,
                            }
                        },
                        {
                            "startTime": "2026-06-19T10:10:00Z",
                            "values": {
                                "precipitationIntensity": 0.0,
                                "windSpeed": 14.0,
                                "windDirection": 90,
                            }
                        }
                    ]
                }
            ]
        }
    }
    respx.get(url__startswith="https://api.tomorrow.io/v4/timelines").mock(
        return_value=httpx.Response(200, json=tomorrow_payload)
    )

    with patch("app.services.weather_manager.get_repo_context", mock_repo_context):
        manager = WeatherManager()
        result = await manager.predict_rain(13.75, 100.5, force_endpoint="tomorrow")

    assert result is not None
    assert result["endpoint"] == "tomorrow"
    assert result["max_rain"] == 7.5
    # wind_speed_kmh is converted: 15 m/s * 3.6 = 54.0 km/h
    assert result["wind_speed_kmh"] == 54.0


# ────────────────────────────────────────────────────────────
# 2. Auto fallback: xweather ล้มเหลว → tomorrow สำเร็จ
# ────────────────────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_auto_fallback_xweather_fail_to_tomorrow(mock_repo, mock_repo_context, monkeypatch):
    """
    ถ้า xweather (reliability สูงสุด) fail ด้วย 500
    ระบบต้อง fallback ไป tomorrow.io และ return ผลลัพธ์ถูกต้อง
    """
    monkeypatch.setenv("TOMORROW_API_KEY", "mock-key")
    monkeypatch.setenv("XWEATHER_CLIENT_ID", "mock")
    monkeypatch.setenv("XWEATHER_CLIENT_SECRET", "mock")
    monkeypatch.setenv("XWEATHER_ENABLED", "true")

    # xweather ต้องล้มเหลว (500)
    respx.get(url__startswith="https://data.api.xweather.com/").mock(
        return_value=httpx.Response(500, json={"error": "Server Error"})
    )

    # tomorrow ต้องสำเร็จ
    tomorrow_payload = {
        "data": {
            "timelines": [
                {
                    "timestep": "1m",
                    "intervals": [
                        {
                            "startTime": "2026-06-19T10:00:00Z",
                            "values": {
                                "precipitationIntensity": 3.2,
                                "windSpeed": 8.0,
                                "windDirection": 270,
                            }
                        }
                    ]
                }
            ]
        }
    }
    respx.get(url__startswith="https://api.tomorrow.io/v4/timelines").mock(
        return_value=httpx.Response(200, json=tomorrow_payload)
    )

    with patch("app.services.weather_manager.get_repo_context", mock_repo_context):
        manager = WeatherManager()
        result = await manager.predict_rain(13.75, 100.5)

    assert result is not None
    assert result["endpoint"] == "tomorrow"
    assert result["max_rain"] == 3.2


# ────────────────────────────────────────────────────────────
# 3. All-fail: ทุก API ล้มเหลว → ต้องคืน {"endpoint": "error"}
# ────────────────────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_all_apis_fail_returns_error_dict(mock_repo_context, monkeypatch):
    """
    ถ้าทุก API พัง ระบบต้องคืน dict ที่มี endpoint='error'
    แทนที่จะ raise NameError/KeyError/Exception
    ไม่ควรมี crash ที่ไม่คาดคิด
    """
    monkeypatch.setenv("TOMORROW_API_KEY", "mock-key")
    monkeypatch.setenv("XWEATHER_CLIENT_ID", "mock")
    monkeypatch.setenv("XWEATHER_CLIENT_SECRET", "mock")
    monkeypatch.setenv("XWEATHER_ENABLED", "true")

    respx.get(url__startswith="https://data.api.xweather.com/").mock(
        side_effect=httpx.TimeoutException("xweather timeout")
    )
    respx.get(url__startswith="https://api.tomorrow.io/v4/timelines").mock(
        return_value=httpx.Response(500)
    )
    respx.get(url__startswith="https://api.open-meteo.com/v1/forecast").mock(
        side_effect=httpx.TimeoutException("open-meteo timeout")
    )

    with patch("app.services.weather_manager.get_repo_context", mock_repo_context):
        manager = WeatherManager()
        result = await manager.predict_rain(13.75, 100.5)

    # ต้องไม่ crash - ต้องคืน error dict
    assert result is not None
    assert result["endpoint"] == "error"
    assert "predictions" in result
    assert result["max_rain"] == 0.0


# ────────────────────────────────────────────────────────────
# 4. force_endpoint ที่ fail ต้องคืน error dict ไม่ใช่ Exception
# ────────────────────────────────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_forced_endpoint_fail_returns_error_dict(mock_repo_context, monkeypatch):
    """
    force_endpoint ที่ fail ต้องคืน {"endpoint": "error"} ไม่ใช่ raise Exception
    """
    monkeypatch.setenv("TOMORROW_API_KEY", "mock-key")
    respx.get(url__startswith="https://api.tomorrow.io/v4/timelines").mock(
        return_value=httpx.Response(429, json={"error": "Rate limit"})
    )

    with patch("app.services.weather_manager.get_repo_context", mock_repo_context):
        manager = WeatherManager()
        result = await manager.predict_rain(13.75, 100.5, force_endpoint="tomorrow")

    assert result is not None
    assert result["endpoint"] == "error"
