# Cloud Vision Rate Limiting

ระบบจำกัดโควต้าการใช้งาน API สำหรับ Cloud Vision ถูกพัฒนาเสร็จสมบูรณ์แล้ว เพื่อป้องกันค่าใช้จ่ายส่วนเกิน (เกิน 1,000 ครั้ง/เดือน) โดยใช้เทคนิคการบันทึกตัวเลขลงใน Firestore

## 📝 รายละเอียดการเปลี่ยนแปลง
- **เพิ่มระบบนับโควต้า (`firestore.py`)** 
  เพิ่ม Method `check_and_increment_vision_quota(limit)` ที่จะเช็คและบวกเลขขึ้น 1 หากเรียกใช้งานต่อเดือนยังไม่เกิน Limit โดยบันทึกลงใน Firestore Collection `api_quotas` (Document เช่น `vision_2026-06`)
- **เชื่อมต่อโควต้าเข้ากับเซอร์วิสหลัก (`ocr_service.py`)**
  ระบบจะเช็คโควต้าก่อนที่จะเรียก `_call_cloud_vision()` หากพบว่าโควต้าเกินแล้ว จะทำการ Fallback ไปใช้ `Gemini 2.5 Flash` อัตโนมัติในทันที
- **เพิ่ม Automated Tests (`test_firestore.py`, `test_ocr_service.py`)**
  ครอบคลุมกรณีโควต้ายังไม่เต็ม (ถูกเรียกใช้และบวกเลข) และกรณีโควต้าเต็ม (ไม่ถูกเรียกใช้ ข้ามไป Gemini สำเร็จ)

## 🎯 Verification (การตรวจสอบ)
- ✅ Unit Tests ผ่านหมดทั้ง 12 เคสใน `test_firestore.py`
- ✅ Unit Tests ผ่านหมดทั้ง 7 เคสใน `test_ocr_service.py` 
- ✅ โครงสร้างเป็นไปตาม TDD (Red -> Green -> Refactor)
  
> [!NOTE]
> ฟีเจอร์นี้จะช่วยรักษาต้นทุนของโปรเจกต์ให้อยู่ในกรอบ Free Tier ตลอดเวลา โดยไม่มีความเสี่ยงเรื่องบิล Google Cloud โผล่ขึ้นมาอย่างไม่ตั้งใจ
