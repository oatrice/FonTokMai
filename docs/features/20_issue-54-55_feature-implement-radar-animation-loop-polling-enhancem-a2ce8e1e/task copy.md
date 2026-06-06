# Optical Flow Nowcasting Implementation Tasks

- `[x]` **Update `tmd_radar_processor.py`**
  - เพิ่มฟังก์ชัน `extrapolate_rain_at_pixel(img, flow, px, py, steps)` สำหรับคำนวณ dBZ ล่วงหน้าแบบ Semi-Lagrangian (Backward Tracking)
- `[x]` **Update `weather_manager.py`**
  - เปลี่ยน `_get_tmd_prediction()` ให้ดึงข้อมูล Loop GIF
  - คำนวณ Optical Flow และจำลองพยากรณ์ล่วงหน้า (0-60 นาที, ทีละ 15 นาที)
  - นำผลลัพธ์ใส่ในรูปแบบ `predictions` ของ API Response
- `[x]` **Testing and Verification**
  - อัปเดตและรัน `pytest` สำหรับการทำนายฝน
  - ตรวจสอบความถูกต้องของการคำนวณ
- `[/]` **Documentation**
  - สรุปผลงานลงใน `walkthrough.md`
- `[ ]` **Notification**
  - แจ้งเตือนผู้ใช้ด้วย `notify_task_complete`
