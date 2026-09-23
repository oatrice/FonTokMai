
import pytest


def _install_weather_manager_import_stubs(monkeypatch):
    import sys
    import types

    ocr_stub = types.ModuleType("app.services.ocr_service")
    ocr_stub.OCRService = object
    monkeypatch.setitem(sys.modules, "app.services.ocr_service", ocr_stub)

    storage_stub = types.ModuleType("google.cloud.storage")
    storage_stub.Client = object
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage_stub)


@pytest.mark.asyncio
async def test_tmd_radar_e2e_prediction_success(monkeypatch):
    """
    E2E Test สำหรับ TMD Radar Pipeline ป้องกันบั๊กพวก NameError หรือ Unawaited coroutine
    โดยจะ Mock แค่การดาวน์โหลดภาพเรดาร์จากเว็บ TMD เท่านั้น
    """
    _install_weather_manager_import_stubs(monkeypatch)

    from app.services.weather_manager import WeatherManager
    from unittest.mock import AsyncMock, patch
    import numpy as np
    import cv2
    
    # พิกัดหนองคาย
    lat, lng = 17.8785, 102.7420
    
    # สร้างภาพจำลองเรดาร์ขนาด 800x800 สีดำ และสมมติให้มีสีฝนตกนิดหน่อย
    dummy_image = np.zeros((800, 800, 3), dtype=np.uint8)
    # วาดจุดสีเขียว (ฝนอ่อน) ตรงกลาง
    cv2.circle(dummy_image, (400, 400), 10, (0, 255, 0), -1)
    
    from datetime import datetime, timezone
    import time
    from app.services.tmd_radar_processor import TMDRadarProcessor

    manager = WeatherManager()
    
    # คำนวณ dummy flow ด้วย processor เพื่อให้ format ถูกต้อง
    processor = TMDRadarProcessor("skn240")
    dummy_flow = processor.calculate_optical_flow([dummy_image, dummy_image])
    
    from app.services import weather_manager as wm
    from app.services.tmd_radar.cache_manager import radar_cache

    
    # Mock cache ตรงเข้าใน module-level แทน
    radar_cache.set("skn240", [dummy_image, dummy_image], datetime.now(timezone.utc), dummy_flow, "static", 15.0, [], [])
    # ตัด kkn120/kkn240 ออกเพื่อให้มัน fall through ไป skn240 ที่เรา mock ไว้
    # หรือ mock ทั้งหมดเลยก็ได้
    for st in ["kkn120", "kkn240", "skn240"]:
        radar_cache.set(st, [dummy_image, dummy_image], datetime.now(timezone.utc), dummy_flow, "static", 15.0, [], [])
        
    result = await manager._get_tmd_prediction(lat, lng)
    
    # ตรวจสอบว่าได้ข้อมูลจาก tmd-radar หรือ skn240 / kkn240 จริงๆ ไม่ได้ถูก Fallback เป็น tomorrow.io
    assert result is not None
    assert "tmd-radar" in result["endpoint"]
        
    # ตรวจสอบว่าไม่ติดบั๊ก (gif_bytes ถูกตั้งเป็น None, render_hq_png ไม่แจ้งเตือน)
    assert "radar_gif_bytes" in result
    assert result["radar_gif_bytes"] is None
    assert "radar_hq_gif_bytes" in result
    assert result["radar_hq_gif_bytes"] is None
    
    # ต้องมีการสร้าง static image มาให้
    assert "radar_static_bytes" in result
    assert result["radar_static_bytes"] is not None
    assert len(result["radar_static_bytes"]) > 0


