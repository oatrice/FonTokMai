# การสรุปการแก้ไข: รองรับพิกัดหลายตำแหน่งต่อผู้ใช้งาน (Issue #9)

## 📌 ภาพรวมของการเปลี่ยนแปลง (Overview)
เราได้ทำการเพิ่มความสามารถให้บอทสามารถจำตำแหน่งพิกัดได้มากกว่าหนึ่งแห่งต่อผู้ใช้หนึ่งคน โดยให้ผู้ใช้สามารถกำหนดชื่อประเภทของตำแหน่งได้ เช่น **บ้าน**, **ที่ทำงาน**, หรือ **ทั่วไป** จากเดิมที่แต่ละคนสามารถเก็บได้แค่ตำแหน่งเดียวเท่านั้น ทั้งหมดนี้ทำภายใต้ข้อกำหนดการเขียนโค้ดแบบ TDD อย่างเคร่งครัด

## 📝 ไฟล์ที่แก้ไข (Changes Made)
- [models.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/models.py): ลบ `unique=True` ในฟิลด์ `chat_id` ของตาราง `UserLocation` และเพิ่มฟิลด์ `name`
- [base.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/base.py): ปรับแก้ Interface ให้เมธอดส่วนใหญ่รับพารามิเตอร์ `name`
- [sqlite.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/sqlite.py) และ [firestore.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/firestore.py): ปรับแก้ Repository Implementation ให้รองรับการค้นหาและบันทึกข้อมูลแบบมี Composite key (`chat_id` และ `name`)
- [webhook.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/webhook.py): 
  - เพิ่ม UI ของ Inline Keyboard เมื่อผู้ใช้ส่งพิกัดมาใหม่ ให้สามารถเลือกปุ่มเป็น บ้าน, ที่ทำงาน, หรือทั่วไป พร้อมระยะเวลา (2 เดือน / ตลอดไป)
  - รองรับ Callback Query Format ใหม่ `loc_save_<name>_<retention>_<lat>_<lng>`
  - ปรับปรุงการตอบกลับคำสั่ง `/mylocation` ให้แสดงรายการสถานที่ทั้งหมดที่บันทึกไว้ พร้อมปุ่มลบแยกตามสถานที่
- [scheduler_tasks.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/scheduler_tasks.py): 
  - ปรับข้อความตอนแจ้งเตือนฝนตกให้ระบุด้วยว่าเป็นฝนกำลังตกที่พิกัดไหน (เช่น "ที่พิกัด 'บ้าน' ของคุณ")

## 🧪 การทดสอบ (Testing)
ทำการแก้ Test ทั้งหมดตามวงจร Red -> Green -> Refactor ซึ่งรวมถึงการแก้ไข `test_firestore.py`, `test_db.py`, `test_webhook.py` และ `test_scheduler.py` ปัจจุบัน Test ทั้ง 32 ตัวรันผ่านสมบูรณ์ 100%

> [!TIP]
> ฐานข้อมูล (Firestore และ SQLite) ตอนนี้พร้อมรองรับความสามารถการเพิ่มสถานที่ได้อย่างยืดหยุ่นในอนาคต หากต้องการเพิ่มประเภทสถานที่ใหม่ สามารถแก้ไข UI ใน `webhook.py` ได้ทันที

## ✅ ผลลัพธ์การตรวจสอบ (Validation)
- รันคำสั่ง `pytest backend/tests/`
- **สถานะ:** 32 passed in 0.69s (Success)
