# Cloud Vision Rate Limiting

- `[x]` สร้างการรองรับการจำกัดโควต้าใน Firestore
  - `[x]` เขียนเทสต์สำหรับเมธอด `check_and_increment_vision_quota` (Red)
  - `[x]` สร้างเมธอด `check_and_increment_vision_quota` ใน `firestore.py` (Green)
- `[x]` เชื่อมต่อ Rate Limiter ใน `ocr_service.py`
  - `[x]` อัปเดตเทสต์ OCR Service ให้ครอบคลุมกรณีโควต้าเต็ม
  - `[x]` อัปเดต `get_frame_timestamp` ให้เช็คโควต้าก่อนรัน Cloud Vision
- `[ ]` ทดสอบการทำงานจริงด้วยสคริปต์
- `[ ]` อัปเดตเอกสารสรุปผล (Walkthrough)
# Task List: OCR Fallback Chain Implementation

- `[x]` 1. ปรับปรุง Dependencies และไฟล์ Configuration
  - `[x]` ลบ `pytesseract` และเพิ่ม `google-cloud-vision`, `google-generativeai` ใน `requirements.txt`
  - `[x]` ลบคำสั่งติดตั้ง `tesseract-ocr` ใน `Dockerfile`
  - `[x]` เพิ่มตัวแปร `GEMINI_API_KEY` และ `OCR_SPACE_API_KEY` ใน `.env.example`
- `[x]` 2. ปรับปรุง `ocr_service.py`
  - `[x]` สร้างฟังก์ชันช่วยเหลือสำหรับแปลงภาพ Numpy เป็น PNG Bytes
  - `[x]` สร้าง HTTP Client / API Client สำหรับ Google Cloud Vision, Gemini 1.5 Flash, และ OCR.space
  - `[x]` สร้าง Fallback Chain ใน `get_frame_timestamp`
- `[x]` 3. ปรับปรุงและรัน Unit Tests
  - `[x]` แก้ไข `tests/test_ocr_service.py` เพื่อ Mock การเรียก API ทั้ง 3 ตัว
  - `[x]` ทดสอบกรณีที่ 1 พัง แล้ว 2 ทำงานต่อ (Fallback)
  - `[x]` ทดสอบกรณีพังทั้งหมด และใช้ `fallback_ts`
  - `[x]` รันคำสั่ง `pytest` ในสภาพแวดล้อมจำลอง
# Task List: Batch Issues 60, 53, 51

- `[x]` **Issue 60: OCR & Firestore Caching**
  - `[x]` เพิ่ม `pytesseract` ใน `requirements.txt`
  - `[x]` แก้ไข `Dockerfile` ให้ติดตั้ง `tesseract-ocr`
  - `[x]` สร้าง `app/services/ocr_service.py` สำหรับสกัด Timestamp ด้วย Tesseract
  - `[x]` เพิ่ม `get_radar_timestamp_cache` และ `set_radar_timestamp_cache` ใน `app/repositories/firestore.py`
  - `[x]` เรียกใช้งาน `ocr_service` ใน `tmd_radar_processor.py` แทนการดึงจาก HTML

- `[x]` **Issue 51: Force Weather Data Source**
  - `[x]` อัปเดต `get_weather_with_fallback` ใน `weather_manager.py` ให้รับ `force_provider`
  - `[x]` เพิ่มการจับคำสั่ง `/rain <provider>` ใน `webhook.py`
  - `[x]` เพิ่ม Inline Keyboard ปุ่มเลือกระบุ Provider ตอนกด Compare API

- `[x]` **Issue 53: Compare API Integration**
  - `[x]` จัด Format Response ของ `_get_tmd_prediction()` ให้มี `predictions` และรองรับ Compare API
  - `[x]` ปรับแก้ `webhook.py` ในส่วน `compare_api_` ให้พ่น Text ออกมาได้โดยไม่ติดบัค Image

- `[ ]` **Verification & Deployment**
  - `[ ]` สร้าง/อัปเดต Unit Tests (`test_ocr_service.py`, `test_webhook.py`)
  - `[ ]` ตรวจสอบและ Commit งาน
  - `[ ]` สร้าง Walkthrough Document