def test_tmd_radar_cached_static_frames_use_static_pixel_mapping(monkeypatch):
    """
    The Cloud Run radar pipeline reads T/T-1 static images from radar_latest_cache.
    User coordinates must therefore be mapped with static crop settings, not loop GIF
    crop settings, before drawing the pin or sampling rain at that pixel.
    """
    import asyncio
    from datetime import datetime, timezone
    import time
    import cv2
    import numpy as np

    _install_weather_manager_import_stubs(monkeypatch)

    from app.services.weather_manager import WeatherManager
    from app.services import weather_manager as wm
    from app.services.tmd_radar.cache_manager import radar_cache

    from app.services.tmd_radar_processor import TMDRadarProcessor

    lat, lng = 17.8785, 102.7420  # Nong Khai: covered by kkn240.
    dummy_image = np.zeros((800, 800, 3), dtype=np.uint8)
    cv2.circle(dummy_image, (425, 158), 10, (0, 255, 0), -1)

    processor = TMDRadarProcessor("kkn240")
    dummy_flow = processor.calculate_optical_flow([dummy_image, dummy_image])
    cached_entry = ([dummy_image, dummy_image], datetime.now(timezone.utc), dummy_flow, "static", 15.0, [], [])

    original_cache = {st: radar_cache.get(st) for st in radar_cache.get_all_stations()}
    radar_cache.clear()
    for station_code in ["kkn120", "kkn240", "skn240"]:
        radar_cache.set(station_code, *cached_entry)

    calls = []
    original_latlng_to_pixel = TMDRadarProcessor.latlng_to_pixel

    def record_latlng_to_pixel(self, lat_arg, lng_arg, is_loop=True, projection=None, **kwargs):
        calls.append((self.station_code, is_loop))
        return original_latlng_to_pixel(self, lat_arg, lng_arg, is_loop=is_loop, projection=projection, **kwargs)

    monkeypatch.setattr(TMDRadarProcessor, "latlng_to_pixel", record_latlng_to_pixel)

    try:
        result = asyncio.run(WeatherManager()._get_tmd_prediction(lat, lng))
    finally:
        radar_cache.clear()
        for st, v in original_cache.items(): radar_cache.set(st, v.frames, v.last_modified_dt, v.cache_timestamp, v.flow, v.frame_source, v.data_gap_minutes, v.frame_timestamps, v.frame_urls)

    assert result["endpoint"] == "tmd-radar (kkn240)"
    assert ("kkn240", False) in calls


def test_tmd_radar_cached_static_frames_use_static_pixel_mapping_skn(monkeypatch):
    """
    SKN 240km cached static frames should still use static mapping for the user pin.
    """
    import asyncio
    from datetime import datetime, timezone
    import time
    import cv2
    import numpy as np

    _install_weather_manager_import_stubs(monkeypatch)

    from app.services.weather_manager import WeatherManager
    from app.services import weather_manager as wm
    from app.services.tmd_radar.cache_manager import radar_cache

    from app.services.tmd_radar_processor import TMDRadarProcessor

    lat, lng = 17.8785, 102.7420  # Nong Khai still reaches kkn240 first, but skn can be forced by cache setup.
    dummy_image = np.zeros((800, 800, 3), dtype=np.uint8)
    cv2.circle(dummy_image, (425, 158), 10, (0, 255, 0), -1)

    processor = TMDRadarProcessor("skn240")
    dummy_flow = processor.calculate_optical_flow([dummy_image, dummy_image])
    cached_entry = ([dummy_image, dummy_image], datetime.now(timezone.utc), dummy_flow, "static", 15.0, [], [])

    original_cache = {st: radar_cache.get(st) for st in radar_cache.get_all_stations()}
    radar_cache.clear()
    radar_cache.set("skn240", *cached_entry)

    calls = []
    original_latlng_to_pixel = TMDRadarProcessor.latlng_to_pixel

    def record_latlng_to_pixel(self, lat_arg, lng_arg, is_loop=True, projection=None, **kwargs):
        calls.append((self.station_code, is_loop))
        return original_latlng_to_pixel(self, lat_arg, lng_arg, is_loop=is_loop, projection=projection, **kwargs)

    monkeypatch.setattr(TMDRadarProcessor, "latlng_to_pixel", record_latlng_to_pixel)

    try:
        result = asyncio.run(WeatherManager()._get_tmd_prediction(lat, lng, force_station="skn240"))
    finally:
        radar_cache.clear()
        for st, v in original_cache.items(): radar_cache.set(st, v.frames, v.last_modified_dt, v.cache_timestamp, v.flow, v.frame_source, v.data_gap_minutes, v.frame_timestamps, v.frame_urls)

    assert result["endpoint"] == "tmd-radar (skn240)"
    assert ("skn240", False) in calls


