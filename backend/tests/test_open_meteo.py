import pytest
import respx
import httpx
from datetime import datetime, timezone

from app.services.open_meteo import OpenMeteoService

@pytest.fixture
def open_meteo_service():
    return OpenMeteoService(default_model="auto")

@respx.mock
@pytest.mark.asyncio
async def test_open_meteo_predict_rain_success(open_meteo_service):
    mock_response = {
        "minutely_15": {
            "time": ["2026-06-05T12:00", "2026-06-05T12:15"],
            "precipitation": [0.0, 5.5]
        },
        "hourly": {
            "time": ["2026-06-05T12:00", "2026-06-05T13:00"],
            "wind_speed_10m": [15.0, 20.0]
        }
    }
    
    respx.get(url__startswith="https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json=mock_response)
    )
    
    result = await open_meteo_service.predict_rain_by_location(13.0, 100.0)
    
    assert result["endpoint"] == "open_meteo"
    assert result["max_rain"] == 5.5
    assert result["intensity"] == "ปานกลาง (Moderate)"
    assert len(result["predictions"]) == 2
    assert result["predictions"][1]["rain"] == 5.5
    assert result["wind_speed_kmh"] == 15.0  # From hourly data

@respx.mock
@pytest.mark.asyncio
async def test_open_meteo_get_wind_vector_success(open_meteo_service):
    mock_response = {
        "current": {
            "time": "2026-06-05T12:00",
            "wind_speed_10m": 25.5,
            "wind_direction_10m": 45
        }
    }
    
    respx.get(url__startswith="https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json=mock_response)
    )
    
    result = await open_meteo_service.get_wind_vector(13.0, 100.0)
    
    assert result["speed_kmh"] == 25.5
    assert result["direction_deg"] == 45
    assert result["direction_cardinal"] == "NE"
    assert result["source"] == "open_meteo"

@pytest.mark.asyncio
async def test_open_meteo_mock_state(open_meteo_service):
    # Test "rain" state
    rain_res = await open_meteo_service.predict_rain_by_location(13.0, 100.0, mock_state="rain")
    assert rain_res["max_rain"] == 15.0
    assert rain_res["intensity"] == "หนัก (Heavy)"
    
    # Test "clear" state
    clear_res = await open_meteo_service.predict_rain_by_location(13.0, 100.0, mock_state="clear")
    assert clear_res["max_rain"] == 0.0
    
    # Test "error" state
    with pytest.raises(Exception, match="Mock Network Error"):
        await open_meteo_service.predict_rain_by_location(13.0, 100.0, mock_state="error")

@respx.mock
@pytest.mark.asyncio
async def test_open_meteo_custom_model(open_meteo_service):
    respx.get(url__startswith="https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json={
            "minutely_15": {"time": ["2026-06-05T12:00"], "precipitation": [0.0]},
            "hourly": {"time": ["2026-06-05T12:00"], "wind_speed_10m": [0.0]}
        })
    )
    
    # Pass a custom model
    await open_meteo_service.predict_rain_by_location(13.0, 100.0, model="icon_global")
    
    # Extract the last request
    request = respx.calls.last.request
    assert "models=icon_global" in str(request.url)
