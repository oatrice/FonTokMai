# แผนการแก้ไข Issue #21: ย้ายการจัดเก็บข้อมูล Location เป็น Firestore

ปัญหา: ข้อมูลพิกัด (Location) สำหรับแจ้งเตือนผู้ใช้งานจะสูญหายเมื่อ Google Cloud Run ทำการ Cold Start เนื่องจากปัจจุบันระบบบันทึกข้อมูลลงไฟล์ฐานข้อมูล SQLite ท้องถิ่น (`fonmayang.db`) ซึ่งเป็น Ephemeral filesystem บน Cloud Run ข้อมูลในไฟล์จะถูกล้างใหม่เมื่อเกิด Cold Start

เป้าหมาย: ย้ายระบบการจัดเก็บข้อมูล Location จาก SQLite เป็น Firestore (Google Cloud Firestore) ตามที่มีเตรียม Repository โครงสร้างไว้แล้ว เพื่อให้ข้อมูลคงอยู่ถาวรแม้ Cloud Run จะ restart

## User Review Required
> [!IMPORTANT]
> ระบบต้องการให้โปรเจกต์ Google Cloud เปิดใช้งาน **Cloud Firestore API** และมีฐานข้อมูล Firestore สร้างไว้ในโหมด Native เรียบร้อยแล้ว นอกจากนี้ Service Account ที่ใช้รัน Cloud Run จำเป็นต้องมีสิทธิ์ **Cloud Datastore User** (`roles/datastore.user`) รบกวนผู้ใช้ยืนยันว่าโปรเจกต์ใน GCP ได้เปิดใช้งานและให้สิทธิ์เรียบร้อยแล้ว

> [!WARNING]
> จะมีการเพิ่ม Environment variable `STORAGE_BACKEND=firestore` ในไฟล์ `.gitlab-ci.yml` ของขั้นตอน Deploy เพื่อให้แอพบน Cloud Run เปลี่ยนไปใช้ Firestore อย่างถาวร ข้อมูลพิกัดเก่า ๆ ที่อาจจะหลงเหลืออยู่ใน SQLite บน Cloud Run จะไม่ถูกย้ายมา (จะเริ่มระบบเปล่าใหม่)

## Open Questions
- การจำลอง Firebase ในฝั่ง Test (Mock) เนื่องจากเราจะใช้ TDD, ผมจะ Mock ตัว `firestore_async.client()` ด้วย `AsyncMock` ใน `test_firestore.py` เพื่อให้ครอบคลุม Use case ทั้งหมด ผู้ใช้มีประเด็นอะไรเพิ่มเติมสำหรับการเขียน Mock ไหมครับ?

## Proposed Changes

### backend/tests

#### [NEW] [test_firestore.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/tests/test_firestore.py)
- เพิ่ม Test suites เพื่อจำลอง `firestore_async` และทดสอบฟังก์ชัน `FirestoreLocationRepository` แบบ TDD (Red -> Green -> Refactor)
- ทดสอบทั้ง `get_location`, `save_location` (พร้อมคำนวณวันหมดอายุ), `get_active_locations` (ตรวจสอบเงื่อนไข `expires_at`), `update_last_alerted` และ `delete_location`

### backend/app/repositories

#### [MODIFY] [firestore.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/firestore.py)
- Implement โค้ดทั้งหมดที่ยังค้างไว้ (Stub) ให้ทำงานเชื่อมต่อกับ Firestore ได้จริง:
  - `save_location`: บันทึกข้อมูลและเพิ่มการคำนวณวันหมดอายุ `expires_at` (บวกไปอีก 60 วัน) สำหรับประเภทการจดจำแบบสองเดือน
  - `get_active_locations`: Query ดึงพิกัดที่ยังไม่หมดอายุ
  - `update_last_alerted`: อัปเดตฟิลด์ `last_alerted_at` บน document ที่กำหนด
  - `delete_location`: ลบ document ออกจาก collection ตาม `chat_id`

### CI/CD

#### [MODIFY] [.gitlab-ci.yml](file:///Users/oatrice/Software-projects/FonMaYang/.gitlab-ci.yml)
- ใน Stage `deploy_cloud_run` ให้เพิ่ม `--set-env-vars STORAGE_BACKEND=firestore` ต่อท้ายคำสั่ง deploy `gcloud run deploy`

## Verification Plan

### Automated Tests
- รันคำสั่ง `cd backend && pytest tests/test_firestore.py -v` เพื่อให้แน่ใจว่า logic Firestore ทำงานถูกต้อง.
- รันคำสั่ง `cd backend && pytest tests/ -v` เพื่อให้แน่ใจว่าไม่มีผลกระทบกับส่วนอื่นของระบบ.

### Manual Verification
- หลังจาก Deploy ผู้ใช้สามารถลองส่ง Location ให้บอท จากนั้นบังคับให้ Cloud Run รีสตาร์ทด้วยการ Deploy ใหม่ (หรือยิงคำสั่ง kill container) แล้วเช็คด้วย `/mylocation` อีกครั้งว่าบอทยังจำพิกัดได้
