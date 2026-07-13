import pytest
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager
from app.services.tmd_radar_processor import TMDRadarProcessor
from app.services.weather_manager import WeatherManager, _DEV_CONFIG

@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_all_api_reliability.return_value = {"tmd-radar": 0.9}
    repo.get_mock_state.return_value = None
    repo.get_global_dev_config.return_value = {}
    return repo

@pytest.fixture
def mock_repo_context(mock_repo):
    @asynccontextmanager
    async def _context():
        yield mock_repo
    return _context

@pytest.mark.asyncio
async def test_find_approaching_clouds_respects_decay_enabled():
    # Setup mock frames and flow
    curr_frame = np.zeros((800, 800, 3), dtype=np.uint8)
    prev_frame = np.zeros((800, 800, 3), dtype=np.uint8)
    flow = np.zeros((800, 800, 2), dtype=np.float32)

    # Let's add some rain pixels within crop area (> 80)
    # Blue: (0, 0, 255) -> 15.0 dBZ
    curr_frame[240, 240] = (0, 255, 0) # now is 20.0 (Green)
    # prev was 15.0 at the backward-traced coordinate (240 - 1 = 239)
    prev_frame[239, 239] = (0, 0, 255)
    
    # flow vector pointing to user at (250, 250)
    flow[240, 240] = [1.0, 1.0]

    processor = TMDRadarProcessor("kkn120")
    
    # Enable decay (default)
    _DEV_CONFIG["decay_enabled"] = True
    clouds_enabled = processor.find_approaching_clouds(
        curr_frame, prev_frame, flow, user_x=250, user_y=250,
        search_radius=20, min_dbz=10.0, cluster_min=1
    )
    
    assert len(clouds_enabled) > 0
    c_enabled = clouds_enabled[0]
    assert c_enabled["growth_rate"] > 0
    # Growth rate is (20 - 15) / 15 = 0.333
    # With decay enabled, predicted_dbz should be calculated using growth_rate
    assert c_enabled["predicted_dbz"] != c_enabled["dbz_now"]

    # Disable decay
    _DEV_CONFIG["decay_enabled"] = False
    clouds_disabled = processor.find_approaching_clouds(
        curr_frame, prev_frame, flow, user_x=250, user_y=250,
        search_radius=20, min_dbz=10.0, cluster_min=1
    )
    
    assert len(clouds_disabled) > 0
    c_disabled = clouds_disabled[0]
    assert c_disabled["predicted_dbz"] == c_disabled["dbz_now"]

@pytest.mark.asyncio
async def test_predict_rain_respects_decay_enabled_and_steps(mock_repo_context):
    manager = WeatherManager()
    
    # Let's mock a TMD radar fetch to return fake frames, flow, etc.
    fake_frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(3)]
    # Set user coordinate at (50, 50) to have a rain pixel
    # Current frame at (50, 50) is Green (20 dBZ)
    fake_frames[-1][50, 50] = (0, 255, 0)
    fake_frames[-2][50, 50] = (0, 0, 255) # 15 dBZ
    
    fake_flow = np.zeros((100, 100, 2), dtype=np.float32)
    # Point flow towards user (doesn't matter much as user is already in rain)
    fake_flow[50, 50] = [1.0, 1.0]

    # Mock fetch/extraction
    mock_processor = MagicMock(spec=TMDRadarProcessor)
    mock_processor.station_code = "kkn120"
    mock_processor.latlng_to_pixel.return_value = (50, 50)
    mock_processor.get_dbz_at_pixel.side_effect = lambda img, x, y: 20.0 if img[y, x, 1] == 255 else (15.0 if img[y, x, 2] == 255 else 0.0)
    mock_processor.render_rain_summary.return_value = "Mock Summary"
    mock_processor.get_wind_speed_kmh.return_value = 10.0
    mock_processor.get_wind_direction_text.return_value = "N"
    
    # Mock extrapolate_rain_at_pixel
    # If rate is 0.0, dbz is constant 20.0
    # If rate is > 0, dbz changes
    def mock_extrapolate(img, flow, px, py, steps, rate=0.0, **kwargs):
        dbz = 20.0
        if rate != 0.0:
            dbz = 20.0 * ((1.0 + rate) ** steps)
        return dbz, px, py

    mock_processor.extrapolate_rain_at_pixel.side_effect = mock_extrapolate

    # Mock cache
    import time
    fake_cache = (fake_frames, None, time.time(), fake_flow, "mock_source", 15.0, [time.time() - 900, time.time()])
    
    with patch("app.services.weather_manager._GLOBAL_TMD_CACHE", {"kkn120": fake_cache}), \
         patch("app.services.weather_manager.TMDRadarProcessor", return_value=mock_processor), \
         patch("app.services.weather_manager.get_repo_context", mock_repo_context):
        
        # Test Default/Enabled: decay_enabled = True, steps = 7
        _DEV_CONFIG["decay_enabled"] = True
        _DEV_CONFIG["prediction_steps"] = 7
        
        # Mock approaching clouds
        mock_clouds = [{
            "cx": 40, "cy": 40, "vx": 1.0, "vy": 1.0,
            "dbz_now": 20.0, "dbz_prev": 15.0, "growth_rate": 0.333,
            "dist": 14.14, "eta_min": 15.0, "approaching": True, "label": "CloudA"
        }]
        mock_processor.find_approaching_clouds.return_value = mock_clouds
        mock_processor.get_all_rain_clusters.return_value = []
        
        result_decay = await manager.predict_rain(16.43, 102.82, force_endpoint="kkn120")
        assert len(result_decay["predictions"]) == 7
        # First prediction (step 0) should be 20.0 DBZ
        assert result_decay["predictions"][0]["dbz"] == pytest.approx(20.0)
        # Next predictions should grow because growth_rate = 0.333 and decay_enabled = True
        assert result_decay["predictions"][1]["dbz"] > 20.0
        
        # Test Disabled: decay_enabled = False, steps = 5
        _DEV_CONFIG["decay_enabled"] = False
        _DEV_CONFIG["prediction_steps"] = 5
        
        result_const = await manager.predict_rain(16.43, 102.82, force_endpoint="kkn120")
        assert len(result_const["predictions"]) == 5
        # All predictions should be exactly 20.0 DBZ because decay_enabled = False, meaning rate = 0
        for p in result_const["predictions"]:
            assert p["dbz"] == pytest.approx(20.0)

def test_config_regex_parsing_with_spaces():
    import re
    pattern = r'(\w+)\s*:\s*([a-zA-Z0-9_.-]+)'
    args = "prediction_steps: 13 decay_enabled: false"
    pairs = re.findall(pattern, args)
    assert len(pairs) == 2
    assert pairs[0] == ("prediction_steps", "13")
    assert pairs[1] == ("decay_enabled", "false")
