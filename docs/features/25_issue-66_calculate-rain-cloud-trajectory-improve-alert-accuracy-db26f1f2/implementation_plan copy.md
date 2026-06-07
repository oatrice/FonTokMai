# Unified Radar Cache System (Firestore + Firebase Storage)

## Goal
เพื่อลดปัญหาการดึงข้อมูลจากเว็บกรมอุตุนิยมวิทยา (TMD) ที่เกิดความล่าช้า บล็อก IP หรือทำให้เว็บต้นทางล่มเมื่อมีผู้ใช้งานพร้อมกันจำนวนมาก เราจะเปลี่ยนมาใช้ระบบ "Cache ตรงกลาง" โดยใช้ Firebase Storage เก็บไฟล์ภาพ และใช้ Firestore เก็บ Metadata และทำงานควบคู่กับ Cron Job ทุก 5 นาที

## User Review Required
> [!IMPORTANT]
> **สรุป Flow ใหม่ที่นำเสนอ:**
> 1. เมื่อ Cron ยิงมาที่ `/api/v1/cron/check-rain` (ทุก 5 นาที) ระบบจะทำ **Cache Phase** ก่อน
> 2. **Cache Phase:** ไปดึงภาพ Static และ Loop GIF ล่าสุดจากเว็บ TMD ของสถานีเป้าหมาย
> 3. นำภาพไปโยนเข้า Firebase Storage ทันที
> 4. นำภาพมาทำ OCR หา Timestamp แล้วบันทึก URL ของภาพ + Timestamp ลง **Firestore (`radar_latest_cache`)** 
> 5. **Predict Phase:** หลังจาก Cache เสร็จ ระบบถึงจะลูปหา User เพื่อแจ้งเตือนฝนตก
> 6. ในจังหวะที่คำนวณฝน `TMDRadarProcessor` จะไม่อ่านข้อมูลจาก TMD แล้ว แต่จะดึงภาพจาก Firebase Storage ตาม URL ที่อยู่ใน Firestore แทน
>
> รบกวนพิจารณา Flow นี้ หากอนุมัติ ผมจะเริ่มปรับโครงสร้างโค้ดทันทีครับ

## Proposed Changes

### 1. `backend/app/repositories/firestore.py`
เพิ่มการจัดการ Collection `radar_latest_cache` เพื่อเก็บ Metadata ของแต่ละสถานีเรดาร์ (Station Code)
#### [MODIFY] firestore.py
- เพิ่มฟังก์ชัน `get_latest_radar_cache(station_code: str)` เพื่อดึงข้อมูล Cache ล่าสุดของสถานีนั้นๆ
- เพิ่มฟังก์ชัน `set_latest_radar_cache(station_code: str, static_url: str, loop_url: str, timestamp: int)`

### 2. `backend/app/scheduler_tasks.py`
ควบรวมการทำ Cache ให้เกิดขึ้นก่อนที่ระบบจะลูปเช็คฝนรายคน
#### [MODIFY] scheduler_tasks.py
- อัปเดตฟังก์ชัน `check_rain_and_alert()`:
  - เพิ่ม **Step 1:** วนลูปรายชื่อสถานีที่ต้องใช้ทั้งหมด (เช่น kkn120, kkn240, skn240) ดึงภาพจาก TMD -> อัปโหลดเข้า Firebase Storage -> อ่าน OCR Timestamp -> อัปเดตลง Firestore
  - **Step 2:** ดำเนินการเช็คพิกัด User เหมือนเดิม

### 3. `backend/app/services/tmd_radar_processor.py`
ปรับปรุงให้ Processor พึ่งพา Cache จาก Firestore แทนการขูดเว็บแบบ Real-time
#### [MODIFY] tmd_radar_processor.py
- ปรับ `fetch_latest_image_bytes()` และ `fetch_loop_gif_and_extract_frames()`:
  - ให้ไปเช็ค `radar_latest_cache` ใน Firestore ก่อน
  - ถ้าระยะเวลา Cache ยังสดใหม่ (เช่นไม่เกิน 15 นาที) ให้ดาวน์โหลดภาพจาก Firebase Storage URL แทนการไปที่ `weather.tmd.go.th`
  - หากไม่มี Cache หรือเก่าเกินไป ค่อยใช้ Logic เดิมเป็น Fallback

## Verification Plan

### Automated Tests
- ตรวจสอบ/เพิ่ม Test case ว่า `TMDRadarProcessor` เมื่อมี Cache อยู่ใน Firestore จะดึงข้อมูลจาก Storage จริงๆ (Mock Storage Response)
- ตรวจสอบ `check_rain_and_alert` ว่ามีการเรียกอัปเดต Cache ก่อนทำงานหลัก

### Manual Verification
- ยิง API `/api/v1/cron/check-rain` ผ่าน Postman
- สังเกต Log ว่าระบบดึงภาพจาก TMD -> อัปโหลดเข้า Firebase Storage -> และเก็บลง Firestore ก่อนที่ทำการประเมินสภาพอากาศให้ User
- เช็คว่ารูปภาพในข้อความแจ้งเตือนที่ส่งมาใน Telegram เป็นลิงก์ที่โหลดได้ถูกต้อง และมาจาก Storage ของระบบเราเอง
