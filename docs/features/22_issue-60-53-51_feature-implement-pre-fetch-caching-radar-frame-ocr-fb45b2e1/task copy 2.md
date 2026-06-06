# Cloud Vision Rate Limiting

- `[x]` สร้างการรองรับการจำกัดโควต้าใน Firestore
  - `[x]` เขียนเทสต์สำหรับเมธอด `check_and_increment_vision_quota` (Red)
  - `[x]` สร้างเมธอด `check_and_increment_vision_quota` ใน `firestore.py` (Green)
- `[x]` เชื่อมต่อ Rate Limiter ใน `ocr_service.py`
  - `[x]` อัปเดตเทสต์ OCR Service ให้ครอบคลุมกรณีโควต้าเต็ม
  - `[x]` อัปเดต `get_frame_timestamp` ให้เช็คโควต้าก่อนรัน Cloud Vision
- `[ ]` ทดสอบการทำงานจริงด้วยสคริปต์
- `[ ]` อัปเดตเอกสารสรุปผล (Walkthrough)
