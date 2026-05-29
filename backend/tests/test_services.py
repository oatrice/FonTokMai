import pytest
from datetime import datetime, timezone
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
    service = RainViewerService()
    metadata = await service.get_current_radar_metadata()
    assert "timestamp" in metadata
    assert "map_layer" in metadata
    assert isinstance(metadata["timestamp"], int)

@pytest.mark.asyncio
async def test_rainbow_service_predict_rain_by_location():
    service = RainbowService()
    # Mocking or integration test with an actual lat, lng (e.g., Sakon Nakhon)
    result = await service.predict_rain_by_location(17.1664, 104.1486)
    assert "predictions" in result
    assert isinstance(result["predictions"], list)

@pytest.mark.asyncio
async def test_check_data_delay():
    service = RainViewerService()
    # Override current time to be far ahead of the data timestamp
    old_timestamp = int(datetime.now(timezone.utc).timestamp()) - 3600 # 1 hour ago
    is_delayed = service.check_data_delay(old_timestamp)
    assert is_delayed is True
