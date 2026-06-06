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
