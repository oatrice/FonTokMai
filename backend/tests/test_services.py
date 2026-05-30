import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.weather_base import BaseWeatherService
from app.services.rainviewer import RainViewerService
from app.services.rainbow import RainbowService

@pytest.mark.asyncio
async def test_base_weather_service_abstract():
    # Should not be able to instantiate an abstract base class
    with pytest.raises(TypeError):
        BaseWeatherService()

@pytest.mark.asyncio
async def test_rainviewer_service_get_current_radar_metadata():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "host": "https://tilecache.rainviewer.com",
            "radar": {
                "past": [{"time": 1700000000, "path": "/v2/radar/1700000000"}]
            }
        }
        mock_get.return_value = mock_response
        service = RainViewerService()
        metadata = await service.get_current_radar_metadata()
        assert "timestamp" in metadata
        assert "map_layer" in metadata
        assert metadata["timestamp"] == 1700000000
        assert metadata["map_layer"] == "https://tilecache.rainviewer.com/v2/radar/1700000000/256/{z}/{x}/{y}/2/1_1.png"

@pytest.mark.asyncio
async def test_rainbow_service_predict_rain_by_location():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "forecast": [
                {
                    "timestampBegin": 1780063200, # 2026-05-29T14:00:00Z
                    "timestampEnd": 1780063800,   # 10 minutes later
                    "precipRate": 12.5,
                    "precipType": "rain"
                }
            ],
            "summary": {"intensity": "heavy"}
        }
        mock_get.return_value = mock_response
        service = RainbowService()
        result = await service.predict_rain_by_location(17.1664, 104.1486)
        assert "predictions" in result
        assert isinstance(result["predictions"], list)
        assert len(result["predictions"]) == 1
        assert result["predictions"][0]["rain"] == 12.5

@pytest.mark.asyncio
async def test_rainbow_service_extended_data_heavy_rain():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "forecast": [
                {"timestampBegin": 1780063200, "timestampEnd": 1780063800, "precipRate": 0},
                {"timestampBegin": 1780063800, "timestampEnd": 1780064400, "precipRate": 2.0},
                {"timestampBegin": 1780064400, "timestampEnd": 1780065000, "precipRate": 12.5},
                {"timestampBegin": 1780065000, "timestampEnd": 1780065600, "precipRate": 5.0},
                {"timestampBegin": 1780065600, "timestampEnd": 1780066200, "precipRate": 0}
            ],
            "summary": {"intensity": "heavy"}
        }
        mock_get.return_value = mock_response
        service = RainbowService()
        result = await service.predict_rain_by_location(17.1664, 104.1486)
        
        assert result["intensity"] == "หนัก (Heavy)"
        assert result["duration_minutes"] == 30 # 14:10 to 14:40 is 30 mins

@pytest.mark.asyncio
async def test_rainbow_service_extended_data_light_rain():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "forecast": [
                {"timestampBegin": 1780063200, "timestampEnd": 1780063800, "precipRate": 1.5},
                {"timestampBegin": 1780063800, "timestampEnd": 1780064400, "precipRate": 2.0},
                {"timestampBegin": 1780064400, "timestampEnd": 1780065000, "precipRate": 0}
            ],
            "summary": {"intensity": "light"}
        }
        mock_get.return_value = mock_response
        service = RainbowService()
        result = await service.predict_rain_by_location(17.1664, 104.1486)
        
        assert result["intensity"] == "เบา (Light)"
        assert result["duration_minutes"] == 20 # 14:00 to 14:20 is 20 mins

@pytest.mark.asyncio
async def test_rainbow_service_endpoint_type():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "forecast": [],
            "summary": {"intensity": "no_precipitation"}
        }
        mock_get.return_value = mock_response
        service = RainbowService()
        
        # Test global (default)
        result_global = await service.predict_rain_by_location(17.1664, 104.1486)
        assert mock_get.call_args[0][0] == "https://api.rainbow.ai/nowcast/v1/precip-global/104.1486/17.1664"
        assert result_global["endpoint"] == "global"
        
        # Test radar
        result_radar = await service.predict_rain_by_location(17.1664, 104.1486, endpoint_type="radar")
        assert mock_get.call_args[0][0] == "https://api.rainbow.ai/nowcast/v1/precip/104.1486/17.1664"
        assert result_radar["endpoint"] == "radar"


@pytest.mark.asyncio
async def test_check_data_delay():
    service = RainViewerService()
    # Override current time to be far ahead of the data timestamp
    old_timestamp = int(datetime.now(timezone.utc).timestamp()) - 3600 # 1 hour ago
    is_delayed = service.check_data_delay(old_timestamp)
    assert is_delayed is True
