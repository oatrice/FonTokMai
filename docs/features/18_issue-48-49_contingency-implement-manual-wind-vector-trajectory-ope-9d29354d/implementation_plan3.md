# Add Tests for API Accuracy Evaluation (Issue 49)

แผนงานนี้มีจุดประสงค์เพื่อเพิ่มเติม Automated Tests ให้ครอบคลุมฟีเจอร์การประเมินความแม่นยำของ API (Evaluation System) ที่เพิ่งถูกพัฒนาเข้าไป เพื่อให้มั่นใจได้ว่าระบบบันทึกความแม่นยำ ทำการคำนวณและดึงข้อมูลเพื่อมาจัดลำดับ (Fallback Order) ได้อย่างถูกต้อง

## Proposed Changes

### Backend Tests

#### [MODIFY] [test_db.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/tests/test_db.py)
เพิ่ม Unit Test สำหรับ `SQLiteLocationRepository` ในการจัดการ Model `ApiReliability`:
- ทดสอบเมธอด `get_all_api_reliability` ให้อ่านค่าคะแนน Default หากไม่มีบันทึกในฐานข้อมูล 
- ทดสอบเมธอด `record_api_query_success` ว่าสามารถอัปเดตค่า `total_queries` และคำนวณ `accuracy_score` ออกมาได้ถูกต้อง
- ทดสอบเมธอด `save_feedback` ว่าเมื่อเซฟ "false_alarm" ระบบจะเพิ่มยอด `false_alarms` ใน `api_reliability` และคำนวณลดคะแนน Accuracy ลงตามสัดส่วนได้อย่างถูกต้อง

#### [MODIFY] [test_firestore.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/tests/test_firestore.py)
เพิ่ม Unit Test สำหรับ `FirestoreLocationRepository` เช่นเดียวกับ SQLite:
- ทดสอบดึงคะแนน Reliability ด้วย Mock Firestore
- ทดสอบบันทึกและคำนวณคะแนนผ่านฟังก์ชัน `save_feedback` และ `record_api_query_success` โดยใช้ Mock Firestore Collections 

#### [MODIFY] [test_webhook.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/tests/test_webhook.py)
อัปเดต/เพิ่มเติม Test ของ Telegram Webhook:
- **Compare API**: อัปเดต `test_telegram_webhook_callback_compare_api` ให้ตรวจสอบด้วยว่าในข้อความตอบกลับมีการรวมค่า `% ความแม่นยำ` ออกมาใน text ตอบกลับ (เพราะเราได้อัปเดตฟีเจอร์ไปก่อนหน้านี้)
- **False Alarm Button**: ปรับปรุง `test_telegram_webhook_callback_false_alarm` ให้ทดสอบกรณีที่ได้รับพารามิเตอร์ของระบบ เช่น `fb_falsealarm_13.0_100.0_t` (Source: Tomorrow.io) ว่ามันได้ถูกส่งต่อไปยัง `save_feedback` ในฐานะ Endpoint ที่ถูกต้อง

## Verification Plan

### Automated Tests
- รัน `pytest -q` ต้องผ่านทั้งหมด
- คำสั่ง: `cd backend && source venv/bin/activate && pytest -q tests/test_db.py tests/test_firestore.py tests/test_webhook.py`
