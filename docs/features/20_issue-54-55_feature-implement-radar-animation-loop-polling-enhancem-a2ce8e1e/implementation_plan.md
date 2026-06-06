# Feature: Radar Loop Polling, Location Fine-tuning & Optical Flow Nowcasting

เป้าหมายของแผนนี้คือการพัฒนาระบบ TMD Radar ให้สมบูรณ์แบบยิ่งขึ้น โดยแบ่งเป็น 3 ส่วนหลัก:
1. **Radar Loop & Polling**: การเก็บภาพย้อนหลังเพื่อทำ Loop Animation และเตรียมทำ Optical Flow สำหรับคำนวณ ETA
2. **Location Mapping Fine-tuning**: การปรับสมการคำนวณ Lat/Lng -> Pixel ให้แม่นยำที่สุด (แก้ปัญหาขอบภาพและแผนที่ทรงกลม)
3. **Optical Flow Nowcasting**: การนำอัลกอริทึม Optical Flow มาสร้างระบบพยากรณ์ฝนล่วงหน้า (Nowcasting) แบบแม่นยำราย 15 นาที โดยคำนวณจากทิศทางและความเร็วในการเคลื่อนที่ของกลุ่มฝน

## Design Considerations & Tradeoffs

### 1. Storage สำหรับเก็บภาพ Polling
| รูปแบบ Storage | ข้อดี (Pros) | ข้อเสีย (Cons) |
| --- | --- | --- |
| **Local Filesystem** | เร็วที่สุดในการพัฒนา, ไม่ต้องตั้งค่า Credential, อ่านเขียนเร็ว | ทำ Multi-instance ลำบาก, เปลืองดิสก์, เสี่ยงไฟล์หายเมื่อ Restart |
| **Google Cloud Storage** | สเกลได้ไม่จำกัด, แชร์ภาพให้ทุก Service ได้, คงทนสูง | ต้องตั้งค่า Service Account, มีค่าใช้จ่าย, Latency อาจสูงกว่า Local |
| **Redis / Database** | ตั้ง TTL ลบตัวเองอัตโนมัติได้ง่าย, เร็วมาก (In-memory) | สิ้นเปลืองทรัพยากรราคาแพงมาก, ไม่แนะนำสำหรับเก็บไฟล์ |

### 2. การประเมินทิศทางฝน (Advection Approach)
เมื่อได้ Vector `(dx, dy)` จากเฟรมเรดาร์ย้อนหลัง เรามี 2 วิธีในการพยากรณ์:
- **Forward Tracking:** คำนวณขยับพิกเซลฝนทั้งหมดไปข้างหน้า (+15m, +30m) สร้างเป็นภาพอนาคต แล้วเช็คพิกัดผู้ใช้
  - *ข้อดี:* ได้ภาพพยากรณ์รวม เอาไปแสดง Animation ได้
  - *ข้อเสีย:* ใช้เวลาคำนวณนานมาก (หนัก CPU) ไม่เหมาะกับการตอบ API Real-time
- **Backward Tracking (Semi-Lagrangian):** ถอยพิกัดเป้าหมายกลับไปตาม Vector ขั้วตรงข้าม `(px - dx, py - dy)` ว่ามีฝนต้นทางอยู่ไหม
  - *ข้อดี:* คำนวณเร็วมาก O(1) ตอบ API ได้ทันที
  - *ข้อเสีย:* ไม่ได้ภาพ Animation อนาคตทั้งประเทศ

## Decisions Made
- **การ Fine-tune ตำแหน่ง (Location Mapping):** ตกลงใช้ **ทั้งสองวิธี (Both)** 
  - ใช้ **Mathematical Projection Formulas** (เช่น Equirectangular / Web Mercator) เป็นแกนหลัก เพื่อชดเชยความโค้งของโลก
  - ใช้ **Manual Calibration Points** เป็นตัวช่วยตบให้เข้าที่ (Affine Transformation/Offset) อ้างอิงจาก Landmark 4 จุดหลักบนแผนที่ TMD เพื่อแก้ปัญหาภาพบิดเบี้ยวหรือวาดผิดสัดส่วนของต้นทาง
