# แผนการปรับปรุง OCR ด้วย Fallback Chain (Cloud Vision -> Gemini -> OCR.space)

ปัญหาที่พบคือ Tesseract OCR ไม่สามารถอ่านค่า Timestamp จากรูปภาพเรดาร์ของ TMD ได้อย่างแม่นยำ เนื่องจากตัวหนังสือมีขนาดเล็กและพื้นหลังมีความซับซ้อน ผู้ใช้จึงต้องการเปลี่ยนไปใช้ API ที่มีความสามารถในการทำ OCR สูงกว่า โดยจัดทำเป็นระบบ Fallback Chain ตามลำดับ

## User Review Required

> [!IMPORTANT]  
> 1. คุณจำเป็นต้องเพิ่ม API Key 2 ตัวในไฟล์ `.env` ของคุณ:
>    - `GEMINI_API_KEY` (สำหรับ Gemini 1.5 Flash)
>    - `OCR_SPACE_API_KEY` (ฟรี สมัครได้ที่ ocr.space)
> 2. สำหรับ **Google Cloud Vision** จะใช้ Credential เดียวกับ Firestore ที่ระบบใช้อยู่แล้ว (ผ่าน `GOOGLE_APPLICATION_CREDENTIALS`) โปรดตรวจสอบว่า Service Account มีสิทธิ์เข้าถึง Cloud Vision API 
> 3. จะมีการถอด `tesseract-ocr` ออกจาก `Dockerfile` เพื่อลดขนาดของ Image
> คุณเห็นด้วยกับแผนการและพร้อมที่จะเตรียม API Key เหล่านี้หรือไม่ครับ?

## Proposed Changes

### 1. Dependencies & Dockerfile

จะทำการอัปเดตไฟล์คอนฟิกต่างๆ เพื่อถอด Tesseract ออกและเพิ่ม Library ที่จำเป็น

#### [MODIFY] [requirements.txt](file:///Users/oatrice/Software-projects/FonMaYang/backend/requirements.txt)
- ลบ `pytesseract`
- เพิ่ม `google-cloud-vision`
- เพิ่ม `google-generativeai`

#### [MODIFY] [Dockerfile](file:///Users/oatrice/Software-projects/FonMaYang/backend/Dockerfile)
- ลบคำสั่ง `RUN apt-get update && apt-get install -y tesseract-ocr` ออกเพื่อลดขนาด Image 

#### [MODIFY] [.env.example](file:///Users/oatrice/Software-projects/FonMaYang/backend/.env.example)
- เพิ่ม `GEMINI_API_KEY=`
- เพิ่ม `OCR_SPACE_API_KEY=`

---

### 2. OCR Service 

เราจะปรับปรุง Logic ในคลาส `OCRService` ให้รองรับการเรียก API ภายนอกทั้ง 3 ตัวตามลำดับ 

#### [MODIFY] [ocr_service.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/ocr_service.py)
- เปลี่ยนกระบวนการ Pre-process ภาพ: แทนที่จะแปลงเป็นขาวดำ จะแปลง `numpy array` (RGB) ให้เป็นข้อมูล Byte ของไฟล์ `.png` เพื่อส่งให้ API แทน
- สร้างเมธอดสำหรับเรียก API แยกกัน:
  - `_call_cloud_vision(image_bytes)`
  - `_call_gemini(image_bytes)`
  - `_call_ocr_space(image_bytes)`
- ปรับโครงสร้างเมธอด `get_frame_timestamp` เพื่อให้ทำ **Fallback Chain**:
  1. ลองเรียก Cloud Vision ก่อน หากสำเร็จและพบ Timestamp ให้ส่งค่ากลับ 
  2. หากล้มเหลว (หรือหา Timestamp ไม่เจอ) ให้ลองเรียก Gemini 1.5 Flash
  3. หากยังล้มเหลวอีก ให้ลองเรียก OCR.space
  4. หากล้มเหลวทั้งหมด ให้ดึง `fallback_ts` (เวลาจาก Header หรือปัจจุบัน) มาใช้
- ระบบ Regex ดึงเวลาจากข้อความ (`_extract_timestamp_from_text`) จะยังคงเก็บไว้เพื่อนำข้อความที่ได้จาก API มาหาวันที่และเวลา 

---

### 3. Tests

ปรับปรุง Unit Test เพื่อให้สอดคล้องกับการเรียกผ่าน API แทน Tesseract

#### [MODIFY] [test_ocr_service.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/tests/test_ocr_service.py)
- ลบ Test สำหรับ `_preprocess_image` (แบบเก่า)
- ปรับปรุง Mock สำหรับการทดสอบ Fallback Chain เพื่อให้มั่นใจว่าเมื่อ Cloud Vision คืนค่าเปล่า มันจะทำการเรียก Gemini ถัดไป

## Verification Plan

### Automated Tests
- รันคำสั่ง `pytest tests/test_ocr_service.py` เพื่อตรวจสอบ Logic ของการทำ Fallback Chain ว่าข้ามไปยัง Provider ถัดไปถูกต้องเมื่ออันแรกพังหรือไม่

### Manual Verification
1. เพิ่ม API Key ลงใน `.env` ท้องถิ่น
2. รันสคริปต์เพื่อตรวจสอบว่าระบบสามารถดึงเวลาจาก TMD Radar ได้ถูกต้องผ่าน Vision API (หรือ API ลำดับถัดๆ ไป)
3. ตรวจสอบว่าใน Firestore (Collection `radar_frame_cache`) มีเอกสารข้อมูลถูกบันทึกพร้อมค่า timestamp ที่ถูกต้อง
