# สรุปผลการทำงาน Issue #21: ย้ายระบบไปใช้ Firestore

ปัญหาที่พบคือข้อมูลพิกัดการแจ้งเตือนของผู้ใช้สูญหายเมื่อ Google Cloud Run ทำการ Cold Start เนื่องจากไฟล์ฐานข้อมูล SQLite จะถูกรีเซ็ต. งานนี้จึงทำการสลับให้ไปบันทึกข้อมูลในฐานข้อมูล **Google Cloud Firestore** แทนเมื่อรันอยู่บน Cloud Run.

## สิ่งที่ได้ดำเนินการ (Changes Made)

1. **การเขียนแบบ Test-Driven Development (TDD)**
   - สร้างไฟล์ [test_firestore.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/tests/test_firestore.py) เพื่อจำลอง `firebase_admin` และ `firestore_async`
   - เขียน Failing Test (Red) จำนวน 7 กรณี เช่น การทดสอบ `get_location`, `save_location`, `get_active_locations` (แบบกรองวันหมดอายุ), การลบข้อมูล ฯลฯ

2. **การพัฒนาระบบฐานข้อมูล Firestore**
   - แก้ไขไฟล์ [firestore.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/firestore.py) โดยปรับปรุง `FirestoreLocationRepository` ที่มีแค่ Stub เอาไว้ ให้สามารถทำงานได้จริงทั้งหมด
   - ปรับปรุงการคำนวณวันหมดอายุ `expires_at` สำหรับตัวเลือกการบันทึกแบบสองเดือน (`TWO_MONTHS`) โดยบวกไปอีก 60 วัน และจัดการข้อมูลให้อยู่ในรูปแบบ Native Datetime เพื่อบันทึกลง Firestore

3. **การทดสอบความถูกต้อง (Validation)**
   - รัน Test เฉพาะ Firestore แล้วผลลัพธ์ผ่านทั้งหมด (Green Phase)
   - รัน Unit Test ของทั้งโปรเจกต์ `pytest tests/` ทั้งหมด 31 เคส พบว่าผ่านทุกกรณี (100% Passed) ระบบเดิมไม่ได้รับผลกระทบ

4. **การปรับปรุงระบบ CI/CD**
   - อัปเดตไฟล์ [.gitlab-ci.yml](file:///Users/oatrice/Software-projects/FonMaYang/.gitlab-ci.yml) เพื่อเพิ่ม Environment Variable `STORAGE_BACKEND=firestore` ส่งให้ตอนสั่ง `gcloud run deploy` 

> [!NOTE]
> ระบบพร้อมสำหรับการรีวิวและ Merge เข้า `main` เรียบร้อยแล้ว หากมีการ Deploy ครั้งถัดไป Cloud Run จะใช้ฐานข้อมูลจาก Firestore โดยอัตโนมัติ ข้อมูลเก่า ๆ ใน SQLite บน Cloud Run (หากมี) จะไม่ถูกดึงมาด้วยเนื่องจากเป็นการเริ่มใช้ฐานข้อมูลแหล่งใหม่.
