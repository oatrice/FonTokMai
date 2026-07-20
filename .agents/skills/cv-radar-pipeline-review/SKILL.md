---
name: cv-radar-pipeline-review
description: Framework for reviewing, debugging, and optimizing CV/image-processing pipelines that extract shapes or regions from imagery — especially radar, satellite, meteorological, and cloud imagery, but applies to any pipeline using contour detection, convex hull, morphological ops, color/spectral masking, or edge detection. Use whenever the user debugs a pipeline producing masks/contours that are "too big," "too smooth," "wrong shape," "blurry edges," or don't match the source; whenever code uses cv2.convexHull, cv2.dilate/erode/morphologyEx, Canny/Sobel filters, or RGB/HSV/LAB/Spectral color-threshold masking; or whenever asked to review an OpenCV/image-segmentation/Edge AI pipeline. Trigger even without an explicit "review" request — any request to explain, fix, optimize, or improve a shape-extraction/masking/edge-detection pipeline's behavior qualifies. Also use for radar reflectivity (dBZ) data, storm/cloud shape detection, remote-sensing, or Cloud-Edge deployment tasks.
---

# CV / Radar & Cloud Pipeline Review

กรอบความคิด (framework) สำหรับวิเคราะห์ ดีบัก และเพิ่มประสิทธิภาพ Pipeline ที่ประมวลผลภาพ (โดยเฉพาะภาพเรดาร์/ดาวเทียม/อุตุนิยมวิทยา/ภาพถ่ายเมฆ) เพื่อแปลงเป็น mask, contour, polygon หรือตรวจจับเส้นขอบ ปัญหาประเภทนี้มักไม่ได้เกิดจากบั๊กจุดเดียว แต่เกิดจาก "effect สะสม" ของหลายขั้นตอนที่แต่ละขั้นดูสมเหตุสมผลเมื่อมองแยกกัน — ต้องไล่วิเคราะห์ทั้ง pipeline เป็นระบบเดียว ตั้งแต่ขั้นตอน Preprocessing ไปจนถึงการนำไป Optimization รันบน Edge Device

ใช้ 6 หมวดความรู้ด้านล่างเป็น checklist เวลาอ่านหรือรีวิวโค้ดประเภทนี้ ไม่ต้องใช้ทุกหมวดเสมอไป — แต่ให้ scan ผ่านทุกหมวดเพื่อเช็คว่าอาการที่ผู้ใช้อธิบาย (เช่น "รูปทรงกว้างเกินจริง", "ขอบเมฆฟุ้งจนจับพลาด", "โมเดลหนักเกินไปสำหรับกล้อง/โดรน") ตรงกับหมวดไหน

## วิธีใช้ framework นี้

1. **อย่า patch ที่อาการ** — ถ้าคนขอ "ทำให้กรอบแคบลง" หรือ "ลด noise ขอบเมฆ" อย่าเสนอ shrink factor, Canny threshold, หรือ filter เพิ่มทันที ให้ trace ก่อนว่าอะไรทำให้เกิดสิ่งนั้นตั้งแต่ต้น (ดูหมวด 6)
2. **ไล่ mask/data ทีละ stage** ใน pipeline แล้วถามที่ทุกจุดว่า stage นี้ทำให้พื้นที่/ความแม่นยำ "โตขึ้น" หรือ "เล็กลง" หรือทำให้ขอบเขต "เบลอ/ฟุ้ง" ขึ้น — เขียน mental trace ออกมาให้เห็นเป็นลำดับขั้น ก่อนเสนอ fix
3. **แยกอาการ (broad framing) ออกจาก root cause** เสมอ แล้วระบุให้ชัดว่า fix ที่เสนอไปแก้ที่ root cause จริงหรือแค่ปิดอาการ

---

## 1. Computational Geometry & Shape Extraction

จุดที่พลาดบ่อยที่สุดในโค้ดประเภทนี้คือการใช้ `cv2.convexHull()` เป็น default โดยไม่รู้ตัวว่ามันคือ **lossy transformation ที่ area ของผลลัพธ์ ≥ area ต้นฉบับเสมอ**

