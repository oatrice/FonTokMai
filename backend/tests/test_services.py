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

@pytest.mark.asyncio
async def test_weather_manager_compare_all_apis():
    from app.services.weather_manager import WeatherManager
    
    manager = WeatherManager()
    manager.tomorrow_svc.predict_rain_by_location = AsyncMock(return_value={"endpoint": "tomorrow", "max_rain": 1.0})
    
    async def mock_rainbow(lat, lng, endpoint_type="global", mock_state=None):
        return {"endpoint": endpoint_type, "max_rain": 2.0}
        
    manager.rainbow_svc.predict_rain_by_location = AsyncMock(side_effect=mock_rainbow)
    
    with patch("app.services.weather_manager.get_repo_context") as mock_repo_context:
        mock_repo = AsyncMock()
        mock_repo.get_all_api_reliability.return_value = {"tomorrow": 0.9, "rainbow-local": 0.8, "rainbow-global": 0.7}
        mock_repo_context.return_value.__aenter__.return_value = mock_repo
        
        results = await manager.compare_all_apis(13.0, 100.0)
    
    assert "tomorrow" in results
    assert "rainbow-local" in results
    assert "rainbow-global" in results
    
    assert results["tomorrow"]["max_rain"] == 1.0
    assert results["rainbow-local"]["max_rain"] == 2.0
    assert results["rainbow-global"]["max_rain"] == 2.0

@pytest.mark.asyncio
async def test_weather_manager_fallback_chain():
    from app.services.weather_manager import WeatherManager
    
    manager = WeatherManager()
    
    with patch("app.services.weather_manager.get_repo_context") as mock_repo_context:
        mock_repo = AsyncMock()
        mock_repo.get_all_api_reliability.return_value = {
            "xweather": 1.0, 
            "tomorrow": 0.9, 
            "rainbow-local": 0.8, 
            "rainbow-global": 0.7
        }
        mock_repo_context.return_value.__aenter__.return_value = mock_repo
        
        # 1. Test Xweather succeeds
        manager.xweather_svc.predict_rain_by_location = AsyncMock(return_value={"endpoint": "xweather", "max_rain": 5.0})
        manager.tomorrow_svc.predict_rain_by_location = AsyncMock(return_value={"endpoint": "tomorrow", "max_rain": 1.0})
        result = await manager.predict_rain(13.0, 100.0)
        assert result["endpoint"] == "xweather"
        assert result["max_rain"] == 5.0
        manager.tomorrow_svc.predict_rain_by_location.assert_not_called()
        
        # 2. Test Xweather fails -> fall back to Tomorrow.io
        manager.xweather_svc.predict_rain_by_location = AsyncMock(side_effect=Exception("Xweather failed"))
        manager.tomorrow_svc.predict_rain_by_location.reset_mock()
        result = await manager.predict_rain(13.0, 100.0)
        assert result["endpoint"] == "tomorrow"
        assert result["max_rain"] == 1.0
        manager.tomorrow_svc.predict_rain_by_location.assert_called_once()

@pytest.mark.asyncio
async def test_weather_manager_get_advanced_alerts_fallback():
    from app.services.weather_manager import WeatherManager
    
    manager = WeatherManager()
    manager.xweather_svc.enabled = True
    
    # 1. Test Xweather succeeds
    manager.xweather_svc.get_advanced_alerts = AsyncMock(return_value={
        "advisories": [], "lightning": None, "stormcell": {"distance_km": 5.0, "direction": "N", "speed_kmh": 20.0, "max_dbz": 45}
    })
    manager.open_meteo_svc.get_wind_vector = AsyncMock()
    
    res1 = await manager.get_advanced_alerts(13.0, 100.0)
    assert res1["stormcell"]["distance_km"] == 5.0
    assert res1["stormcell"]["direction"] == "N"
    manager.open_meteo_svc.get_wind_vector.assert_not_called()
    
    # 2. Test Xweather fails -> fallback to Open-Meteo contingency
    manager.xweather_svc.get_advanced_alerts = AsyncMock(side_effect=Exception("Xweather API timeout"))
    manager.open_meteo_svc.get_wind_vector = AsyncMock(return_value={
        "direction_cardinal": "NE",
        "speed_kmh": 35.5
    })
    
    res2 = await manager.get_advanced_alerts(13.0, 100.0)
    assert res2["stormcell"]["distance_km"] is None
    assert res2["stormcell"]["direction"] == "NE"
    assert res2["stormcell"]["speed_kmh"] == 35.5
    manager.open_meteo_svc.get_wind_vector.assert_called_once()

    # 3. Test Xweather is disabled -> fallback to Open-Meteo contingency
    manager.xweather_svc.enabled = False
    manager.open_meteo_svc.get_wind_vector.reset_mock()
    manager.open_meteo_svc.get_wind_vector = AsyncMock(return_value={
        "direction_cardinal": "S",
        "speed_kmh": 12.0
    })
    
    res3 = await manager.get_advanced_alerts(13.0, 100.0)
    assert res3["stormcell"]["distance_km"] is None
    assert res3["stormcell"]["direction"] == "S"
    assert res3["stormcell"]["speed_kmh"] == 12.0
    manager.open_meteo_svc.get_wind_vector.assert_called_once()
