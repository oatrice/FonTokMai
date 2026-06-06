# Manual Verification Guide: TMD Radar Optical Flow & Polling

เอกสารนี้จะช่วยอธิบายวิธีการทดสอบระบบ (Manual Testing) ให้สามารถทำตามได้ง่ายแบบ Step-by-Step พร้อมคำสั่งที่ก๊อปปี้ไปวางได้เลย

---

## Test Case 1: ทดสอบการดูดภาพเรดาร์และเซฟลง GCS
**เป้าหมาย:** เช็คว่าระบบสามารถโหลดภาพเรดาร์และอัปโหลดเข้า Firebase Storage ได้ถูกต้องหรือไม่

- **Step 1:** ตรวจสอบว่าในไฟล์ `backend/.env` ของคุณมีตัวแปร `FIREBASE_STORAGE_BUCKET=fonmayang-xxxx.appspot.com` และ `GOOGLE_APPLICATION_CREDENTIALS` ถูกต้อง
- **Step 2:** เปิด Terminal (cd เข้าไปที่โฟลเดอร์ `backend`)
- **Step 3:** รันคำสั่งนี้เพื่อบังคับเรียกฟังก์ชัน Scheduler ให้ทำงานทันที 1 รอบ (ไม่ต้องรอ 15 นาที):
  ```bash
  python -c "import asyncio; from dotenv import load_dotenv; load_dotenv(); from app.scheduler_tasks import fetch_tmd_radar_routine; asyncio.run(fetch_tmd_radar_routine())"
  ```
- **Expected Result:**
  - ที่ Terminal จะแสดงข้อความประมาณว่า `Saved radar frame to radar/kkn120/kkn120_17xxxx.gif`
  - เข้าไปที่ Firebase Console > Storage จะเจอโฟลเดอร์ `radar/kkn120/` และมีภาพ `.gif` ถูกอัปโหลดอยู่

---

## Test Case 2: ทดสอบการทำนายฝน (Optical Flow Nowcasting API)
**เป้าหมาย:** เช็คว่า API สามารถคำนวณทิศทางฝนล่วงหน้าได้ 60 นาทีและตอบกลับข้อมูลครบถ้วน

- **Step 1:** เปิด Terminal สตาร์ทเซิร์ฟเวอร์ Backend
  ```bash
  cd backend
  uvicorn app.main:app --reload
  ```
- **Step 2:** เปิด Terminal อีกหน้าต่าง (หรือใช้ Postman) รันคำสั่ง `curl` ด้านล่างนี้ เพื่อจำลองพิกัดใจกลางเมืองขอนแก่น (พิกัด 16.43, 102.83) (ใช้ GET request แทน)
  ```bash
  curl -X GET "http://127.0.0.1:8001/api/v1/weather/compare?lat=16.43&lng=102.83"
  ```
  *(หรือถ้าบอทเชื่อมต่อแล้ว: ลองกดส่ง Location ในแชท Telegram ที่พิกัดแถวๆ ขอนแก่น หรืออุดรธานี)*
- **Expected Result:** API จะตอบกลับมาเป็น JSON แบบนี้
  ```json
  {
    "tmd-radar": {
      "predictions": [
        { "time_offset": 0, "intensity": "ไม่มีฝน", "dbz": 0.0 },
        { "time_offset": 15, "intensity": "ไม่มีฝน", "dbz": 0.0 },
        { "time_offset": 30, "intensity": "ไม่มีฝน", "dbz": 0.0 },
        { "time_offset": 45, "intensity": "ไม่มีฝน", "dbz": 0.0 },
        { "time_offset": 60, "intensity": "ไม่มีฝน", "dbz": 0.0 }
      ],
      "intensity": "ไม่มีฝน",
      "max_rain": 0.0,
      "duration_minutes": 0,
      "wind_speed_kmh": 0.1,
      "endpoint": "tmd-radar",
      "accuracy_score": 1.0
    }
  }
  ```
  *(ถ้าพื้นที่นั้นมีฝน ค่า intensity, dbz, และ wind_speed_kmh จะมีตัวเลขเพิ่มขึ้น และ predictions จะทายล่วงหน้าตามทิศทางลม)*

---

## Test Case 3: ทดสอบความแม่นยำของการปักพิกัดและทิศทางลม (Visual Verification)
**เป้าหมาย:** สร้างภาพเรดาร์ที่มีการวาด Overlay หมุดพิกัดเมืองต่างๆ และลูกศรทิศทางลม เพื่อยืนยันว่าโค้ดทำงานได้ตรงสเกลแผนที่จริงทั้งภาพ Static และภาพ Loop

