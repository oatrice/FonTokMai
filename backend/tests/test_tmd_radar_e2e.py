
import pytest

@pytest.mark.asyncio
async def test_tmd_radar_e2e_prediction_success():
    """
    E2E Test สำหรับ TMD Radar Pipeline ป้องกันบั๊กพวก NameError หรือ Unawaited coroutine
    โดยจะ Mock แค่การดาวน์โหลดภาพเรดาร์จากเว็บ TMD เท่านั้น
    """
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
    
    # Mock cache ตรงเข้าใน module-level แทน
    wm._GLOBAL_TMD_CACHE["skn240"] = (
        [dummy_image, dummy_image], 
        datetime.now(timezone.utc), 
        time.time(), 
        dummy_flow
    )
    # ตัด kkn120/kkn240 ออกเพื่อให้มัน fall through ไป skn240 ที่เรา mock ไว้
    # หรือ mock ทั้งหมดเลยก็ได้
    for st in ["kkn120", "kkn240", "skn240"]:
        wm._GLOBAL_TMD_CACHE[st] = (
            [dummy_image, dummy_image], 
            datetime.now(timezone.utc), 
            time.time(), 
            dummy_flow
        )
        
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