@pytest.mark.asyncio
async def test_tmd_radar_fresh_loop_fallback_works(monkeypatch):
    _install_weather_manager_import_stubs(monkeypatch)

    from contextlib import asynccontextmanager
    from datetime import datetime, timezone
    import time
    import numpy as np
    import cv2

    from app.services.weather_manager import WeatherManager
    from app.services import weather_manager as wm
    from app.services.tmd_radar.cache_manager import radar_cache

    from app.services.tmd_radar_processor import TMDRadarProcessor
    from unittest.mock import MagicMock, AsyncMock

    lat, lng = 17.8785, 102.7420
    frame_a = np.zeros((800, 800, 3), dtype=np.uint8)
    frame_b = np.zeros((800, 800, 3), dtype=np.uint8)
    cv2.circle(frame_b, (400, 400), 24, (0, 255, 0), -1)

    repo = MagicMock()
    repo.get_latest_radar_cache = AsyncMock(return_value=None)
    repo.set_latest_radar_cache = AsyncMock()

    @asynccontextmanager
    async def mock_repo_context():
        yield repo

    original_cache = {st: radar_cache.get(st) for st in radar_cache.get_all_stations()}
    radar_cache.clear()

    calls = []
    original_latlng_to_pixel = TMDRadarProcessor.latlng_to_pixel

    def record_latlng_to_pixel(self, lat_arg, lng_arg, is_loop=True, projection=None, **kwargs):
        calls.append((self.station_code, is_loop))
        return original_latlng_to_pixel(self, lat_arg, lng_arg, is_loop=is_loop, projection=projection, **kwargs)

    async def fake_fetch(self, status_callback=None, use_cache=True):
        if self.station_code == "kkn240":
            return [frame_a, frame_b], datetime.now(timezone.utc), b"fresh-loop-bytes"
        return [], None, None

    async def fake_save(self, image_bytes):
        assert image_bytes == b"fresh-loop-bytes"
        return "radar/kkn240/kkn240_fresh.gif"

    monkeypatch.setattr("app.services.weather_manager.get_repo_context", mock_repo_context)
    monkeypatch.setattr(TMDRadarProcessor, "fetch_loop_gif_and_extract_frames", fake_fetch)
    monkeypatch.setattr(TMDRadarProcessor, "save_polled_frame", fake_save)
    monkeypatch.setattr(TMDRadarProcessor, "latlng_to_pixel", record_latlng_to_pixel)

    try:
        result = await WeatherManager()._get_tmd_prediction(lat, lng, mock_state="storm")
    finally:
        radar_cache.clear()
        for st, v in original_cache.items(): radar_cache.set(st, v.frames, v.last_modified_dt, v.cache_timestamp, v.flow, v.frame_source, v.data_gap_minutes, v.frame_timestamps, v.frame_urls)

    assert result["endpoint"] == "tmd-radar (kkn240)"
    assert result["radar_static_bytes"] is not None
    assert result["radar_tracking_bytes"] is not None
    assert result["rain_timeline_bytes"] is not None
    assert ("kkn240", True) in calls


