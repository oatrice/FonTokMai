# แผนการสร้าง Rate Limit สำหรับ Cloud Vision

เป้าหมายคือการป้องกันไม่ให้มีการเรียกใช้งาน Cloud Vision API เกินโควต้าฟรี (1,000 ครั้งต่อเดือน) เมื่อถึงขีดจำกัดแล้ว ระบบจะตัดไปใช้ Gemini หรือ OCR.space โดยอัตโนมัติเพื่อป้องกันค่าใช้จ่ายที่อาจเกิดขึ้น

## Proposed Changes

### `backend/app/repositories/firestore.py`
เพิ่มระบบนับโควต้ารายเดือนใน Firestore
#### [MODIFY] `firestore.py`
*   เพิ่ม Method `check_and_increment_vision_quota(limit: int = 1000) -> bool`
*   ใช้ Collection ชื่อ `api_quotas` และ Document ID เป็นเดือนปัจจุบัน (เช่น `vision_2026-06`)
*   ดึงค่าปัจจุบันมาตรวจเช็ค ถ้ายังไม่เกินโควต้า จะส่งคำสั่ง `firestore.Increment(1)` เข้าไปและ Return `True` (อนุญาตให้รัน)
*   ถ้าเกินโควต้า จะ Return `False` (ไม่อนุญาตให้รัน)

### `backend/app/services/ocr_service.py`
แก้ไข Flow การเรียกใช้ OCR ให้เช็คโควต้าก่อน
#### [MODIFY] `ocr_service.py`
*   ดึงเดือนปัจจุบันในรูปแบบ `YYYY-MM`
*   ก่อนเริ่ม `_call_cloud_vision` ให้เรียก `await self.repo.check_and_increment_vision_quota(1000)`
*   ถ้าฟังก์ชันคืนค่า `False` หมายถึงโควต้าเต็มแล้ว ให้ข้าม Cloud Vision ไปเริ่มทำงานที่ Gemini เลย
*   ถ้าคืนค่า `True` ก็รัน Cloud Vision ตามปกติ

## Verification Plan
1. เขียน Unit Test ใน `test_ocr_service.py` หรือสร้างสคริปต์จำลองเพื่อรันเกิน 1,000 ครั้ง
2. (หรือ) ทดสอบโดยการปรับลิมิตลงชั่วคราว เช่น `limit=2` เพื่อตรวจสอบว่าพอถึงครั้งที่ 3 ระบบข้ามไปเรียก Gemini แทนจริงๆ
3. ตรวจสอบใน Firestore Console หรือผ่านสคริปต์ว่า Document `api_quotas/vision_YYYY-MM` ถูกสร้างขึ้นและตัวเลขเพิ่มขึ้นจริง

> [!IMPORTANT]
> หากเห็นด้วยกับแนวทางนี้ คุณสามารถอนุมัติให้ผมลงมือเขียนโค้ดได้เลยครับ!
# แผนการปรับปรุง OCR ด้วย Fallback Chain (Cloud Vision -> Gemini -> OCR.space)

ปัญหาที่พบคือ Tesseract OCR ไม่สามารถอ่านค่า Timestamp จากรูปภาพเรดาร์ของ TMD ได้อย่างแม่นยำ เนื่องจากตัวหนังสือมีขนาดเล็กและพื้นหลังมีความซับซ้อน ผู้ใช้จึงต้องการเปลี่ยนไปใช้ API ที่มีความสามารถในการทำ OCR สูงกว่า โดยจัดทำเป็นระบบ Fallback Chain ตามลำดับ

## User Review Required

> [!IMPORTANT]  
> 1. คุณจำเป็นต้องเพิ่ม API Key 2 ตัวในไฟล์ `.env` ของคุณ:
>    - `GEMINI_API_KEY` (สำหรับ Gemini 1.5 Flash)
>    - `OCR_SPACE_API_KEY` (ฟรี สมัครได้ที่ ocr.space)
> 2. สำหรับ **Google Cloud Vision** จะใช้ Credential เดียวกับ Firestore ที่ระบบใช้อยู่แล้ว (ผ่าน `GOOGLE_APPLICATION_CREDENTIALS`) โปรดตรวจสอบว่า Service Account มีสิทธิ์เข้าถึง Cloud Vision API 
> 3. จะมีการถอด `tesseract-ocr` ออกจาก `Dockerfile` เพื่อลดขนาดของ Image
> คุณเห็นด้วยกับแผนการและพร้อมที่จะเตรียม API Key เหล่านี้หรือไม่ครับ?

