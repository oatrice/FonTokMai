import pytest
import respx
import httpx
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.services.xweather import XweatherService

@pytest.fixture
def xweather_service(monkeypatch):
    monkeypatch.setenv("XWEATHER_CLIENT_ID", "mock_id")
    monkeypatch.setenv("XWEATHER_CLIENT_SECRET", "mock_secret")
    monkeypatch.setenv("XWEATHER_ENABLED", "true")
    return XweatherService()

@pytest.mark.asyncio
async def test_xweather_disabled_raises_error(monkeypatch):
    monkeypatch.setenv("XWEATHER_ENABLED", "false")
    service = XweatherService()
    with pytest.raises(ValueError, match="Xweather is disabled"):
        await service.predict_rain_by_location(13.0, 100.0)

@respx.mock
@pytest.mark.asyncio
async def test_xweather_circuit_breaker(xweather_service):
    # Mock a 429 response
    route = respx.get("https://data.api.xweather.com/minutecast").mock(
        return_value=httpx.Response(429, json={"error": "Too Many Requests", "description": "Rate limit exceeded"})
    )
    
    # First request should fail and open the circuit breaker
    with pytest.raises(httpx.HTTPStatusError):
        await xweather_service.predict_rain_by_location(13.0, 100.0)
        
    assert route.called
    assert xweather_service._is_circuit_open() is True
    
    # Second request should immediately raise Exception without making HTTP call
    route.reset()
    with pytest.raises(Exception, match="circuit is open"):
        await xweather_service.predict_rain_by_location(13.0, 100.0)
    assert not route.called

@respx.mock
@pytest.mark.asyncio
async def test_xweather_predict_rain_success(xweather_service):
    mock_response = {
        "success": True,
        "error": None,
        "response": {
            "loc": {"lat": 13.0, "long": 100.0},
            "periods": [
                {
                    "timestamp": 1717500000,
                    "dateTimeISO": "2026-06-04T12:00:00Z",
                    "precipMM": 2.5,
                    "precipType": "rain",
                    "windSpeedKPH": 15.0
                },
                {
                    "timestamp": 1717500060,
                    "dateTimeISO": "2026-06-04T12:01:00Z",
                    "precipMM": 0.0,
                    "precipType": "none",
                    "windSpeedKPH": 10.0
                }
            ]
        }
    }
    
    respx.get("https://data.api.xweather.com/minutecast").mock(
        return_value=httpx.Response(200, json=mock_response)
    )
    
    result = await xweather_service.predict_rain_by_location(13.0, 100.0)
    
    assert result["endpoint"] == "xweather"
    assert result["max_rain"] == 2.5
    assert result["intensity"] == "ปานกลาง (Moderate)"
    assert len(result["predictions"]) == 2
    assert result["predictions"][0]["rain"] == 2.5
    assert result["wind_speed_kmh"] == 15.0 # average wind during rain