def test_tmd_prediction_timestamps_based_on_now_utc(monkeypatch):
    """
    Test that predictions from TMD Radar use the cache's frame time (now_utc)
    rather than the server's current run time (current_utc).
    """
    import asyncio
    from datetime import datetime, timezone, timedelta
    import time
    import numpy as np
    import cv2

    _install_weather_manager_import_stubs(monkeypatch)

    from app.services.weather_manager import WeatherManager
    from app.services import weather_manager as wm
    from app.services.tmd_radar.cache_manager import radar_cache

    from app.services.tmd_radar_processor import TMDRadarProcessor

    lat, lng = 17.8785, 102.7420
    dummy_image = np.zeros((800, 800, 3), dtype=np.uint8)
    
    # 20 minutes in the past
    past_now_utc = datetime.now(timezone.utc) - timedelta(minutes=20)
    
    processor = TMDRadarProcessor("kkn240")
    dummy_flow = processor.calculate_optical_flow([dummy_image, dummy_image])
    cached_entry = ([dummy_image, dummy_image], past_now_utc, dummy_flow, "static", 15.0, [], [])

    original_cache = {st: radar_cache.get(st) for st in radar_cache.get_all_stations()}
    radar_cache.clear()
    for station_code in ["kkn120", "kkn240", "skn240"]:
        radar_cache.set(station_code, *cached_entry)

    try:
        result = asyncio.run(WeatherManager()._get_tmd_prediction(lat, lng))
    finally:
        radar_cache.clear()
        for st, v in original_cache.items(): radar_cache.set(st, v.frames, v.last_modified_dt, v.cache_timestamp, v.flow, v.frame_source, v.data_gap_minutes, v.frame_timestamps, v.frame_urls)

    assert result is not None
    predictions = result.get("predictions", [])
    assert len(predictions) > 0
    
    # The first prediction timestamp should match past_now_utc, not current time
    pred_time_0 = datetime.fromisoformat(predictions[0]["time"].replace("Z", "+00:00"))
    time_diff_sec = abs((pred_time_0 - past_now_utc).total_seconds())
    
    # It must be within 1 second of past_now_utc
    assert time_diff_sec < 1.0


@pytest.mark.asyncio
async def test_tmd_radar_no_false_failover_notice_for_outer_boundary(monkeypatch):
    """
    Verify that when coordinates (e.g. Nong Khai / Thabo) fall outside kkn120 (120km)
    but inside kkn240 (240km), kkn240 is selected as primary without emitting a false
    'radar failed / offline' notice.
    """
    _install_weather_manager_import_stubs(monkeypatch)

    from app.services.weather_manager import WeatherManager
    from app.services import weather_manager as wm
    from app.services.tmd_radar.cache_manager import radar_cache

    from datetime import datetime, timezone
    import time
    import numpy as np

    # Thabo, Nong Khai (outside kkn120 120km radius, inside kkn240)
    lat, lng = 17.8392, 102.5734
    dummy_image = np.zeros((724, 724, 3), dtype=np.uint8)

    from app.services.tmd_radar_processor import TMDRadarProcessor
    processor = TMDRadarProcessor("kkn240")
    dummy_flow = processor.calculate_optical_flow([dummy_image, dummy_image])

    original_cache = {st: radar_cache.get(st) for st in radar_cache.get_all_stations()}
    radar_cache.clear()
    
    # Mock fresh cache for kkn240
    radar_cache.set("kkn240", [dummy_image, dummy_image], datetime.now(timezone.utc), dummy_flow, "static", 15.0, [], [])

    try:
        result = await WeatherManager()._get_tmd_prediction(lat, lng)
    finally:
        radar_cache.clear()
        for st, v in original_cache.items(): radar_cache.set(st, v.frames, v.last_modified_dt, v.cache_timestamp, v.flow, v.frame_source, v.data_gap_minutes, v.frame_timestamps, v.frame_urls)

    assert result is not None
    assert result["endpoint"] == "tmd-radar (kkn240)"
    # failover_notice MUST be None because kkn240 is the legitimate primary covering station
    assert result.get("failover_notice") is None


