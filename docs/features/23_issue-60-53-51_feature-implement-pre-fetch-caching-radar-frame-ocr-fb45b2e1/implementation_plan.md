# [Implementation Plan] Batch Issues 60, 53, 51

ดำเนินการออกแบบแผนผังรวมสำหรับกลุ่มงาน (Batch) ถัดไปที่มุ่งเน้นความแม่นยำของข้อมูลและทางเลือกของ User ประกอบด้วย:
1. **Issue 60:** ทำ OCR แบบ Pre-fetch และ Cache ลง Firestore เพื่อระบุ Timestamp รายเฟรมภาพ
2. **Issue 53:** เพิ่ม TMD Radar เข้าไปในฟีเจอร์ Compare API บน Telegram
3. **Issue 51:** ให้ User สามารถระบุบังคับ Source ข้อมูลอากาศได้ (เช่น `/rain tmd-radar`)

---

## User Review Required

> [!WARNING]
> **Issue 60 (OCR):** การติดตั้ง Tesseract OCR จะต้องมีการแก้ไข `Dockerfile` ซึ่งอาจทำให้ Image Size ใหญ่ขึ้นเล็กน้อย หากทดสอบรันบน Mac ของคุณโอ๊ตอาจจะต้องทำการ `brew install tesseract` เพิ่มเติมไว้ด้วยครับ เพื่อให้รัน/เทสแบบ Local ผ่าน
> **Issue 53 (Compare API):** โค้ดที่มีอยู่ใน `weather_manager.py` (บรรทัด 139) มีการเรียก `tmd-radar` อยู่แล้ว แต่สาเหตุที่มันอาจไม่โชว์ใน Telegram อาจเป็นเพราะรูปแบบ Key ที่รับส่งไม่ตรงกัน ผมจะไปปรับให้มันโชว์ข้อมูลได้สม่ำเสมอกับ API ตัวอื่นๆ ครับ

## Open Questions

> [!IMPORTANT]
> **การ Force API (Issue 51):** อยากให้บอทรองรับรูปแบบคำสั่ง `/rain <provider>` เช่น `/rain xweather` หรือ `/rain tmd-radar` เลยใช่ไหมครับ? หรืออยากให้ส่ง `/rain` เฉยๆ แล้วมีปุ่ม Inline Keyboard เด้งขึ้นมาให้กดเลือก Provider ครับ? (ผมเสนอว่าทำเป็น Command Param `/<command> <provider>` ควบคู่กับการกดผ่าน Inline Keyboard เพื่อความยืดหยุ่น)

---

## Proposed Changes

### 1. OCR & Firestore Caching (Issue 60)

#### [MODIFY] [requirements.txt](file:///Users/oatrice/Software-projects/FonMaYang/backend/requirements.txt)
- เพิ่ม package `pytesseract` สำหรับการอ่านตัวอักษรบนภาพเรดาร์

#### [MODIFY] [Dockerfile](file:///Users/oatrice/Software-projects/FonMaYang/backend/Dockerfile)
- เพิ่มคำสั่ง `RUN apt-get update && apt-get install -y tesseract-ocr` เพื่อติดตั้งระบบ OCR ให้ใช้งานบน Cloud Run ได้

#### [NEW] [ocr_service.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/ocr_service.py)
- สร้าง Service สำหรับจัดการ Tesseract โดยการตัด Crop บริเวณ "ด้านล่าง" ของเฟรมภาพเรดาร์ซึ่งมีตัวหนังสือ Timestamp ฝังอยู่ แล้วทำ Image Pre-processing (Grayscale, Thresholding) ก่อนเข้าสู่ Tesseract OCR

#### [MODIFY] [firestore.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/firestore.py)
- เพิ่ม Method สำหรับ Cache: `get_radar_timestamp_cache(frame_hash: str)` และ `set_radar_timestamp_cache(frame_hash: str, timestamp: int)` เพื่อที่เวลาดึงเฟรมเดิม ไม่ต้องคำนวณ OCR ซ้ำให้เปลือง CPU

#### [MODIFY] [tmd_radar_processor.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/tmd_radar_processor.py)
- อัปเดต `fetch_loop_gif_and_extract_frames()` แทนที่จะอาศัย Last-Modified จะทำการวนลูปแยกเฟรม -> คำนวณ Hash ของแต่ละเฟรม -> เช็ค Firestore Cache -> ถ้าไม่มีให้สั่ง OCR -> ได้ Timestamp รายเฟรมที่แม่นยำ -> จัดเก็บ Cache

---

### 2. Force Weather Data Source (Issue 51)

#### [MODIFY] [webhook.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/webhook.py)
- จับข้อความ `/rain` และเช็ค arguments ต่อยอด (เช่น `/rain tomorrow`, `/rain tmd`) 
- เพิ่มปุ่มลัด Inline Keyboard ใต้ข้อความตอนดึง Compare API เพื่อให้คนสามารถกดบังคับใช้ API นั้นในครั้งถัดไปได้อย่างรวดเร็ว

#### [MODIFY] [weather_manager.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/weather_manager.py)
- เพิ่มพารามิเตอร์ `force_provider: str = None` ลงในเมธอดหลัก `get_weather_with_fallback()`
- หากมีการระบุ `force_provider` จะทำการเรียก Provider นั้นทันที โดยข้ามกระบวนการ Fallback Chain เดิม

---

### 3. Compare API Integration (Issue 53)

#### [MODIFY] [tmd_radar_processor.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/tmd_radar_processor.py)
- ตรวจสอบ `_get_tmd_prediction()` ให้แน่ใจว่าได้ Return Key มาตรฐาน ได้แก่ `max_rain`, `intensity`, `duration_minutes`, `predictions` เพื่อให้เข้ากันได้กับระบบ Compare API formatter ใน Telegram 

#### [MODIFY] [webhook.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/webhook.py)
- หากข้อมูลที่ Return จาก TMD เป็นภาพเรดาร์ ให้เพิ่มเงื่อนไขรองรับและแปลงเป็น Text พยากรณ์แทน เพราะในโหมดเปรียบเทียบ 4 API พร้อมกัน (Compare API) เราจะเน้นที่ Data Text ล้วนๆ

---

## Verification Plan

### Automated Tests
- `pytest tests/test_ocr_service.py` (สร้างใหม่เพื่อเทสการสกัดข้อความและการแคช)
- `pytest tests/test_tmd_processor.py` (รันของเดิมที่แก้ไขใหม่ เพื่อเทสว่าการแกะเฟรมได้ Timestamp ครบทุกอัน)
- `pytest tests/test_webhook.py` (เช็คการ Parse ข้อความ `/rain <provider>`)

### Manual Verification
- รันบอทและพิมพ์สั่ง `/rain tmd-radar` เพื่อทดสอบ Force Provider
- รันบอทด้วยพิกัดสถานที่ แล้วกดปุ่ม "📊 เทียบข้อมูล" เพื่อเช็คดูว่ามีของ TMD Radar โชว์ควบคู่กับ 3 เจ้าแรกแล้วหรือไม่
- ลองเปิดดู Firestore ว่ามี Collection ใหม่ `radar_frame_cache` ถูกสร้างขึ้นและมีข้อมูล Hash หรือไม่
