import asyncio
import sys
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta, timezone

# Add backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.scheduler_tasks import check_rain_and_alert
from app.services.weather_manager import WeatherManager
from app.dependencies import get_repo_context

async def main():
    # 1. เคลียร์ข้อมูล last_alerted_at เพื่อให้แน่ใจว่าจะไม่ติด Cooldown
    async with get_repo_context() as repo:
        locations = await repo.get_active_locations()
        if not locations:
            print("❌ ไม่พบพิกัดในระบบ กรุณาส่ง Location ให้บอทใน Telegram ก่อนครับ")
            return
            
        for loc in locations:
            await repo.update_last_alerted(loc, datetime.min.replace(tzinfo=timezone.utc))
        print(f"✅ ล้างสถานะ Cooldown ให้กับ {len(locations)} ผู้ใช้งานเรียบร้อยแล้ว")

    # 2. ทำการ Monkey-patch (สับเปลี่ยน) WeatherManager เพื่อหลอกว่ามีพายุเข้า
    original_predict = WeatherManager.predict_rain
    original_advanced = WeatherManager.get_advanced_alerts
    
    async def mock_predict(*args, **kwargs):
        base_time = datetime.now(timezone.utc)
        rain_time = base_time + timedelta(minutes=15)
        return {
            "predictions": [
                {"time": base_time.isoformat(), "rain": 0},
                {"time": rain_time.isoformat(), "rain": 15.0} # ฝนตกหนักมาก
            ],
            "max_rain": 15.0,
            "intensity": "หนัก (Heavy)",
            "duration_minutes": 45,
            "wind_speed_kmh": 35.0,
            "endpoint": "xweather"
        }
        
    async def mock_advanced(*args, **kwargs):
        return {
            "advisories": [{"name": "Severe Thunderstorm Warning (จำลอง)"}],
            "lightning": {"distance_km": 2.5},
            "stormcell": {"distance_km": 10.0, "max_dbz": 60, "speed_kmh": 40, "direction": "NE"}
        }

    WeatherManager.predict_rain = mock_predict
    WeatherManager.get_advanced_alerts = mock_advanced
    
    print("⛈️ กำลังรันฟังก์ชันแจ้งเตือน โดยจำลองว่าฝนและพายุจะเข้าใน 15 นาที...")
    await check_rain_and_alert()
    
    # คืนค่ากลับ
    WeatherManager.predict_rain = original_predict
    WeatherManager.get_advanced_alerts = original_advanced
    print("✅ ทำงานเสร็จสิ้น ลองเปิดเช็คข้อความใน Telegram ดูครับ!")

if __name__ == "__main__":
    asyncio.run(main())