- **Convex hull vs concave hull (alpha shape)**: convex hull "ยืด" ทุกส่วนเว้าให้ตรง ถ้ารูปทรงต้นฉบับมีส่วนเว้า (concave) อยู่จริง — เช่น squall line ของพายุ หรือขอบเขตของเมฆธรรมชาติ — convex hull จะบวมออกจนพื้นที่ผิดจากของจริงมาก ถ้าเจออาการ "mask กว้างเกินภาพต้นฉบับ" ให้เช็คจุดนี้เป็นอันดับแรก
- **Solidity / convexity ratio** (`contour_area / hull_area`) เป็นตัวเลขที่บอกได้ทันทีว่ารูปทรงนี้เหมาะจะใช้ convex hull หรือไม่ — solidity ต่ำ (เช่น < 0.8) แปลว่ารูปทรงเว้ามาก การใช้ convex hull จะทำให้เพี้ยนมาก ควรพิจารณา concave hull / alpha shape หรือใช้ contour ดิบแทน
- **Polygon simplification** (`cv2.approxPolyDP`, Douglas-Peucker): ค่า epsilon ที่สูงทำให้รูปทรง "เรียบ" ขึ้นแต่ fidelity ต่อรูปทรงจริงลดลง เวลา debug ต้องแยกให้ออกว่าความเพี้ยนมาจาก simplification หรือมาจาก hull

**เวลารีวิว**: ถ้าเห็น `convexHull()` ในโค้ดที่ทำงานกับรูปทรงธรรมชาติ (เมฆ, พายุ, สิ่งมีชีวิต, ชายฝั่ง ฯลฯ) ที่มักมีส่วนเว้า ให้ตั้งคำถามทันทีว่าทีมตั้งใจแลก fidelity เพื่อความเรียบ/เร็วหรือเปล่า ไม่ใช่แค่ก็อปมาจาก tutorial

## 2. Morphological & Edge Processing

`dilate` / `erode` / `open` / `close` หรือ Edge Filters (Canny, Sobel, Laplacian) แต่ละตัวมี **effect สะสม (compounding)** เมื่อรันต่อกันหลายจุดใน pipeline เดียว การมองแยกทีละบรรทัดจะพลาดง่ายมาก ต้อง trace ว่า kernel หรือ window size ที่จุดหนึ่งไปกระทบผลลัพธ์ปลายทางยังไง

- ไล่ทุก morphological op ใน pipeline เรียงตามลำดับที่รัน พร้อม kernel size และ iteration count ของแต่ละตัว แล้วรวมผลสะสม (เช่น dilate 3x3 x2 ครั้ง + close 5x5 อีกจุดหนึ่ง = ขยายไปมากกว่าที่ตั้งใจไว้เห็นๆ)
- **Edge Dynamics**: สำหรับขอบที่มีความฟุ้งสูง (เช่น เมฆบาง หรือ Thin Clouds) การใช้ Canny Edge Detection ที่ฟิกซ์ threshold ตายตัวมักจะล้มเหลว ควรตรวจสอบว่าโค้ดมีการใช้วิธี Adaptive Thresholding, Otsu's Binarization หรือการทำ Hysteresis หรือไม่
- **Order matters**: closing ก่อน opening กับ opening ก่อน closing ให้ผลไม่เท่ากัน ต้องเช็คว่าลำดับที่ใช้ตรงกับเจตนาจริงหรือเป็นการก็อปแบบสุ่ม

## 3. Color Science, Spectral Analysis & Image Artifacts

**RGB exact-match เปราะบางมาก** กับ JPEG compression, anti-aliasing, แสงเงารบกวน, และความแปรผันของชั้นบรรยากาศ

