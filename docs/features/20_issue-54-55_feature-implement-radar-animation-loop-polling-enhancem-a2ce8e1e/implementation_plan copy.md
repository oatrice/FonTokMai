# Feature: Optical Flow Nowcasting (TMD Radar)

เป้าหมายของแผนนี้คือการนำอัลกอริทึม **Optical Flow** ที่มีอยู่แล้วใน `TMDRadarProcessor` มาสร้างระบบพยากรณ์ฝนล่วงหน้า (Nowcasting) แบบแม่นยำราย 15 นาที โดยคำนวณจากทิศทางและความเร็วในการเคลื่อนที่ของกลุ่มฝน

## User Review Required
> [!IMPORTANT]
> **การเลือกเทคนิคการประเมินทิศทางฝน (Advection Approach)**
> เรามี `flow` vector `(dx, dy)` ที่คำนวณได้จากเฟรมเรดาร์ย้อนหลัง (15 นาที/เฟรม) เพื่อจะพยากรณ์ว่าฝนจะตกที่ตำแหน่งของผู้ใช้ (พิกัด `px, py`) หรือไม่ เรามี 2 วิธีหลัก:
>
> 1. **Forward Tracking (ผลักกลุ่มฝนไปข้างหน้า):** คำนวณพิกเซลฝนทั้งหมดในภาพ แล้วขยับตาม Vector ทีละพิกเซลเพื่อสร้างภาพเรดาร์อนาคต (+15m, +30m) จากนั้นค่อยเช็คว่าตรงกับพิกัดผู้ใช้ไหม
>    - *ข้อดี:* ได้ภาพเรดาร์พยากรณ์ล่วงหน้า เอาไปแสดงเป็น Animation บนหน้าเว็บได้
>    - *ข้อเสีย:* ใช้เวลาคำนวณนานมาก (หนัก CPU) ไม่เหมาะกับการตอบกลับ API แบบ Real-time
> 
> 2. **Backward Tracking (Semi-Lagrangian - ถอยพิกัดผู้ใช้กลับไปหาฝน):** ไม่ต้องคำนวณทั้งภาพ แค่ใช้พิกัดผู้ใช้ `(px, py)` แล้วลากเส้นย้อนกลับไปในทิศทางตรงข้ามกับลม `(px - dx, py - dy)` เพื่อดูว่าต้นทางมีฝนอยู่หรือไม่ 
>    - *ข้อดี:* คำนวณเร็วมาก O(1) ตอบ API ได้ทันที เหมาะกับการทำ Alert Server
>    - *ข้อเสีย:* ไม่ได้ภาพ Animation อนาคตทั้งประเทศ (ได้แค่กราฟพยากรณ์ของจุดนั้น)
>
> **ข้อเสนอจาก AI:** แนะนำให้ใช้ **Backward Tracking (วิธีที่ 2)** สำหรับทำ Webhook / API ตอบกลับผู้ใช้งานครับ เพราะเร็วและกินทรัพยากรน้อยกว่ามาก

## Open Questions
- เราควรพยากรณ์ล่วงหน้านานแค่ไหนครับ? (เช่น +15m, +30m, +45m, +60m) ปกติความแม่นยำของ Optical Flow แบบคงที่จะเริ่มลดลงหลัง 60 นาที 
- การแปลงค่า `dx, dy` เป็นความเร็วลม (Wind Speed) ควรแสดงผลด้วยไหมครับ? (เราสามารถแปลง pixel/15min ให้กลายเป็น km/h คร่าวๆ ได้)

## Proposed Changes

---

### Weather Manager Updates
#### [MODIFY] [weather_manager.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/weather_manager.py)
- อัปเดตเมธอด `_get_tmd_prediction()` 
- เปลี่ยนจากการเรียก `fetch_latest_image_bytes()` เป็นการเรียก `fetch_loop_gif_and_extract_frames()` เพื่อดึงภาพเรดาร์ย้อนหลัง (เช่น 6 เฟรมล่าสุด)
- คำนวณ `calculate_optical_flow()` เพื่อหา Vector field
- คำนวณ Backward Tracking:
  - `t+15m`: เช็คฝนที่ `px - dx`, `py - dy`
  - `t+30m`: เช็คฝนที่ `px - 2dx`, `py - 2dy`
  - `t+45m`: เช็คฝนที่ `px - 3dx`, `py - 3dy`
- สร้าง Array `predictions` สำหรับตอบกลับ API (มี `time_offset`, `rain_intensity`, `dbz`)

### TMD Radar Processor Updates
#### [MODIFY] [tmd_radar_processor.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/tmd_radar_processor.py)
- เพิ่มฟังก์ชัน `extrapolate_rain_at_pixel(img, flow, px, py, steps)` ที่ช่วยคำนวณหาค่า dBZ ล่วงหน้าตามจำนวน Step โดยอัตโนมัติ พร้อมทั้งใช้ `calculate_growth_decay` ช่วยปรับความแรงฝนให้สมจริงยิ่งขึ้น

## Verification Plan

### Automated Tests
- สร้าง Test จำลอง `flow` vector แบบสมมติ (ฝนเคลื่อนที่จากซ้ายไปขวา) และตรวจสอบว่า `extrapolate_rain_at_pixel` ทายว่าฝนจะมาถึงพิกัดเป้าหมายในอีก X นาทีได้ถูกต้อง

### Manual Verification
- ขอพิกัดผู้ใช้ 1 จุด แล้วทดลองยิง API `predict_rain` โหมดบังคับ `tmd-radar` สังเกตดูว่ามี `predictions` ล่วงหน้าออกมาหรือไม่ และสอดคล้องกับภาพ Loop เรดาร์จริงบนเว็บไซต์หรือไม่
