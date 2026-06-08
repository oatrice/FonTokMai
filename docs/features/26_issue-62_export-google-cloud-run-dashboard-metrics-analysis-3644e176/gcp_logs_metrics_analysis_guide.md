# คู่มือการวิเคราะห์ Google Cloud Run Metrics และ Logs Explorer

เอกสารนี้รวบรวมคำแนะนำในการใช้เครื่องมือของ Google Cloud Platform (GCP) เพื่อวิเคราะห์ประสิทธิภาพ การใช้งานระบบ และการแก้ปัญหา (Troubleshooting) ของแอปพลิเคชัน FonTokMai

## 1. การวิเคราะห์กราฟบน Cloud Run Dashboard

เมื่อเข้าสู่หน้า Cloud Run Service Dashboard เราสามารถดูข้อมูลภาพรวมระบบระดับ Infrastructure ได้:

*   **Container Memory Utilizations:** ใช้เพื่อเช็คว่า "แอปใช้แรมเต็มหรือไม่" หากเส้นกราฟเฉลี่ยวิ่งเข้าใกล้ขีดจำกัด (เช่นแตะ 90%-100% ของ 512MiB) บ่อยๆ แสดงว่ามีความเสี่ยงที่จะเกิด Out of Memory (OOM) ซึ่งจะทำให้ Container พังและถูกรีสตาร์ท
*   **Request Latencies:** ใช้ดูความเร็วในการตอบกลับ (Latency) ของแอปพลิเคชัน เช่น "ยิงข้อความ Telegram ช้าไหม" กราฟมักแสดงเป็น `50th` (มัธยฐาน), `95th`, `99th` percentile ถ้าเส้น `99th percentile` พุ่งสูง แสดงว่ามี 1% ของผู้ใช้งานหรือกระบวนการบางอย่างที่ช้าผิดปกติมาก (เช่น ติดขัดที่ API กรมอุตุฯ)
*   **Request Count & Error Count:** จำนวน Request ที่เข้ามาต่อวินาที รวมถึงกราฟแสดงจำนวนข้อผิดพลาด 4xx (Client Errors) และ 5xx (Server Errors) หากมีแท่ง 5xx ปรากฏขึ้น แสดงว่าเกิด Unhandled Exception ขึ้นในแอป
*   **Container CPU Utilizations:** ดูภาระงาน (Load) ของซีพียูว่าทำงานหนักเกินไปหรือต้องเพิ่มคอนเทนเนอร์หรือไม่

## 2. การใช้ Logs Explorer เพื่อค้นหาปัญหาอย่างเจาะจง

ใน Logs Explorer เราสามารถใช้ Query Builder ในการกรองดูเฉพาะเหตุการณ์หรือ Request ที่สนใจได้

### ตัวอย่าง Query ที่ใช้บ่อย:

**1. หาคนยิง Webhook Telegram เข้ามาที่ `/api/v1/webhook`:**
```text
resource.type = "cloud_run_revision"
resource.labels.service_name = "fontokmai"
httpRequest.requestUrl =~ "/api/v1/webhook"
```

**2. ค้นหา Error (HTTP 500) และ Unhandled Exceptions ในโค้ดทั้งหมด:**
```text
resource.type = "cloud_run_revision"
resource.labels.service_name = "fontokmai"
severity >= ERROR
```

**3. ตรวจสอบว่าแอปพังเพราะ "แรมเต็ม" (Out of Memory - OOM) จริงไหม:**
```text
resource.type = "cloud_run_revision"
resource.labels.service_name = "fontokmai"
textPayload:"Memory limit of"
# หรือหาข้อความที่เกี่ยวกับ "OOM" หรือ "exceeded"
```

## 3. การนำออกข้อมูล (Export) ให้ AI ช่วยวิเคราะห์

แทนที่จะไล่อ่านตัวเลขหรือ Log เองทีละบรรทัด เราสามารถดาวน์โหลดข้อมูลและใช้ Generative AI (เช่น Gemini, ChatGPT, Claude) ช่วยสรุปสาเหตุและเสนอทางแก้ได้

### 3.1 วิธี Export Logs (จาก Logs Explorer)
1. ไปที่เมนู **Logs Explorer** และใส่ Query ที่ต้องการกรองข้อมูล
2. กดปุ่มไอคอน **Download (ลูกศรชี้ลง)** ที่มุมขวาบนของตารางรายการ Logs
3. เลือก Download เป็นไฟล์แบบ **JSON** หรือ **CSV**
4. แนบไฟล์ให้ AI พร้อม Prompt เช่น:
   > *"นี่คือไฟล์ Log จาก Google Cloud Run ของแอปพลิเคชัน FastAPI ช่วยวิเคราะห์ให้หน่อยว่า: มี Error 5xx เกิดจากอะไรมากที่สุด, Webhook ใช้เวลาตอบกลับเฉลี่ยนานแค่ไหน และมีสัญญาณที่บอกว่าแรมไม่พอหรือไม่"*

### 3.2 วิธี Export Metrics (จาก Cloud Monitoring)
1. ไปที่เมนู **Monitoring > Metrics Explorer** ใน GCP
2. เลือก Metric ที่ต้องการวิเคราะห์ เช่น `run.googleapis.com/container/memory/utilizations`
3. ที่มุมขวาบนของกราฟให้คลิก **More options (จุด 3 จุด)** แล้วเลือก **Download CSV**
4. โยนไฟล์ CSV ให้ AI วิเคราะห์เพื่อหาสาเหตุที่ค่าต่างๆ กระโดดผิดปกติ

## 4. ทำไมเราต้องมี Custom Endpoint `/api/v1/metrics/export` ของระบบเอง?

ข้อมูลที่ได้จาก Cloud Run นั้นดีมากในมุมมองของ **Infrastructure (System Level)** เช่น เรารู้ว่า Request นี้ใช้เวลาตอบกลับนาน 10 วินาที หรือแรมเต็มตอนบ่ายสาม **แต่ Cloud Run จะไม่เข้าใจ Business Logic ของเรา**

Endpoint ภายในระบบของเรา (Issue #62) จะทำหน้าที่เก็บ Metrics เชิง Business Logic เมื่อเราส่งออก (Export) ข้อมูลทั้งจาก Google Cloud Run (CSV/JSON) และจาก Custom Endpoint ภายในของเรา (CSV/JSON) ไปให้ AI ช่วยวิเคราะห์พร้อมๆ กัน AI จะสามารถเชื่อมโยงและตอบปัญหาได้แม่นยำลึกซึ้งยิ่งขึ้น เช่น:

> *"สาเหตุที่แอปพลิเคชัน OOM และช้าถึง 10 วินาทีเมื่อตอนบ่ายสาม เป็นเพราะฟังก์ชัน `fetch_tmd_radar` (จากฝั่ง Backend) ใช้เวลาโหลดรูปจาก API กรมอุตุฯ นานถึง 8 วินาที ประกอบกับมี Request เข้ามาเยอะ ทำให้การดึงรูปใหญ่ๆ หลายรูปถูกสะสมใน RAM จนกินขีดจำกัด 512MiB ในที่สุด"*
