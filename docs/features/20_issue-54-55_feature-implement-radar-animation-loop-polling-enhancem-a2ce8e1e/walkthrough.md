# Walkthrough: TMD Radar Loop Polling & Location Fine-tuning

การพัฒนาระบบ Backend ในส่วนของ **Radar Batch** ตามแผนการที่วางไว้เสร็จสมบูรณ์แล้วครับ โดยมีรายละเอียดการทำ TDD และการพัฒนาฟีเจอร์หลักดังนี้:

## 1. การดึงภาพ Loop.gif และแยกเฟรม (Issue #54)
- **เครื่องมือที่ใช้:** เราใช้ไลบรารี `imageio` (`imageio.v3`) สำหรับการดึงและแยกเฟรมภาพออกจากไฟล์ `.gif` แบบหลายเฟรมของ TMD (เช่น `kkn240Loop.gif`)
- **โค้ดที่เพิ่ม:** เพิ่มเมธอด `fetch_loop_gif_and_extract_frames()` ลงใน `TMDRadarProcessor`
- **TDD Flow:** เริ่มจากการเขียน Failing Test `test_fetch_loop_gif_and_extract_frames` โดยจำลอง Mock HTTP response และการใช้งาน `imageio` ก่อน จากนั้นจึงเขียนฟังก์ชันจริงจนกว่าโค้ดจะรันผ่าน (Green)

## 2. การจัดเก็บภาพ Polling ด้วย Local Storage
- ระบบจะทำการเซฟภาพจากเรดาร์ลงใน `backend/tmp/` โดยอัตโนมัติ 
- มีฟังก์ชัน `cleanup_old_frames(max_age_hours=3)` ที่จะหมุนเวียนลบภาพเก่าทิ้งเมื่อรัน Scheduler ไม่ให้เปลืองพื้นที่ของเซิร์ฟเวอร์
- ระบบเชื่อมต่อกระบวนการนี้เข้ากับ `fetch_tmd_radar_routine()` ใน `scheduler_tasks.py` แล้ว
- **TDD Flow:** สร้าง `test_save_and_cleanup_polled_frames` โดยใช้ `tmp_path` ของ PyTest ในการจำลองพื้นที่จัดเก็บ และตรวจสอบเงื่อนไขการลบไฟล์ที่เกิน 3 ชั่วโมง 

## 3. การ Fine-tune พิกัด Lat/Lng สู่ Pixel (Issue #55)
- ระบบได้เพิ่มการรองรับ `calibration_points` และ `projection_type` ลงใน `StationConfig`
- สำหรับสมการคณิตศาสตร์ มีการคำนวณผ่าน **Linear/Affine Interpolation** เพื่อใช้ปรับจูนพิกัดแผนที่ (Mapping) โดยอ้างอิงจาก Landmark 4 มุม หากมีการระบุจุด Calibration ไว้อย่างแน่ชัด
- **TDD Flow:** เพิ่มชุดทดสอบ `test_latlng_to_pixel_with_calibration` เพื่อยืนยันว่าสูตรคณิตศาสตร์สามารถแปลงค่าพิกัดโลกกลับมาเป็นเลข Pixel แบบจำเพาะได้ตรงเผง

## Validation Results
- ยืนยันการทำงานด้วย `pytest backend/tests/test_tmd_processor.py` สำเร็จ 100% (6/6 tests passed) 
- ติดตั้ง `imageio` เรียบร้อยและเตรียมพร้อมสำหรับการต่อยอดไปยังกระบวนการ **Optical Flow (Nowcasting)** ในก้าวถัดไปครับ!
