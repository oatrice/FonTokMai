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
