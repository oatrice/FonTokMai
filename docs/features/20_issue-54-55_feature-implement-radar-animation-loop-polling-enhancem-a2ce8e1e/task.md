# Tasks

- [x] 1. **Setup Config**
  - [x] อัปเดต `tmd_radar_config.py` เพิ่ม `calibration_points` และ `projection_type`
- [x] 2. **TDD: Radar Processor (GIF & Fine-tuning)**
  - [x] เขียน Failing Test สำหรับฟังก์ชันแตกเฟรม `fetch_loop_gif_and_extract_frames`
  - [x] เขียนโค้ดให้ฟังก์ชันผ่าน (Green)
  - [x] เขียน Failing Test สำหรับสูตรคณิตศาสตร์ Fine-tuning (Projection + Affine) ใน `latlng_to_pixel`
  - [x] เขียนโค้ดให้สมการทำงานผ่าน (Green)
- [x] 3. **TDD: Scheduler Polling**
  - [x] เขียน Failing Test สำหรับ `save_polled_frame` และระบบลบไฟล์เก่ากว่า 3 ชั่วโมง
  - [x] เขียนโค้ด Scheduler และฟังก์ชันที่เกี่ยวข้องให้ผ่าน (Green)
- [x] 4. **Optical Flow Nowcasting**
  - [x] เพิ่มฟังก์ชัน `extrapolate_rain_at_pixel(img, flow, px, py, steps)` ใน `tmd_radar_processor.py`
  - [x] เปลี่ยน `_get_tmd_prediction()` ให้ดึงข้อมูล Loop GIF และประเมินฝนแบบ 0-60 นาที
  - [x] อัปเดตและรัน `pytest` สำหรับการทำนายฝน
- [x] 5. **Documentation & Verification**
  - [x] รันสคริปต์วาดจุดพิกัดลงบนแผนที่เรดาร์เพื่อทดสอบความแม่นยำด้วยตาเปล่า
  - [x] สรุปผลงานลงใน `walkthrough.md`
  - [x] แจ้งเตือนผู้ใช้ด้วย `notify_task_complete`
