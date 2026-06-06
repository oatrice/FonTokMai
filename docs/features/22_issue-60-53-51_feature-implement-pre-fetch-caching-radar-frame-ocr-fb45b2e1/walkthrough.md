# Walkthrough: Batch Issues 60, 53, 51

การพัฒนาในรอบนี้ได้มุ่งเน้นการปรับปรุง 3 ส่วนหลักเพื่อให้ระบบทำงานได้เสถียรและยืดหยุ่นมากขึ้นตาม Architecture Decisions 002:

## 1. Issue 60: OCR & Firestore Caching สำหรับ TMD Radar Timestamp
- **ปัญหา:** ที่ผ่านมาเราใช้วิธี Extract Timestamp ผ่านการโหลดหน้าเว็บ `loop.php` และ Parse HTML ทำให้ช้าและเสี่ยงพังหาก TMD เปลี่ยนหน้าเว็บ
- **การแก้ไข:** 
  - สร้าง `OCRService` ใน `app/services/ocr_service.py` ซึ่งจะนำภาพเรดาร์ล่าสุดมาครอบบริเวณขอบล่าง ทำ Thresholding เผื่อปรับให้อ่านง่าย แล้วใช้ **Tesseract OCR** (`pytesseract`) สกัดข้อความวันที่และเวลา
  - นำผลลัพธ์ Timestamp (ในหน่วย UTC) มาบันทึกลง Firestore `radar_frame_cache` โดยใช้ MD5 Hash ของภาพเป็น Document ID เพื่อให้ครั้งต่อไปถ้าเป็นภาพเดิมไม่ต้องรัน OCR อีก
  - เพิ่ม Dependency `pytesseract` และอัปเดต `Dockerfile` ให้ติดตั้ง `tesseract-ocr` ผ่าน `apt-get` 

## 2. Issue 51: Force Weather Data Source
- **ฟีเจอร์:** ให้ผู้ใช้บังคับใช้ API เจ้าใดเจ้าหนึ่งโดยเฉพาะ
- **การทำงาน:** 
  - ผู้ใช้สามารถพิมพ์คำสั่ง `/rain <provider_name>` เช่น `/rain tmd-radar` เพื่อข้ามระบบ Fallback แล้วดึงข้อมูลจากเจ้านั้นๆ ทันที
  - เพิ่มปุ่ม Inline Keyboard **✅ บังคับใช้ <Provider>** ใต้ข้อความผลลัพธ์ของโหมด **Compare API** เพื่อความสะดวกในการคลิกครั้งถัดไป
  - การทำงานภายในได้ปรับ `weather_manager.py` (ฟังก์ชัน `predict_rain`) เพื่อรองรับ `force_endpoint` โดยดึงข้อมูลจาก `service_map` ได้ทุกตัว

## 3. Issue 53: Compare API Integration
- **ฟีเจอร์:** รวม TMD Radar เข้าสู่ระบบเปรียบเทียบ API ทั้งหมด
- **การทำงาน:**
  - ปรับ Format การพ่นข้อมูลใน `_get_tmd_prediction()` ให้รองรับ List ของ `predictions` และค่าต่างๆ ตามที่ `WeatherManager` คาดหวัง
  - ปรับแก้ระบบการโต้ตอบใน `webhook.py` ในส่วนของ `compare_api_` เพื่อให้โชว์ผลลัพธ์ของ TMD Radar เคียงคู่กับ Tomorrow.io, Rainbow ฯลฯ ได้อย่างสมบูรณ์โดยไม่ติดบัค Image Error

## การทดสอบ (Verification)
- ✅ สร้าง Unit Tests `test_ocr_service.py` ตรวจสอบกระบวนการ Preprocess รูปภาพ และแกะ Timestamp
- ✅ รัน `pytest` ทั้งหมดผ่านเรียบร้อย (`test_tmd_processor.py` และ `test_ocr_service.py` รวม 13 items)
- โค้ดทั้งหมดได้ถูก Commit ขึ้น Git เรียบร้อยแล้ว (`feat/60-53-51-feature-implement-pre-fetch-ca`)

> [!TIP]
> ตอนนำขึ้น Cloud Run ให้แน่ใจว่า Base Image เป็น Debian/Ubuntu ที่มี `apt-get` เพราะเรามีการเพิ่มขั้นตอน `apt-get install -y tesseract-ocr` ใน Dockerfile ครับ
