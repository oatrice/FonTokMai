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
# สรุปผลการปรับปรุงระบบ OCR Fallback Chain

ระบบ OCR ได้รับการอัปเกรดเป็น **Fallback Chain** ตามแผนที่วางไว้เพื่อเพิ่มความแม่นยำและเสถียรภาพในการสกัดเวลา (Timestamp) จากภาพเรดาร์ของ TMD โดยไม่ต้องพึ่งพา `tesseract-ocr` อีกต่อไป

## สิ่งที่เปลี่ยนแปลงในระบบ

### 1. ลำดับการทำ Fallback (Fallback Chain)
ระบบได้ถูกปรับปรุงใน `ocr_service.py` ให้ทำงานเป็นขั้นตอนดังนี้:
1. **Google Cloud Vision API:** เรียกใช้เป็นลำดับแรก (ใช้ Credential จาก Firestore) ซึ่งจะอ่านตัวอักษรได้แม่นยำมาก
2. **Gemini 1.5 Flash:** หาก Cloud Vision ล้มเหลวหรืออ่านค่าไม่ได้ ระบบจะเรียกใช้โมเดลของ Gemini โดยใช้ `GEMINI_API_KEY` แทน
3. **OCR.space API:** หาก Gemini ล้มเหลว ระบบจะทำการส่งรูปแบบ HTTP POST ไปที่ OCR.space โดยใช้ `OCR_SPACE_API_KEY`
4. **Fallback Timestamp:** หากทั้งสามตัวล้มเหลวทั้งหมด (หรือไม่มี API Key) ระบบจะใช้ค่าความปลอดภัย (Fallback Time) ไปบันทึกใน Firestore เช่นเดิมเพื่อป้องกันไม่ให้พยายามทำ OCR ซ้ำๆ

### 2. การลบ Tesseract OCR ออก
- ถอด `pytesseract` ออกจาก `requirements.txt`
- ถอดการติดตั้งโปรแกรม `tesseract-ocr` ออกจากคำสั่งใน `Dockerfile` ทำให้ Image มีขนาดเล็กลง

### 3. การจัดการ Environment Variables
- ได้ทำการเพิ่มตัวแปร `GEMINI_API_KEY` และ `OCR_SPACE_API_KEY` ลงในไฟล์ `.env.example` และ `.env` แล้ว 

## สิ่งที่คุณต้องทำต่อไป

> [!IMPORTANT]
> เพื่อให้ระบบนี้ทำงานได้สมบูรณ์ กรุณาเข้าไปที่ไฟล์ `backend/.env` แล้วใส่รหัส API Key ของคุณ:
> ```env
> GEMINI_API_KEY=your_gemini_key_here
> OCR_SPACE_API_KEY=your_ocr_space_key_here
> ```
> หากไม่ได้ใส่ไว้ ระบบจะข้าม Provider ตัวนั้นไปทำ Fallback ในลำดับถัดไปโดยอัตโนมัติ

## ผลการทดสอบ (Verification)
- ✅ `test_ocr_service.py`: เขียน Unit Test คลุมการจำลองเหตุการณ์ (Mock) กรณีที่เรียก API แล้วล้มเหลว เพื่อเช็คว่ามันกระโดดข้ามไปใช้ตัวเลือกที่ 2 และ 3 ได้ถูกต้อง
- ✅ การรัน `pytest` ผ่านทั้งหมดเรียบร้อยแล้ว
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
