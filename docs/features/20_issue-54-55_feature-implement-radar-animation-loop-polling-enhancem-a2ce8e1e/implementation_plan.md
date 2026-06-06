# Feature: Radar Loop Polling and Location Fine-tuning

เป้าหมายของแผนนี้คือการพัฒนาระบบ TMD Radar ให้สมบูรณ์แบบยิ่งขึ้น โดยแบ่งเป็น 2 ส่วนหลัก:
1. **Radar Loop & Polling**: การเก็บภาพย้อนหลังเพื่อทำ Loop Animation และเตรียมทำ Optical Flow สำหรับคำนวณ ETA
2. **Location Mapping Fine-tuning**: การปรับสมการคำนวณ Lat/Lng -> Pixel ให้แม่นยำที่สุด (แก้ปัญหาขอบภาพและแผนที่ทรงกลม)

## User Review Required
> [!IMPORTANT]
> **การเปรียบเทียบข้อดี-ข้อเสียของ Storage (Tradeoffs) เพื่อใช้เก็บภาพ Polling**
> กรุณาเลือกวิธีที่คุณ oatrice คิดว่าเหมาะสมที่สุดกับ Architecture ของโปรเจกต์นี้ครับ:

| รูปแบบ Storage | ข้อดี (Pros) | ข้อเสีย (Cons) |
| --- | --- | --- |
| **1. Local Filesystem** (`backend/tmp/`) | - ง่ายและเร็วที่สุดในการพัฒนา<br>- ไม่ต้องตั้งค่า Credential ใดๆ<br>- อ่าน/เขียนไฟล์ได้รวดเร็ว | - ทำ Multi-instance (Scale) ลำบาก เพราะไฟล์ไม่แชร์กัน<br>- เปลืองดิสก์ของเซิร์ฟเวอร์หลัก<br>- เสี่ยงไฟล์หายเมื่อ Restart Server |
| **2. Google Cloud Storage** (GCS) | - สเกลได้ไม่จำกัด (Unlimited Storage)<br>- แชร์ภาพให้ทุกๆ Service/Instance เข้าถึงได้<br>- ข้อมูลปลอดภัย มีความคงทนสูง | - ต้องตั้งค่า Service Account และ Bucket<br>- มีค่าใช้จ่ายเล็กน้อย (ตามปริมาณ)<br>- Latency อาจสูงกว่า Local เล็กน้อยเวลาอ่านภาพมาทำ Loop |
| **3. Redis / Database** | - สามารถตั้ง TTL ลบตัวเองอัตโนมัติได้ง่ายใน Redis<br>- เข้าถึงได้เร็วมาก (In-memory) | - การเก็บรูปภาพเป็น Bytes ใน RAM/DB สิ้นเปลืองทรัพยากรราคาแพงอย่างมาก<br>- ไม่แนะนำสำหรับการเก็บไฟล์ขนาดใหญ่/จำนวนมาก |

*คำแนะนำจาก AI:* ถ้าจะเปิดให้ใช้งานจริงในอนาคต (Production) **GCS** เป็นทางเลือกที่ดีที่สุด แต่ถ้าเป็นเพียงช่วงทดลอง **Local Filesystem** จะง่ายและเร็วที่สุดครับ

## Decisions Made
- **การ Fine-tune ตำแหน่ง (Location Mapping):** ตกลงใช้ **ทั้งสองวิธี (Both)** 
  - ใช้ **Mathematical Projection Formulas** (เช่น Equirectangular / Web Mercator) เป็นแกนหลัก เพื่อชดเชยความโค้งของโลก
  - ใช้ **Manual Calibration Points** เป็นตัวช่วยตบให้เข้าที่ (Affine Transformation/Offset) อ้างอิงจาก Landmark 4 จุดหลักบนแผนที่ TMD เพื่อแก้ปัญหาภาพบิดเบี้ยวหรือวาดผิดสัดส่วนของต้นทาง

## Proposed Changes

---

### Radar Processor Updates
#### [MODIFY] [tmd_radar_processor.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/tmd_radar_processor.py)
- เพิ่มฟังก์ชัน `fetch_loop_gif_and_extract_frames()` สำหรับดึง `Loop.gif` แล้วใช้ `imageio` แตกไฟล์เป็น Array ของภาพย้อนหลัง
- เพิ่มฟังก์ชัน `save_polled_frame()` สำหรับบันทึกภาพจากการ Polling ด้วย Scheduler (จุดเซฟขึ้นอยู่กับ Storage ที่เลือก)
- แก้ไขสูตร `latlng_to_pixel()` โดยใส่ Projection Formula และรองรับ Matrix Transformation ผ่าน Calibration Points

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
- ทดสอบการแตกไฟล์ GIF (`test_extract_gif_frames`) คืนค่าเป็น List ของ NumPy arrays ได้ถูกต้อง

### Manual Verification
- นำจุดเป้าหมายบนแผนที่ (ที่มีพิกัดชัดเจน) มาพล็อตทับบนภาพเรดาร์ด้วยสีที่เห็นชัด แล้วตรวจสอบด้วยตาเปล่าว่าจุดนั้นทับอยู่ตรงกับตำแหน่งเมือง/ขอบเขตจังหวัดจริงๆ หรือไม่