## Proposed Changes

### 1. Dependencies & Dockerfile

จะทำการอัปเดตไฟล์คอนฟิกต่างๆ เพื่อถอด Tesseract ออกและเพิ่ม Library ที่จำเป็น

#### [MODIFY] [requirements.txt](file:///Users/oatrice/Software-projects/FonMaYang/backend/requirements.txt)
- ลบ `pytesseract`
- เพิ่ม `google-cloud-vision`
- เพิ่ม `google-generativeai`

#### [MODIFY] [Dockerfile](file:///Users/oatrice/Software-projects/FonMaYang/backend/Dockerfile)
- ลบคำสั่ง `RUN apt-get update && apt-get install -y tesseract-ocr` ออกเพื่อลดขนาด Image 

#### [MODIFY] [.env.example](file:///Users/oatrice/Software-projects/FonMaYang/backend/.env.example)
- เพิ่ม `GEMINI_API_KEY=`
- เพิ่ม `OCR_SPACE_API_KEY=`

---

### 2. OCR Service 

เราจะปรับปรุง Logic ในคลาส `OCRService` ให้รองรับการเรียก API ภายนอกทั้ง 3 ตัวตามลำดับ 

#### [MODIFY] [ocr_service.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/ocr_service.py)
- เปลี่ยนกระบวนการ Pre-process ภาพ: แทนที่จะแปลงเป็นขาวดำ จะแปลง `numpy array` (RGB) ให้เป็นข้อมูล Byte ของไฟล์ `.png` เพื่อส่งให้ API แทน
- สร้างเมธอดสำหรับเรียก API แยกกัน:
  - `_call_cloud_vision(image_bytes)`
  - `_call_gemini(image_bytes)`
  - `_call_ocr_space(image_bytes)`
- ปรับโครงสร้างเมธอด `get_frame_timestamp` เพื่อให้ทำ **Fallback Chain**:
  1. ลองเรียก Cloud Vision ก่อน หากสำเร็จและพบ Timestamp ให้ส่งค่ากลับ 
  2. หากล้มเหลว (หรือหา Timestamp ไม่เจอ) ให้ลองเรียก Gemini 1.5 Flash
  3. หากยังล้มเหลวอีก ให้ลองเรียก OCR.space
  4. หากล้มเหลวทั้งหมด ให้ดึง `fallback_ts` (เวลาจาก Header หรือปัจจุบัน) มาใช้
- ระบบ Regex ดึงเวลาจากข้อความ (`_extract_timestamp_from_text`) จะยังคงเก็บไว้เพื่อนำข้อความที่ได้จาก API มาหาวันที่และเวลา 

---

### 3. Tests

ปรับปรุง Unit Test เพื่อให้สอดคล้องกับการเรียกผ่าน API แทน Tesseract

#### [MODIFY] [test_ocr_service.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/tests/test_ocr_service.py)
- ลบ Test สำหรับ `_preprocess_image` (แบบเก่า)
- ปรับปรุง Mock สำหรับการทดสอบ Fallback Chain เพื่อให้มั่นใจว่าเมื่อ Cloud Vision คืนค่าเปล่า มันจะทำการเรียก Gemini ถัดไป

## Verification Plan

### Automated Tests
- รันคำสั่ง `pytest tests/test_ocr_service.py` เพื่อตรวจสอบ Logic ของการทำ Fallback Chain ว่าข้ามไปยัง Provider ถัดไปถูกต้องเมื่ออันแรกพังหรือไม่

### Manual Verification
1. เพิ่ม API Key ลงใน `.env` ท้องถิ่น
2. รันสคริปต์เพื่อตรวจสอบว่าระบบสามารถดึงเวลาจาก TMD Radar ได้ถูกต้องผ่าน Vision API (หรือ API ลำดับถัดๆ ไป)
3. ตรวจสอบว่าใน Firestore (Collection `radar_frame_cache`) มีเอกสารข้อมูลถูกบันทึกพร้อมค่า timestamp ที่ถูกต้อง
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