- **Step 1:** ตรวจสอบว่ามีสคริปต์วาดภาพอยู่ที่ `backend/tmp/visualize_radar.py` (ถ้าไม่มี ให้ก็อปปี้สคริปต์มาสร้างไฟล์นี้)
- **Step 2:** เปิด Terminal รันคำสั่งนี้เพื่อประมวลผลรูปภาพ:
  ```bash
  backend/venv/bin/python backend/tmp/visualize_radar.py
  ```
- **Expected Result:**
  - จะมีไฟล์รูปภาพ 2 ไฟล์ถูกสร้างขึ้นมาในโฟลเดอร์ `backend/tmp/`
    1. **`radar_verification_static.png`**: ภาพนิ่ง 800x800 พิสูจน์การปักหมุดพิกัดศูนย์กลางเมือง
    2. **`radar_verification_animated.gif`**: ภาพเคลื่อนไหว 680x680 พิสูจน์การปักพิกัดและลูกศรสีเขียวที่ชี้ทิศทางการเคลื่อนที่ของฝน
  - เมื่อเปิดไฟล์ทั้งสองขึ้นมา จะต้องเห็น **"จุดสีแดง"** มาร์กพิกัดเมือง ขอนแก่น, อุดรธานี, โคราช ได้อย่างแม่นยำ (ตรงกับเส้นขอบจังหวัด)
  - ในไฟล์ GIF จะเห็นการทำงานของ **"ลูกศรสีเขียว"** ในบริเวณที่มีเมฆฝน ชี้บอกทิศทางการเคลื่อนที่ตามอัลกอริทึม Optical Flow

> [!NOTE]
> **การสลับโหมดคำนวณพิกัด (Projection Mode)**
> ตอนนี้ระบบรองรับการคำนวณ 2 แบบ ได้แก่:
> 1. `"linear"` (Flat): อาศัย Bounding Box เป็นสี่เหลี่ยมจัตุรัส เหมาะสมในระดับพื้นฐาน
> 2. `"azimuthal"` (Curvature): คำนวณความโค้งของโลกตามสูตร Haversine สำหรับเรดาร์กวาดวงกลม แม่นยำกว่าบริเวณขอบรัศมี
> 
> หากต้องการเปลี่ยนโหมด ให้ไปแก้ไขค่า `projection_type` ในไฟล์ `backend/app/services/tmd_radar_config.py` ได้เลยครับ (ค่าตั้งต้นคือ `"linear"`)

---

## Test Case 4: ทดสอบการทำงานผ่าน Telegram Bot (End-to-End)
**เป้าหมาย:** ทดสอบว่าเมื่อผู้ใช้ส่ง Location ผ่าน Telegram เข้ามา ระบบสามารถนำพิกัดนั้นไป Mapping กับเรดาร์และส่งผลพยากรณ์กลับไปได้อย่างถูกต้อง

- **Step 1:** เปิดใช้งานบอท FonMaYang ใน Telegram ของคุณ
- **Step 2:** กดเมนูหรือกดส่งพิกัด Location ของคุณในหน้าแชท (แนะนำให้ลองปักพิกัดในเขต ขอนแก่น หรือพื้นที่ที่มีฝนตกในเรดาร์)
- **Step 3:** รอรับข้อความตอบกลับจากบอท
- **Expected Result:** 
  - บอทจะตอบกลับด้วยข้อความแจ้งเตือนสภาพอากาศ
  - ตรวจสอบว่าในข้อความระบุว่า `📡 แหล่งข้อมูล: tmd-radar`
  - ตรวจสอบว่าผลการทำนาย (เช่น "ฝนกำลังตก" หรือ "ไม่มีฝน") สอดคล้องกับภาพเรดาร์ที่เห็นในหน้าเว็บกรมอุตุฯ ณ เวลานั้น

---

## Test Case 4: รัน Unit Test ตรวจสอบคณิตศาสตร์
**เป้าหมาย:** ตรวจสอบว่าสมการ Optical Flow (Lagrangian) และ Affine Mapping ทำงานได้ถูกต้องไม่เพี้ยน

- **Step 1:** เปิด Terminal (cd เข้าไปที่โฟลเดอร์ `backend`)
- **Step 2:** รันคำสั่ง PyTest
  ```bash
  pytest tests/test_tmd_processor.py
  ```
- **Expected Result:** ต้องขึ้นว่าผ่านทั้งหมด (เช่น `7 passed in 0.50s`) แสดงว่าระบบคณิตศาสตร์เบื้องหลังไม่มีอะไรพัง
