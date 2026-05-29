# เป้าหมายโปรเจกต์ (FonMaYang)

ระบบพยากรณ์ฝนล่วงหน้า (Nowcasting) แบบ Privacy-first อาศัยการวิเคราะห์ภาพเรดาร์กรมอุตุนิยมวิทยา (สถานีสกลนครเป็นหลักตามที่ระบุ) ย้อนหลัง 60 นาที ระบบจะแจ้งเตือนล่วงหน้า 15-30 นาทีผ่าน Line OA และ Telegram โดยไม่มีการเก็บตำแหน่งพื้นหลังอย่างต่อเนื่อง

## User Review Required
> [!IMPORTANT]
> **การออกแบบ Privacy-first:** ผู้ใช้จะต้องกดยืนยันการแชร์พิกัดในขณะนั้น (หรือผ่าน Rich Menu ของ LINE) เพื่อตรวจสอบพิกัด โปรดพิจารณาความลื่นไหลของ User Experience (UX) ในส่วนนี้
> 
> **สถาปัตยกรรมระบบ (Architecture):** 
> - **Backend:** Python (FastAPI), OpenCV, NumPy, Redis, Celery (หรือ APScheduler)
> - **Frontend:** Next.js (สำหรับ Web App เริ่มต้น) + Leaflet.js/Mapbox

## Open Questions
> [!WARNING]
> 1. **สถานีเรดาร์:** สำหรับ MVP เราจะเริ่มต้นที่สถานีสกลนคร (`sknLoop.php`) เพียงสถานีเดียวเลยใช่หรือไม่ครับ?
> 2. **Infrastructure/Hosting:** มี Cloud Provider ที่วางแผนจะใช้ (เช่น AWS, GCP, Vercel, DigitalOcean) อยู่แล้วหรือไม่ สำหรับการรัน Backend, Worker และ Redis?
> 3. **Notification Logic:** การแจ้งเตือนจะส่งไปหาทุกคนที่เคยกดแชร์พิกัดไว้และพิกัดนั้นอยู่ในแนวฝน ใช่หรือไม่? (หรือพิกัดมีวันหมดอายุ เช่น 1-2 ชั่วโมงหลังจากแชร์)

## Proposed Changes

การสร้างโครงสร้างโปรเจกต์ (Monorepo) เริ่มแรก:

### Backend
จะเป็น API และ Worker สำหรับดึงภาพและวิเคราะห์ทิศทางลม/ฝน
#### [NEW] `backend/app/main.py`
Entry point ของ FastAPI
#### [NEW] `backend/app/scraper.py`
โมดูลดึงภาพเรดาร์และวิเคราะห์ Metadata Timestamp หากดีเลย์เกิน 30 นาทีให้แจ้ง Alert Status
#### [NEW] `backend/app/processor.py`
โมดูลทำ Geo-referencing และวิเคราะห์ภาพด้วย OpenCV Optical Flow
#### [NEW] `backend/app/notifier.py`
โมดูลเชื่อมต่อ Line OA และ Telegram Bot API
#### [NEW] `backend/app/tasks.py`
ระบบตั้งเวลา (Cron) เพื่อประมวลผลดึงภาพและรัน Pipeline ทุก 5-10 นาที
#### [NEW] `backend/requirements.txt`
Dependencies ของระบบ

### Frontend
แอปพลิเคชันสำหรับแสดงผลเรดาร์และขอพิกัดผู้ใช้
#### [NEW] `frontend/package.json`
ไฟล์จัดการ dependencies ของโปรเจกต์ Next.js
#### [NEW] `frontend/src/app/page.tsx`
หน้าหลักแสดงแผนที่จาก Leaflet/Mapbox ซ้อนทับด้วยภาพเรดาร์ (Overlay) และปุ่ม "ขอตำแหน่งปัจจุบันเพื่อเช็คฝน"

## Verification Plan

### Automated Tests
- เขียน Unit Test ทดสอบการทำ Geo-referencing ว่าสามารถแมพพิกเซลในภาพเข้ากับ Lat/Lng ได้แม่นยำ
- ทดสอบ (Mock) การส่ง Notification ผ่าน LINE/Telegram

### Manual Verification
- รันระบบแบบ End-to-End ตั้งแต่ดึงภาพจากกรมอุตุฯ มาประมวลผลแบบ Time-lapse
- ทดลองแชร์พิกัดบนเว็บและดูว่าได้รับแจ้งเตือนที่ถูกต้องหรือไม่ หากจำลองว่าฝนกำลังมุ่งหน้าไปทางนั้น
