import asyncio
import sys
import os
from dotenv import load_dotenv
load_dotenv(override=True)
from datetime import datetime, timedelta, timezone

# Add backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.scheduler_tasks import check_rain_and_alert
from app.dependencies import get_repo_context
from unittest.mock import patch, AsyncMock
import httpx

async def main():
    # 1. เคลียร์ข้อมูล last_alerted_at และ mock_state
    async with get_repo_context() as repo:
        locations = await repo.get_active_locations()
        if not locations:
            print("❌ ไม่พบพิกัดในระบบ")
            return
            
        for loc in locations:
            await repo.update_last_alerted(loc, datetime.min.replace(tzinfo=timezone.utc))
        print(f"✅ ล้างสถานะ Cooldown ให้กับ {len(locations)} ผู้ใช้งานเรียบร้อยแล้ว")

    # 2. จำลองว่า httpx.AsyncClient.get ยิงไปหาค่ายไหนก็ตามแล้วพังหมด ยกเว้นค่ายสำรอง
    print("⛈️ กำลังรันฟังก์ชันแจ้งเตือน โดยจำลองว่า Xweather เกิด Network Error (Timeout)...")
    
    # เราจะสับเปลี่ยน XweatherService.predict_rain_by_location โดยตรง
    from app.services.xweather import XweatherService
    original_predict = XweatherService.predict_rain_by_location
    
    async def mock_network_error(*args, **kwargs):
        raise httpx.ConnectTimeout("Mocked Network Timeout to Xweather!")
        
    XweatherService.predict_rain_by_location = mock_network_error
    
    try:
        await check_rain_and_alert()
    finally:
        XweatherService.predict_rain_by_location = original_predict
    
    print("✅ ทำงานเสร็จสิ้น ลองเปิดเช็คข้อความใน Telegram ดูครับ!")
    print("ระบบควรจะ Fallback ไปใช้ Tomorrow.io แทน (สังเกตได้จาก Credit ด้านล่างข้อความ)")

if __name__ == "__main__":
    asyncio.run(main())