- ถ้าเห็นโค้ดเทียบสีแบบ exact RGB (`pixel == (r,g,b)`) หรือ threshold ที่แคบมากบน RGB ให้ flag ทันทีว่าเปราะบางต่อ compression/anti-aliasing
- **Color Spaces**: แนะนำ HSV หรือ LAB + tolerance-based matching เป็น default mindset — LAB เหมาะกับงานที่ต้องการ perceptual uniformity, HSV เหมาะกับงานที่ความสว่าง/ความอิ่มตัวของสีแปรผันได้ (เช่น ภาพเรดาร์ที่มี gradient สี หรือภาพถ่ายเมฆภายใต้สภาพแสงแดดที่ต่างกันในแต่ละช่วงเวลา)
- **Spectral Data (สำหรับภาพถ่ายดาวเทียม)**: หากเป็นการตรวจจับระดับ Advance ให้ตรวจสอบการคำนวณดัชนีช่วงคลื่น เช่น การวิเคราะห์ภาพถ่ายหลายช่วงคลื่น (Multispectral/Multi-band เช่น NIR, SWIR) และเช็คว่ามีการทำ Atmospheric Correction เพื่อลด Noise จากชั้นบรรยากาศก่อนเข้ากระบวนการหาขอบหรือไม่

## 4. Deep Learning & Advanced Segmentation

ในยุคปัจจุบัน งานตรวจจับขอบวัตถุที่มีความซับซ้อนสูง (เช่น Advanced Cloud Detection) มักเปลี่ยนจาก Traditional CV มาเป็น Deep Learning

- **Architecture Check**: หากเป็นงานระดับ Pixel-level Accuracy โค้ดควรใช้สถาปัตยกรรมกลุ่ม Semantic Segmentation (เช่น U-Net, DeepLabv3, หรือโมเดลที่มี Feature Aggregation) เพื่อผสาน Feature ระหว่าง Low-level (ขอบเขต/เส้น) และ High-level (บริบท/ความหนาแน่น)
- **Loss Function**: สำหรับปัญหาขอบวัตถุที่ฟุ้งหรือมีความไม่สมดุลของคลาส (Class Imbalance) สูง ให้เช็คว่าโค้ดใช้แค่ Cross-Entropy หรือไม่ หากใช่ ควรแนะนำให้ประยุกต์ใช้ Dice Loss หรือ Focal Loss ร่วมด้วยเพื่อดักจับขอบเขตที่ละเอียดอ่อนได้ดีขึ้น

## 5. Domain Knowledge — Radar & Satellite Meteorology

ถ้า pipeline ทำงานกับข้อมูลเรดาร์ตรวจอากาศ หรือข้อมูลภาพถ่ายดาวเทียมอุตุนิยมวิทยา ต้องมีความรู้พื้นฐานเพื่อไม่ตีความ "อาการปกติของข้อมูล" ว่าเป็นบั๊ก:

- **dBZ scale**: หน่วยวัด reflectivity ของเรดาร์ตรวจอากาศ ค่าที่สูงมักสัมพันธ์กับฝนตกหนัก/พายุรุนแรง
- **รูปทรงเว้าและขอบฟุ้งเป็นเรื่องปกติ**: พายุและเมฆจริง (squall line, gust front, supercell, thin clouds) มักมีรูปทรง concave และมีความหนาแน่นไม่เท่ากันตามธรรมชาติ — ถ้า pipeline พยายามทำให้ขอบเรียบหรือแข็งจนเกินไป (Too Smooth/Sharp boundary) จะทำให้สูญเสียข้อมูลเชิงวิทยาศาสตร์ที่สำคัญ
- **Hysteresis thresholding**: เทคนิคมาตรฐานในงาน remote sensing (ใช้ threshold สูง/ต่ำสองระดับเพื่อลด noise โดยไม่ตัดรายละเอียดสำคัญทิ้ง) — ถ้าเห็นเทคนิคนี้ในโค้ด ไม่ใช่ของที่ dev คิดขึ้นเอง แต่เป็น established practice ที่ควรเข้าใจก่อนแก้

## 6. Edge AI & Model Optimization (สำหรับระบบ Distributed/Hybrid)

