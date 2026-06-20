import asyncio
import logging
import sys

# แสดง Logs เพื่อให้เห็นว่ามีการโหลดเรดาร์กี่ครั้ง
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def main():
    from app.services.weather_manager import WeatherManager
    wm = WeatherManager()
    
    # พิกัดหนองคาย (ใช้งานสถานี skn240)
    lat, lng = 17.8785, 102.7420
    
    print("🚀 ยิง 15 Requests พร้อมกัน (Concurrent) ไปที่ TMD Radar...")
    
    # จำลองการทำงานแบบ Parallel 15 Tasks
    tasks = [wm._get_tmd_prediction(lat, lng) for _ in range(15)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successes = sum(1 for r in results if not isinstance(r, Exception))
    error_objs = [r for r in results if isinstance(r, Exception)]
    print(f"✅ ทำงานเสร็จสิ้น! สำเร็จ: {successes}, เออเร่อ: {len(error_objs)}")
    if error_objs:
        print(f"ตัวอย่าง Error: {repr(error_objs[0])}")

if __name__ == "__main__":
    asyncio.run(main())