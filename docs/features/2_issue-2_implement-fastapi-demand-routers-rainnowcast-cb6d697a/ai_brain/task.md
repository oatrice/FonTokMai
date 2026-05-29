# Tasks: Issue #9

- [x] เพิ่ม Endpoint POST `/api/events` ใน `api/server.py`
  - [x] เขียน Test ที่ล้มเหลว (RED) สำหรับการส่ง POST request ไปที่ `/api/events`
  - [x] เพิ่มโค้ดจริง (GREEN) เพื่อให้ Endpoint สามารถรับ payload และส่งต่อให้ `process_raw_event`
  - [x] ปรับปรุงและ Refactor โค้ด (REFACTOR)
- [x] สร้างโครงสร้างสคริปต์ World of Warships Mod
  - [x] สร้างโฟลเดอร์ `wows_mod/`
  - [x] สร้างไฟล์ `CastBuddyMod.py` ด้วยโค้ด Python 2.7 compatible สำหรับส่ง Webhook
- [x] จัดเตรียมคู่มือ/ขั้นตอน (Walkthrough) สำหรับการใช้งานและการติดตั้ง Mod
