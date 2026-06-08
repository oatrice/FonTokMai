# Implementation Walkthrough: Cloud Trajectory Optimization (Issue #66)

## Changes Made
- **File:** `backend/app/services/tmd_radar_processor.py`
- **Component:** `find_approaching_clouds`
- **Modifications:** 
  - We replaced the basic dot product check (which only ensured the cloud was moving generally towards the user) with a strict **Perpendicular Distance (Cross Track Error)** check.
  - A new parameter `hit_radius: int = 15` was introduced to define the tolerance width of the cloud trajectory.
  - The optical flow vector `(cvx, cvy)` and position vector `(to_x, to_y)` are cross-multiplied and divided by the velocity magnitude to find the closest distance the cloud trajectory will pass by the user. If this distance is greater than `hit_radius`, the cloud is safely ignored.

## What was verified
- The logic strictly evaluates the perpendicular offset of the cloud's exact motion path against the user's location.
- The `hit_radius = 15` effectively filters out adjacent storms that are moving parallel to the user without directly striking them, minimizing false alarms for nearby but non-intersecting rain cells.

---

# สรุปผลการปรับปรุง TMD Radar Processor (Fine-Tuning)

หลังจากการวิเคราะห์และปรับแต่งโค้ดระดับ Production เพื่อแก้ปัญหาฝนปลอมและจับเมฆฝนจริงให้แม่นยำขึ้น มีรายละเอียดการทำงานที่สำเร็จแล้วดังนี้ครับ:

## 1. เพิ่มความแม่นยำในการตรวจจับสี (Color Matching Precision)
เราได้ปรับปรุงกระบวนการแปลงสีพิกเซลจากรูป GIF ของ TMD ให้เป็นระดับฝน (dBZ) ให้ฉลาดและรัดกุมยิ่งขึ้น
- **เพิ่ม `IGNORED_COLORS`**: นำสีพื้นหลังแผนที่ที่เป็นปัญหา (`RGB: 32, 45, 93` สีน้ำตาลเทา) ไปใส่ในรายชื่อสีที่ต้องเมิน 
- **เพิ่ม `DBZ_COLOR_MAPPING`**: เพิ่มเฉดสีเขียวของเมฆที่ถูกบีบอัดในไฟล์ GIF (`RGB: 73, 160, 71`) ให้กลายเป็น 25.0 dBZ เพื่อรักษาเนื้อเมฆไว้ให้สมบูรณ์
- **ปรับสมการเทียบสี (Vectorized Euclidean Distance)**: แทนที่จะจับคู่สีที่ "ใกล้เคียงที่สุด" อย่างเดียว ตอนนี้เราเช็คด้วยว่าระยะห่างของสีนั้น ใกล้เคียงกับ Palette ของเรดาร์ หรือ Palette ของพื้นหลัง (Ignored) มากกว่ากัน **ถ้าใกล้พื้นหลังมากกว่า จะถูกตีเป็น 0 dBZ ทันที!**
- ลดค่า Threshold ลงเหลือ `40` (จาก 80) เพื่อป้องกันความผิดพลาดจากการจับคู่สีข้ามเฉด

## 2. ปรับแต่งเงื่อนไขการรวมกลุ่มเมฆ (Clustering Config)
- ลดข้อกำหนดของ `len(group)` จาก 5 พิกเซล เหลือ **3 พิกเซล** ทำให้จับเมฆกลุ่มเล็กๆ ที่กระจัดกระจายได้
- เพิ่มค่าความอนุโลมทิศทางลม `hit_radius` (Cross Track Error) เป็น **20px** (จากเดิม 15px) ทำให้พิกเซลขอบๆ เมฆสีเขียวที่ไม่ตรงเป้าเป๊ะๆ สามารถเข้ามารวมกลุ่มกันได้

---

## ✅ ผลลัพธ์จากการรันทดสอบ (Validation Results)

จากการรันสคริปต์ `test_custom_image.py` ทบทวนโค้ด Production ล่าสุดพบว่า:
1. **หายวับไปกับตา**: ก้อน 55 dBZ สีม่วง (ที่โผล่มามี ETA 13-19 ชั่วโมง) ถูกลบทิ้งเกลี้ยง 100% เพราะถูกกรองด้วยเงื่อนไขใหม่
2. **เมฆสีเขียวรวมตัวเป็นก้อนเดียวสวยงาม**: ชิ้นส่วนเมฆสีเขียวที่เดิมเคยกะพร่องกะแพร่งและถูกกีดกันออกไป ได้กลับมารวมร่างกันเป็นเมฆก้อนใหญ่ (ขนาด 57 พิกเซล) ก้อนเดียว 
3. **คำนวณทิศทางแม่นยำ**: เมฆก้อนนี้ถูกคำนวณ Vector ว่ากำลังมุ่งหน้ามาทาง User อย่างถูกต้อง ด้วยความเร็วคงที่ และมี ETA แจ้งเตือนอยู่ที่ **18.1 นาที** ซึ่งสอดคล้องกับภาพเรดาร์จริงครับ!

> [!TIP]
> ตอนนี้ภาพแจ้งเตือนใน Production และระบบ Image Timeline Generator (ที่ตัด ETA > 180m ออกอยู่แล้ว) จะคลีนขึ้นมาก จะไม่มีฝนปลอมสีม่วงมารบกวนการแจ้งเตือนแล้วครับ