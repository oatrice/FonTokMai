# แผนการพัฒนา Batch F: Xweather Integration & Advanced Alerts

เอกสารฉบับนี้ร่างแผนการทำงานสำหรับ **Batch F** (Issue #32 - #35) ซึ่งจะมุ่งเน้นที่การเปลี่ยนผ่านระบบการพยากรณ์และการเตือนภัยหลักไปใช้ **Xweather API** แทนระบบปัจจุบัน เพื่อเพิ่มความแม่นยำในการทำ Nowcasting พร้อมเพิ่มฟีเจอร์เตือนภัยขั้นสูง เช่น ฟ้าผ่า และพายุ

> [!IMPORTANT]
> **User Review Required**
> กรุณาตรวจสอบแผนการทำงานนี้และอนุญาตให้ดำเนินการต่อ หากมีข้อเสนอแนะหรือการปรับแก้ สามารถแจ้งได้ทันที

---

## 📌 สรุปขอบเขตงาน (Scope of Work)
การพัฒนาใน Batch F ประกอบไปด้วยการดำเนินการใน 4 Issues หลัก:
1. **Issue #32:** สร้าง Service คุยกับ Xweather API (`minutecast`) และอัปเดตระบบ Fallback
2. **Issue #33:** เพิ่มการเตือนภัยพิบัติและน้ำท่วมขังฉับพลัน (`advisories`)
3. **Issue #34:** เพิ่มการเตือนภัยพายุฟ้าคะนองรุนแรงและฟ้าผ่าในระยะใกล้ (`lightning/closest`)
4. **Issue #35:** เพิ่มการติดตามเส้นทางของกลุ่มพายุและคำนวณเวลาที่พายุจะมาถึง (`stormcells`)

---

## 🛠️ รายละเอียดแผนการพัฒนา (Proposed Changes)

### 1. การตั้งค่า Environment & Configuration
> **[MODIFY]** `backend/.env.example`
> **[MODIFY]** `backend/app/main.py` หรือส่วนที่โหลด Settings
- เพิ่ม Environment Variables สำหรับ Xweather API:
  - `XWEATHER_CLIENT_ID`
  - `XWEATHER_CLIENT_SECRET`
  - `XWEATHER_ENABLED` (Feature Flag เพื่อเปิด/ปิดการใช้งาน Xweather)

### 2. สร้าง Xweather Service (Issue #32)
> **[NEW]** `backend/app/services/xweather.py`
สร้างคลาส `XweatherService` ที่สืบทอดจาก `BaseWeatherService` โดยมีการทำงานดังนี้:
- **`predict_rain_by_location`**: เรียกใช้งาน endpoint `minutecast`
- **`get_advanced_alerts`**: ดึงข้อมูล `advisories`, `lightning/closest`, และ `stormcells`
- **Circuit Breaker (Quota Limit Protection)**: หากได้รับ HTTP Status `429 Too Many Requests` (Quota เต็ม) หรือ `403 Forbidden` จาก Xweather ตัว Service จะปรับสถานะตัวเองเป็นระงับการทำงานชั่วคราว (Circuit Open) อัตโนมัติเป็นเวลาที่กำหนด หรือจนกว่าจะถึงรอบบิลถัดไป เพื่อหลีกเลี่ยงการเสียเวลาเชื่อมต่อ (Timeout) ในทุกๆ ลูป

### 3. อัปเดต Weather Manager & Fallback Chain
> **[MODIFY]** `backend/app/services/weather_manager.py`
- ปรับปรุง Chain of Responsibility ใหม่ เป็น:
  **Xweather** ➡️ **Tomorrow.io** ➡️ **Rainbow Local** ➡️ **Rainbow Global**
- หากค่า `XWEATHER_ENABLED` เป็น `false` หรือสถานะ Circuit Breaker เปิดอยู่ ระบบจะข้าม Xweather แล้วไปใช้ Tomorrow.io ทันที (Graceful Degradation)

### 4. ปรับปรุง Scheduler & Alert Logic (Issue #33, #34, #35)
> **[MODIFY]** `backend/app/scheduler_tasks.py`
- ในลูปการตรวจสอบฝน ระบบจะทำการส่งข้อความหลัก (Main Weather Alert) ไปก่อนตามปกติ
- หากมีข้อมูลเตือนภัยขั้นสูง (เช่น มีฟ้าผ่า หรือมี Advisory) ระบบจะส่ง **ข้อความแจ้งเตือนฉุกเฉินแยกอีก 1 กล่อง (Separate Box)** ตามหลังข้อความหลักไปทันที เพื่อให้ข้อมูลไม่ปะปนกันและมีความโดดเด่นสะดุดตา

---

## 🧪 แผนการทดสอบและตรวจสอบ (Verification Plan)

### Automated Tests
- เขียน Unit Test เพิ่มใน `tests/` เพื่อจำลอง (Mock) การตอบกลับของ Xweather API สำหรับแต่ละ Endpoint (`minutecast`, `advisories`, `lightning`, `stormcells`)
- ทดสอบ Fallback Chain ใน `WeatherManager` เพื่อให้แน่ใจว่าเมื่อบังคับให้ Xweather เกิดข้อผิดพลาด ระบบยังสามารถสลับไป Tomorrow.io ได้สำเร็จ

### Manual Verification
- เรียกใช้ไฟล์สคริปต์บังคับแจ้งเตือน (เช่น `force_test_alert.py`) โดยจำลองค่าละติจูด/ลองจิจูดในพื้นที่ที่มีพายุ หรือใช้ Mock Data เพื่อดูการแสดงผลของข้อความใน Telegram
- ตรวจสอบรูปแบบข้อความที่ได้รับใน Telegram (UX/UI ของการแจ้งเตือน) ว่าไม่รกเกินไปและอ่านง่าย

---

## ❓ คำถามเพิ่มเติม (Open Questions)

1. **โควต้า 15,000 requests/เดือน:** หากมีการตรวจสอบทุกๆ X นาที ผู้ใช้จำนวนมากอาจทำให้โควต้าเต็มเร็ว มีความต้องการที่จะปรับลดความถี่ในการดึงข้อมูลขั้นสูง (Advisories, Lightning) หรือทำ Cache แยกไว้เฉพาะระดับเขต (District) ตั้งแต่ใน Batch F นี้เลยหรือไม่? หรือจะให้เริ่มแบบปกติดึงตรงทุกรอบไปก่อนครับ?
2. **การแจ้งเตือนพายุแยกต่างหาก:** ต้องการให้การเตือนฟ้าผ่าหรือ Advisory **ส่งเป็นข้อความแยก** (Immediate Alert ทันที) หรือให้แนบรวมไปกับข้อความแจ้งเตือน "ฝนจะตก" ในหน้าต่างเวลา 60 นาทีตามปกติครับ? (เบื้องต้นแผนคือการดึงมาแนบรวมกับข้อความเตือนฝนเพื่อลดความถี่ในการเด้งแจ้งเตือน)
