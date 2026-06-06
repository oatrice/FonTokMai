# รายการงาน (Task List) - Batch M

- `[x]` **Issue 56: วาดหมุดลงบนภาพเรดาร์**
  - `[x]` ศึกษาและเขียนเทสท์สำหรับการวาดหมุดลงบนเฟรม Numpy Array 
  - `[x]` เพิ่มฟังก์ชัน `draw_pin_on_frame(img, px, py)` ใน `tmd_radar_processor.py`
  - `[x]` ปรับแก้ฟังก์ชันดึงภาพ/สร้าง GIF ให้สามารถใส่ค่า `(px, py)` เพื่อวาดหมุดลงไปก่อนเซฟเป็นไฟล์ (In-memory GIF)
  - `[x]` ทดสอบส่งไฟล์เข้า Telegram ด้วยฟังก์ชันที่มีอยู่

- `[x]` **Issue 57: โมเดล Growth / Decay Rate**
  - `[x]` เขียนเทสท์ (TDD) สำหรับการจำลองสถานการณ์ฝนเพิ่มขึ้นและลดลง เพื่อทดสอบอัตราการเปลี่ยนแปลง
  - `[x]` อัปเดต `weather_manager.py` (หรือ `tmd_radar_processor.py`) เพื่อรวมการคำนวณ Extrapolation เข้ากับ Growth/Decay factor
  - `[x]` ตรวจสอบและดักจับค่าผิดปกติ (Thresholding: MAX, MIN, Damping)
  - `[x]` สร้างตัวแปรส่งออกสำหรับเปอร์เซ็นต์ Growth Rate
  - `[x]` อัปเดตฟอร์แมตข้อความที่ส่งแจ้งเตือนใน Telegram ให้มีคำอธิบายแนวโน้ม (Trend)

- `[/]` **Final Review & Telegram Update**
  - `[x]` ยืนยันว่า Notification และข้อความที่ส่งหา User สมบูรณ์และสวยงาม
  - `[ ]` แจ้งเตือนเสร็จสิ้นด้วยคำสั่ง `/notify_task_complete`
