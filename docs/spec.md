# 🌧️ RainNowcast (FonMaYang Project Specification)

**คำนิยาม:** แพลตฟอร์มพยากรณ์และแจ้งเตือนฝนตกระยะสั้น (Nowcasting) เชิงรุกรายนาที เน้นความเป็นส่วนตัวสูง (Privacy-first) และประหยัดพลังงาน (Energy-efficient)

---

## 1. ฟีเจอร์หลักในเฟส MVP (Core Features)

### 1.1 ระบบหน้าบ้านและแผนที่อินเตอร์แอคทีฟ (Interactive Map UI)
* **RainViewer Integration:** ดึงภาพแผ่นแผนที่กลุ่มฝน (`Map Tiles`) แบบโปร่งใส (PNG) จาก RainViewer API มาซ้อนทับ (Overlay) บนแผนที่ฐาน (Leaflet.js หรือ Mapbox) บนหน้าเว็บ/แอป
* **Time-Loop Animation:** หน้าจอควบคุมสามารถกดเล่น (Play), หยุด (Pause) หรือเลื่อนแถบเวลา (Timeline) ดูทิศทางการเคลื่อนที่ของฝนย้อนหลัง 60–120 นาที และพยากรณ์ล่วงหน้าได้
* **Dual-Language Support:** รองรับการแสดงผลภาษาไทยเป็นหลัก (MVP) และโครงสร้าง i18n รองรับภาษาอังกฤษในเฟสถัดไป

### 1.2 ระบบวิเคราะห์และแจ้งเตือนเชิงรุก (Proactive Notification Engine)
* **Rainbow Nowcast Integration:** ดึงข้อมูลดิบ (JSON) พยากรณ์ฝนรายนาทีล่วงหน้าสูงสุด 4 ชั่วโมงจาก Rainbow API มาเข้า Engine คำนวณหลังบ้าน
* **Chatbot Delivery:** ส่งข้อความแจ้งเตือนผู้ใช้ในลักษณะ **ETA (Estimated Time of Arrival)** ล่วงหน้า 15–30 นาที ผ่าน Line OA (Flex Message) และ Telegram Bot โดยบอกรายละเอียดชัดเจน เช่น *"ฝนกำลังเคลื่อนมาทางทิศตะวันออก จะตกหนักที่พิกัดของคุณในอีก 20 นาที และตกต่อเนื่อง 15 นาที"*

### 1.3 สถาปัตยกรรมการขอพิกัดแบบชาญฉลาด (Smart Location & Privacy-first)
* **No Background Tracking (Data Minimization):** ไม่มีระบบตามพิกัด GPS ของผู้ใช้ตลอดเวลาเพื่อประหยัดแบตเตอรี่มือถือและรักษาความเป็นส่วนตัว
* **On-Demand Location Request:**
  * **In-App:** มีปุ่มเด่นชัดให้ผู้ใช้ "กดแชร์พิกัดปัจจุบัน" เฉพาะตอนที่ต้องการเช็ค
  * **Chatbot:** ใช้ระบบ Rich Menu "แชร์ตำแหน่ง" หรือยิงข้อความทักตามเวลาสำคัญ (เช่น เวลาเลิกงาน) ชวนให้ผู้ใช้ส่งพิกัดเพื่อเช็คเส้นทางกลับบ้าน
* **Coarse-to-Fine Trigger:** ใช้ Geofencing สัญญาณมือถือวงกว้าง ตรวจสอบว่าฝนเข้าเขตจังหวัด/อำเภอหรือยัง หากเข้าเขตจึงจะส่ง Notification ไปทักให้ผู้ใช้กดแชร์พิกัดแม่นยำ

### 1.4 ระบบดักจับข้อมูลค้าง/ดีเลย์ (Data Quality & Delay Monitor)
* **Timestamp Delta Check (Δt):** เซิร์ฟเวอร์หลังบ้านจะเปรียบเทียบเวลาล่าสุดบนรูป/ข้อมูลของเรดาร์จากค่ายต้นทาง เทียบกับเวลาปัจจุบันของระบบ
* **Status Indicators:** แสดงสถานะความสดใหม่ของข้อมูลบนหน้าจอเป็น 3 ระดับ (🟢 ปกติ / 🟡 เริ่มดีเลย์ / 🔴 ข้อมูลค้างขัดข้อง เกิน 30 นาที)
* **Fail-safe Mechanism:** หากค่ายใดขึ้นสถานะ 🔴 (Outdated) ระบบหลังบ้านจะ **สั่งปิดการยิง Notification แจ้งเตือนความเร็วฝนและ ETA ของค่ายนั้นทันที** เพื่อป้องกันบอททำนายพลาดจนผู้ใช้เสียความมั่นใจ

---

## 2. โครงสร้างและสถาปัตยกรรมระบบ (Architecture & Tech Stack)

### 2.1 Backend (Python FastAPI)
* **Pluggable/Interface Design:** ออกแบบด้วย `Abstract Base Class` แยกโครงสร้างฟังก์ชันการทำงานหลักไว้ แล้วใช้คลาสย่อยแยก `RainViewerService` และ `RainbowService` ออกจากกันอย่างอิสระ เพื่อให้ในอนาคตสามารถทำการเปรียบเทียบหาค่าความต่าง (**Diff**) หรือถอดสลับผู้ให้บริการได้ง่าย
* **Task Scheduler:** ใช้ Redis ร่วมกับ Celery หรือ APScheduler ในการทำ Automated Cron Job ไปเคาะดึงข้อมูลจาก APIs ทุก ๆ 5–10 นาทีตามรอบของเรดาร์

### 2.2 Frontend
* **Web:** React.js / Next.js + TailwindCSS
* **Mobile App:** Flutter (โค้ดชุดเดียวรันได้ทั้ง iOS/Android)

---

## 3. แผนงานการขยายระบบในอนาคต (Future Roadmap)

* **Phase 1 (Current):** พัฒนา MVP โดยใช้ Cloud APIs (RainViewer + Rainbow) ทำงานผสานกันเพื่อลด Time-to-Market
* **Phase 2:** ทำระบบ Analytics บน Backend เพื่อคำนวณเปรียบเทียบค่าความต่าง (Diff Assessment) ระหว่างผลลัพธ์ของ RainViewer และ Rainbow เพื่อหาว่าค่ายไหนทำนายฝนในประเทศไทยได้แม่นยำกว่ากัน
* **Phase 3:** พัฒนาสคริปต์ Scraper และ Image Processing (OpenCV / NumPy) ของตัวเอง ไปดึงภาพเรดาร์ดิบจากหน้าเว็บกรมอุตุฯ ไทยตรง ๆ (เช่น `sknLoop.php` ของสกลนคร) มาทำ Denoise, ทำ Geo-referencing แปลงพิกเซลเป็นพิกัดโลก และคำนวณเวกเตอร์ลมด้วยวิธี Optical Flow เอง เพื่อทำระบบเป็น Source ที่ 3 ยืนยันความแม่นยำสูงสุดโดยไม่พึ่งพาบอทต่างประเทศ