หากโจทย์มีข้อจำกัดเรื่องการนำ Pipeline หรือ Model ไปรันบนอุปกรณ์หน้างาน (Edge Devices เช่น โดรน, กล้อง Smart Camera, หรือคอมพิวเตอร์ขนาดเล็ก)

- **Resource Constraints vs Latency**: ตรวจสอบว่าโมเดลใหญ่เกินไปจนทำให้เกิด Latency สูง หรือ Bandwidth ไม่พอส่งกลับ Cloud หรือไม่
- **Optimization Techniques**: มองหาจุดที่สามารถทำ Model Quantization (เช่น แปลงเป็น INT8/FP16), Knowledge Distillation, หรือการแปลงโมเดลให้อยู่ในรูป Format ของ Edge Engine โดยเฉพาะ (เช่น TensorRT, ONNX Runtime, TFLite) เพื่อประมวลผลแบบ Real-time บน Edge Device

## 7. Systematic Debugging Methodology

วิธีคิดที่ทำให้จับปัญหาได้แม่น ไม่ใช่แค่ domain knowledge:

- **Trace มาสก์/ข้อมูลผ่านทุก stage** ของ pipeline แล้วถามที่ทุกจุดว่า "ขั้นตอนนี้ทำให้พื้นที่ mask โตขึ้น เล็กลง หรือสูญเสียความละเอียดขอบไป" — เขียนออกมาเป็นลำดับ stage-by-stage ก่อนสรุป ไม่ใช่มองข้าม pipeline ทีเดียวแล้วเดา
- **แยก "อาการ" (broad framing ที่คนอธิบายมา) ออกจาก "จุดตั้งต้นของปัญหา"** เช่น อาการคือ "ขอบเมฆเบลอกว้างเกินไป" แต่ต้นตอจริงคือการใช้ kernel ขนาดใหญ่เกินไปในขั้น Morphological Closing หรือการขาดการทำ Dynamic Thresholding — เสนอ fix ที่ต้นตอเสมอ ไม่ใช่ shrink ปลายทางเพื่อกลบอาการ
- เมื่อสรุปการวิเคราะห์ให้ผู้ใช้ ให้แสดง trace เป็นขั้นเป็นตอน (input → stage 1 → stage 2 → ... → output) พร้อมระบุจุดที่เป็นต้นตอของปัญหาชัดเจน ก่อนเสนอ fix

---

## Output ที่ควรให้เวลารีวิว pipeline แบบนี้

เมื่อวิเคราะห์โค้ด/ปัญหาแบบนี้เสร็จ ให้สรุปในรูปแบบนี้:

1. **Trace ทีละ stage** — พื้นที่/ความแม่นยำ/ความคมชัดของขอบ เปลี่ยนแปลงยังไงในแต่ละ stage (โต/เล็กลง/เพี้ยน/ฟุ้ง)
2. **Root cause** — ระบุจุดเดียวหรือไม่กี่จุดที่เป็นต้นตอจริง อ้างอิงบรรทัด/ฟังก์ชัน/พารามิเตอร์ที่เกี่ยวข้อง
3. **ทำไมถึงเกิด** — อธิบายด้วยหลักการจากหมวด 1-6 ที่เกี่ยวข้อง (เช่น "เพราะการใช้ Canny threshold แบบฟิกซ์ค่า ไม่รองรับความฟุ้งของ Thin Cloud")
4. **Fix ที่ต้นตอ** — เสนอทางแก้ที่จุดต้นตอ ไม่ใช่ patch ปลายทาง พร้อมเทียบ trade-off ถ้ามี (เช่น เปลี่ยนไปใช้ Adaptive Thresholding ร่วมกับ Morphological Refining หรือการทำ Quantization ก่อนรันบน Edge)
5. ถ้ามีความรู้เฉพาะทาง (เช่น radar meteorology, cloud dynamics) ที่ทำให้ "อาการ" ที่เห็นเป็นเรื่องปกติของข้อมูล ไม่ใช่บั๊ก ให้ระบุแยกออกมาชัดๆ เพื่อไม่ให้แก้ผิดจุด