- **Storage:** เลือกใช้ **GCS (Google Cloud Storage)** เนื่องจากรองรับการสเกลบน Cloud Run ได้ดีกว่า
- **การประเมินทิศทางฝน:** ตัดสินใจใช้ **Backward Tracking (Semi-Lagrangian)** สำหรับตอบ Webhook / API เพราะเร็วและกินทรัพยากรน้อยกว่ามาก
- **พยากรณ์ล่วงหน้า:** ประเมินฝนไปข้างหน้าที่เวลา +15m, +30m, +45m, +60m

## Proposed Changes

---

### Radar Processor Updates
#### [MODIFY] [tmd_radar_processor.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/tmd_radar_processor.py)
- เพิ่มฟังก์ชัน `fetch_loop_gif_and_extract_frames()` สำหรับดึง `Loop.gif` แล้วใช้ `imageio`/`PIL` แตกไฟล์เป็น Array ของภาพย้อนหลัง
- เพิ่มฟังก์ชัน `save_polled_frame()` สำหรับบันทึกภาพจากการ Polling ด้วย Scheduler (จุดเซฟขึ้นอยู่กับ Storage ที่เลือก)
- แก้ไขสูตร `latlng_to_pixel()` โดยใส่ Projection Formula และรองรับ Matrix Transformation ผ่าน Calibration Points
- เพิ่มฟังก์ชัน `extrapolate_rain_at_pixel(img, flow, px, py, steps)` ที่ช่วยคำนวณหาค่า dBZ ล่วงหน้าตามจำนวน Step โดยอัตโนมัติ พร้อมทั้งใช้ `calculate_growth_decay` ช่วยปรับความแรงฝนให้สมจริงยิ่งขึ้น

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

### Scheduler Updates
#### [MODIFY] [scheduler_tasks.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/scheduler_tasks.py)
- อัปเดต `fetch_tmd_radar_routine()` ให้บันทึกภาพพร้อม Timestamp เป็นชื่อไฟล์เพื่อทำ History Timeline
- (หากใช้ Local) เพิ่มระบบหมุนเวียนลบไฟล์ภาพที่เก่ากว่า 3 ชั่วโมง

### Config Updates
#### [MODIFY] [tmd_radar_config.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/tmd_radar_config.py)
- เพิ่มฟิลด์ใน `StationConfig` สำหรับ Fine-tune พิกัด: `calibration_points` สำหรับทำ Affine Transform (ระบุ Lat/Lng สัมพันธ์กับ Pixel)
- เพิ่ม `projection_type` เพื่อเลือกสมการคณิตศาสตร์ที่เหมาะสมสำหรับสถานีนั้นๆ

## Verification Plan

### Automated Tests
- เขียน Unit test สำหรับฟังก์ชันคณิตศาสตร์ (Projection + Affine Transform) ให้แปลงค่าไป-กลับได้ตรงกับค่า Calibration Points
- ทดสอบการแตกไฟล์ GIF คืนค่าเป็น List ของ NumPy arrays ได้ถูกต้อง
- สร้าง Test จำลอง `flow` vector แบบสมมติ (ฝนเคลื่อนที่จากซ้ายไปขวา) และตรวจสอบว่า `extrapolate_rain_at_pixel` ทายว่าฝนจะมาถึงพิกัดเป้าหมายในอีก X นาทีได้ถูกต้อง

### Manual Verification
- นำจุดเป้าหมายบนแผนที่ (ที่มีพิกัดชัดเจน) มาพล็อตทับบนภาพเรดาร์ด้วยสีที่เห็นชัด แล้วตรวจสอบด้วยตาเปล่าว่าจุดนั้นทับอยู่ตรงกับตำแหน่งเมือง/ขอบเขตจังหวัดจริงๆ หรือไม่
- ขอพิกัดผู้ใช้ 1 จุด แล้วทดลองยิง API `predict_rain` โหมดบังคับ `tmd-radar` สังเกตดูว่ามี `predictions` ล่วงหน้าออกมาหรือไม่ และสอดคล้องกับภาพ Loop เรดาร์จริงบนเว็บไซต์หรือไม่
