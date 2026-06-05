# เป้าหมาย: ขยายขอบเขต Issue 49 (Evaluate API Accuracy)

จากความต้องการของคุณที่อยากให้สามารถ "evaluate แต่ละ api data sources ให้อยู่ใน model ว่ามีความแม่นยำแค่ไหน" ระบบจะทำการสร้าง Model เพื่อเก็บคะแนนความแม่นยำ และนำคะแนนนี้ไปใช้สำหรับการ Auto-select แหล่งข้อมูลที่ดีที่สุดโดยอัตโนมัติ

## Proposed Architecture (การออกแบบระบบ)

เราจะใช้หลักการ **Feedback-driven Auto Selection** คือให้ความแม่นยำถูกคำนวณจากจำนวนครั้งที่ทายถูกเทียบกับจำนวนครั้งที่ถูกแจ้งว่า "False Alarm (ทายผิด)" โดยผู้ใช้จริง หรือจากระบบตรวจสอบอัตโนมัติ

### 1. Database Model ใหม่ (`ApiReliability`)
สร้าง Table ใหม่ใน `app/models.py` เพื่อเก็บสถิติของแต่ละ API:
- `endpoint` (String, PK): เช่น "xweather", "tomorrow", "rainbow-local", "open-meteo"
- `total_queries` (Integer): จำนวนครั้งที่ API นี้ถูกดึงข้อมูลไปใช้แจ้งเตือน
- `false_alarms` (Integer): จำนวนครั้งที่ถูก Report ว่าเป็น False Alarm
- `accuracy_score` (Float): คะแนนความแม่นยำ (เช่น 0.0 - 1.0 หรือ 0% - 100%) คำนวณจาก `1 - (false_alarms / total_queries)`

### 2. ปรับปรุง `save_feedback` (User Feedback Loop)
เมื่อผู้ใช้กดปุ่ม ❌ แจ้งเตือนผิดพลาด (False Alarm) บน Telegram:
- ระบบจะไม่เพียงแค่บันทึกลง `UserFeedback` แต่จะวิ่งไปอัปเดตค่า `false_alarms` ให้กับ API นั้นๆ ใน `ApiReliability`
- คำนวณ `accuracy_score` ใหม่ทันที

### 3. ปรับปรุง Algorithm ของ `WeatherManager` (Auto-Select)
แทนที่จะใช้ Hardcoded Fallback Order (Xweather -> Tomorrow -> Rainbow ...):
- เมื่อรัน `predict_rain()` ระบบจะ query ข้อมูล `accuracy_score` ของทุก API ออกมาจัดเรียง (Sort by highest score)
- ระบบจะพยายามดึงข้อมูลจาก API ที่มีคะแนนสูงสุดก่อน (Auto-select)
- หาก API ที่ดีที่สุดเชื่อมต่อไม่ได้ (Timeout/Error) จึงค่อย Fallback ไปหาอันดับ 2 ตามลำดับคะแนน
- เมื่อนำไปใช้สำเร็จ (และส่งแจ้งเตือน) จะบวกค่า `total_queries` ให้ API นั้น

### 4. ปรับปรุง Compare API (Issue #49 Evaluation)
ในปุ่ม "📊 เทียบข้อมูล" และ Endpoint `/api/v1/weather/compare`:
- จะมีการแนบค่า `accuracy_score` ที่อยู่ใน Database Model ออกมาแสดงผลด้วย
- **หน้าตาบน Telegram จะเป็นแบบนี้:**
  ```text
  🔹 Tomorrow.io (ความแม่นยำ: 95.5%):
     💧 ปริมาณฝนสูงสุด: 15.0 mm/hr
     ...
  🔹 Rainbow Local (ความแม่นยำ: 80.2%):
     💧 ปริมาณฝนสูงสุด: 20.0 mm/hr
     ...
  ```

---

## User Review Required

> [!IMPORTANT]
> **การนับ Total Queries (ความสำเร็จ):**
> การที่จะหาความแม่นยำได้ เราต้องรู้ตัวหาร (Total Queries) คุณอยากให้ "นับ Total Queries +1" เฉพาะตอนที่ API นั้นทายว่า **"ฝนตก" (Max Rain > 0)** หรือนับรวมตอนที่ทายว่า **"ฝนไม่ตก" (All-Clear)** ด้วยครับ?
> *(แนะนำ: เริ่มต้นให้นับเฉพาะตอนที่ทายว่า "ฝนตก" ก่อน เพราะผู้ใช้มักจะกด False Alarm เฉพาะตอนที่ระบบเตือนว่าฝนจะตกแต่ไม่ตกจริง)*

> [!WARNING]
> **ข้อมูลเริ่มต้น (Cold Start):**
> ในช่วงแรกที่สร้างตารางใหม่ `total_queries` จะเป็น 0 ระบบควรให้คะแนนเริ่มต้น (Initial Score) แก่ API ระดับ Premium สูงกว่าไหมครับ? 
> เช่น บังคับให้ Xweather มี Default Score = 1.0, Tomorrow = 0.9, Open-Meteo = 0.8 เพื่อให้ช่วงแรกระบบวิ่งไปหาตัวที่ดีที่สุดก่อน

หากคุณเห็นด้วยกับแนวทางนี้ (และมี Feedback ต่อคำถามด้านบน) ผมจะดำเนินการสร้าง Model ลง Database, ทำ Migration, และแก้ Algorithm ให้เลยครับ!
