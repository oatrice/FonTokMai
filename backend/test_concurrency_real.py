import asyncio
import logging
import time
import os
from google.cloud import storage
import sqlite3
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def prepare_database_e2e():
    load_dotenv()
    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
    if not bucket_name:
        logging.error("Missing FIREBASE_STORAGE_BUCKET in .env")
        return False
        
    logging.info(f"Connecting to GCS Bucket: {bucket_name}")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # ดึงไฟล์รูปล่าสุดของ skn240
    station = "skn240"
    blobs = list(bucket.list_blobs(prefix=f"radar/{station}/"))
    blobs.sort(key=lambda x: x.name, reverse=True)
    
    if len(blobs) < 2:
        logging.error(f"Not enough images found in GCS for {station}. Need at least 2.")
        return False
        
    url_t = blobs[0].name
    url_t_minus_1 = blobs[1].name
    
    logging.info(f"Found latest images on GCS:")
    logging.info(f"  T: {url_t}")
    logging.info(f"  T-1: {url_t_minus_1}")
    
    # อัพเดทข้อมูลลงใน Local Database (fonmayang.db) เพื่อจำลองว่า Worker ทำงานเสร็จแล้ว
    db_path = "fonmayang.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO radar_latest_cache 
        (station_code, static_url, loop_url, timestamp, created_at, url_t, url_t_minus_1) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (station, 'dummy', 'dummy', int(time.time()), '2026-06-20 00:00:00', url_t, url_t_minus_1))
    conn.commit()
    conn.close()
    
    logging.info(f"Successfully populated {db_path} with mock worker data.")
    return True

async def main():
    logging.info("Step 1: Preparing E2E Environment (Mocking Worker Sync)...")
    success = await prepare_database_e2e()
    if not success:
        return
        
    logging.info("Step 2: Starting WeatherManager Concurrency Test...")
    from app.services.weather_manager import WeatherManager
    wm = WeatherManager()
    
    # พิกัดหนองคาย (ใช้งานสถานี skn240)
    lat, lng = 17.8785, 102.7420
    
    print("\n🚀 ยิง 15 Requests พร้อมกัน (Concurrent) ไปที่ TMD Radar...")
    
    start_time = time.time()
    tasks = [wm._get_tmd_prediction(lat, lng) for _ in range(15)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    successes = sum(1 for r in results if not isinstance(r, Exception))
    error_objs = [r for r in results if isinstance(r, Exception)]
    
    print(f"\n✅ ทำงานเสร็จสิ้นใน {end_time - start_time:.2f} วินาที!")
    print(f"✅ สำเร็จ: {successes}")
    print(f"❌ เออเร่อ: {len(error_objs)}")
    
    if successes > 0:
        print("\n✅ ตัวอย่างผลลัพธ์ที่ได้จาก Cache (1 ใน 15):")
        # Print first successful result summary
        for r in results:
            if not isinstance(r, Exception):
                print(f"  ความเข้มข้นสูงสุด: {r.get('max_dbz')} dBZ")
                print(f"  Endpoint ที่ใช้: {r.get('endpoint')}")
                break
                
    if error_objs:
        print(f"\n❌ ตัวอย่าง Error: {repr(error_objs[0])}")

if __name__ == "__main__":
    asyncio.run(main())
