import pytest
import time
import httpx
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

# Apply basic mocks for import stubs
def _install_stubs(monkeypatch):
    import sys
    import types
    ocr_stub = types.ModuleType("app.services.ocr_service")
    ocr_stub.OCRService = MagicMock()
    monkeypatch.setitem(sys.modules, "app.services.ocr_service", ocr_stub)
    
    storage_stub = types.ModuleType("google.cloud.storage")
    storage_stub.Client = MagicMock()
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage_stub)

@pytest.mark.asyncio
async def test_cache_busting_added_to_http_calls(monkeypatch):
    """Test that all HTTP requests to weather.tmd.go.th have a cache-busting query parameter."""
    _install_stubs(monkeypatch)
    from app.services.tmd_radar_processor import TMDRadarProcessor

    processor = TMDRadarProcessor("kkn240")
    
    # We will mock httpx.AsyncClient.get
    mock_get = AsyncMock()
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "v=250626_1030"
    mock_get.return_value.content = b"GIF89a..."
    mock_get.return_value.headers = {"last-modified": "Mon, 13 Jul 2026 15:30:00 GMT"}
    
    with patch("httpx.AsyncClient.get", mock_get):
        await processor.fetch_station_timestamp_utc()
        await processor.fetch_latest_image_bytes()
        await processor.fetch_loop_gif_and_extract_frames()
        
    assert mock_get.call_count >= 3
    for call in mock_get.call_args_list:
        url = call.args[0]
        assert "?t=" in url or "&t=" in url
        # Check that the query parameter has a number (timestamp)
        part = url.split("t=")[1]
        assert part.isdigit()

@pytest.mark.asyncio
async def test_weather_manager_triggers_update_when_cache_stale(monkeypatch):
    """Test that WeatherManager._get_tmd_prediction triggers live update if cache is stale."""
    _install_stubs(monkeypatch)
    from app.services.weather_manager import WeatherManager
    from app.services import weather_manager as wm
    from app.services.tmd_radar_processor import TMDRadarProcessor

    manager = WeatherManager()
    
    # Set stale cache (older than 20 minutes)
    stale_time = time.time() - 1300 # 21.6 minutes ago
    dummy_image = np.zeros((800, 800, 3), dtype=np.uint8)
    dummy_flow = np.zeros((800, 800, 2), dtype=np.float32)
    stale_entry = (
        [dummy_image, dummy_image],
        datetime.now(timezone.utc),
        stale_time,
        dummy_flow,
        "static_cache",
        15.0,
        [int(stale_time) - 900, int(stale_time)]
    )
    
    wm._GLOBAL_TMD_CACHE["kkn240"] = stale_entry
    
    mock_update_cache = AsyncMock()
    # Mock update_radar_cache to return a status dict
    mock_update_cache.return_value = {"updated": True}
    
    monkeypatch.setattr(TMDRadarProcessor, "update_radar_cache", mock_update_cache)
    
    # Trigger prediction for a coordinate inside kkn240
    lat, lng = 16.43, 102.82 # Center of KKN
    
    with patch("app.services.weather_manager.get_repo_context") as mock_repo_context:
        # Mock load_persistent_cache_to_memory to return stale entry
        mock_load = AsyncMock(return_value=stale_entry)
        monkeypatch.setattr(manager, "load_persistent_cache_to_memory", mock_load)
        
        await manager._get_tmd_prediction(lat, lng, force_station="kkn240")
        
    # verify that update_radar_cache was called because cache was older than 20 minutes
    mock_update_cache.assert_called_once()
