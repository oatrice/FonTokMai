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
