import asyncio
import sys
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta, timezone

# Add backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.scheduler_tasks import check_rain_and_alert
from app.services.rainbow import RainbowService
from app.database import AsyncSessionLocal
from app.services.location import get_active_locations

async def mock_predict(*args, **kwargs):
    """ฟังก์ชันจำลอง (Mock) เพื่อหลอกว่าฝนจะตกในอีก 15 นาที"""
    base_time = datetime.now(timezone.utc)
    rain_time = base_time + timedelta(minutes=15)
    return {
        "predictions": [
            {"time": base_time.isoformat(), "rain": 0},
            {"time": rain_time.isoformat(), "rain": 5.0} # ฝนตกหนัก
        ]
    }

async def main():
    # 1. เคลียร์ข้อมูล last_alerted_at เพื่อให้แน่ใจว่าจะไม่ติด Cooldown 2 ชั่วโมง
    async with AsyncSessionLocal() as session:
        locations = await get_active_locations(session)
        if not locations:
            print("❌ ไม่พบพิกัดในระบบ กรุณาส่ง Location ให้บอทใน Telegram ก่อนครับ")
            return
            
        for loc in locations:
            loc.last_alerted_at = None
        await session.commit()
        print(f"✅ ล้างสถานะ Cooldown ให้กับ {len(locations)} ผู้ใช้งานเรียบร้อยแล้ว")

    # 2. ทำการ Monkey-patch (สับเปลี่ยน) ฟังก์ชันเช็คฝนจริง ด้วยฟังก์ชันจำลอง
    original_predict = RainbowService.predict_rain_by_location
    RainbowService.predict_rain_by_location = mock_predict
    
    print("⛈️ กำลังรันฟังก์ชันแจ้งเตือน โดยจำลองว่าฝนจะตกใน 15 นาที...")
    await check_rain_and_alert()
    
    # คืนค่ากลับ (ถึงแม้ว่า script จะจบการทำงานทันทีก็ตาม)
    RainbowService.predict_rain_by_location = original_predict
    print("✅ ทำงานเสร็จสิ้น ลองเปิดเช็คข้อความใน Telegram ดูครับ!")

if __name__ == "__main__":
    asyncio.run(main())
