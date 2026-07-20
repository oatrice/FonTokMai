# FonTokMai Development Guide

## การพัฒนาและทดสอบด้วย Two Bots Strategy

เพื่อป้องกันปัญหา Webhook ตีกันระหว่าง Local Development และ Production เราได้วางกลยุทธ์ "Two Bots Strategy" ดังนี้:

### 1. Production Bot (`@FonTokMaiBot`)
- **สถานะ:** ใช้งานจริง
- **Webhook:** ชี้ไปที่ Google Cloud Run URL ที่ Deploy โดยอัตโนมัติจาก GitLab CI (เช่น `https://fontokmai-api-422715657056.asia-southeast1.run.app/api/v1/telegram/webhook`)
- **การอัปเดต:** GitLab CI จะทำการอัปเดต Webhook URL ให้โดยอัตโนมัติเมื่อ Deploy เสร็จ

### 2. Development Bot (`@FonTokMaiDevBot`)
- **สถานะ:** ใช้สำหรับทดสอบและพัฒนาระบบ
- **Webhook:** ชี้ไปที่ Local URL (ใช้ LocalTunnel หรือ Ngrok)

### วิธีการรันระบบเพื่อทดสอบ (Local Development)

1. **เตรียม Environment Variables**
   ในไฟล์ `.env` ของคุณ ให้ตั้งค่า `TELEGRAM_BOT_TOKEN` เป็น Token ของ `@FonTokMaiDevBot`
   ```env
   TELEGRAM_BOT_TOKEN=your_dev_bot_token
   RAINBOW_API_KEY=your_api_key
   ENVIRONMENT=development
   ```

2. **รัน FastAPI Server**
   ```bash
   uvicorn main:app --reload --port 8080
   ```

3. **เปิด LocalTunnel**
   เพื่อให้ Telegram ส่ง Webhook เข้ามาที่ Localhost ได้ เราจะใช้ `localtunnel` (ข้อดีคือสามารถใช้ `--subdomain` ได้หลาย endpoint ฟรีๆ)
   ```bash
   npx localtunnel --port 8080 --subdomain fontokmaidev
   ```
   *ระบบจะสร้าง URL ให้ เช่น `https://fontokmaidev.loca.lt`*

4. **อัปเดต Webhook ของ Dev Bot**
   นำ URL ที่ได้จาก LocalTunnel มาอัปเดตให้ Dev Bot:
   ```bash
   curl -s -X POST "https://api.telegram.org/bot<your_dev_bot_token>/setWebhook" -d url="https://fontokmaidev.loca.lt/api/v1/telegram/webhook"
   ```

5. **เริ่มทดสอบ**
   ส่งข้อความหรือแชร์ Location ไปที่ `@FonTokMaiDevBot` ใน Telegram ระบบ Local ของคุณจะได้รับการแจ้งเตือนและทำงานได้ตามปกติ

## การจำลองและทดสอบฝนตกในช่วงเวลาที่ไม่มีฝนตกจริง (Radar Mock/Backup Testing)

เมื่อจำเป็นต้องทดสอบบอทหรือความถูกต้องของอัลกอริทึมพยากรณ์ฝน แต่ในสภาพอากาศจริงไม่มีฝนตก เราสามารถใช้ประวัติรูปภาพฝนตกจริงที่ย้ายไปไว้ที่โฟลเดอร์ backup บน Firebase Storage แทนได้ดังนี้:

### 1. เปิดโหมดดึงข้อมูลจาก Backup สำหรับบอท (Local Webhook Testing)
ในไฟล์ [backend/.env](file:///Users/oatrice/Software%20Project/FonMaYang/backend/.env) ให้เปิดใช้งานตัวแปรสภาพแวดล้อม:
```env
USE_SKN240_BACKUP=true
```
* **ผลลัพธ์:** เมื่อมีการเรียกใช้เรดาร์สถานีสกลนคร (`skn240`) ระบบจะสลับไปดึงรูปภาพจาก `radar/skn240_backup/` และเลื่อนช่วงเวลาของไฟล์ให้สอดคล้องกับเวลาปัจจุบันโดยอัตโนมัติ ทำให้บอทวิเคราะห์ฝนและแจ้งเตือนพยากรณ์เหมือนพึ่งเกิดขึ้นสด ๆ ร้อน ๆ

### 2. การรันสคริปต์ทดสอบอัลกอริทึมภายนอก (Script Nowcasting Testing)
เรามีสคริปต์ [test_kkn240_run.py](file:///Users/oatrice/Software%20Project/FonMaYang/backend/tests/test_kkn240_run.py) ที่จำลองการหาพื้นที่ฝนตกและการคำนวณ Optical Flow ของเรดาร์แต่ละสถานีผ่านตัวแปรสภาพแวดล้อม `STATION` (รองรับ `kkn240`, `skn240` ฯลฯ โดยค่าเริ่มต้นคือ `kkn240`)

* **รันสคริปต์โดยใช้ Fixture เดิม (รวดเร็ว/ออฟไลน์):**
  ```bash
  # รันสถานีขอนแก่น (kkn240) โหลดจาก test_kkn240_frames.npz
  PYTHONPATH=backend ./backend/.venv/bin/python backend/tests/test_kkn240_run.py

  # รันสถานีสกลนคร (skn240) โหลดจาก test_skn240_frames.npz
  STATION=skn240 PYTHONPATH=backend ./backend/.venv/bin/python backend/tests/test_kkn240_run.py
  ```
* **รันและสั่งอัปเดต Fixture ใหม่จาก Backup บนคลาวด์:**
  หากต้องการดาวน์โหลดและบันทึกชุดรูปภาพจาก backup มาบันทึกทับลงเป็น Fixture ตัวใหม่:
  ```bash
  export $(grep -v '^#' backend/.env | xargs)
  
  # อัปเดตขอนแก่น (kkn240)
  UPDATE_FIXTURE=true PYTHONPATH=backend ./backend/.venv/bin/python backend/tests/test_kkn240_run.py
  
  # อัปเดตสกลนคร (skn240)
  STATION=skn240 UPDATE_FIXTURE=true PYTHONPATH=backend ./backend/.venv/bin/python backend/tests/test_kkn240_run.py
  ```
  *(เมื่ออัปเดตแล้ว ในการรันรอบถัดไปสคริปต์จะใช้ Fixture ท้องถิ่นนี้รันทันทีโดยไม่ต้องโหลดจากอินเทอร์เน็ต)*

* **การสลับใช้งานไฟล์ Fixture อื่นๆ ผ่าน `FIXTURE_PATH`:**
  หากมีการ copy หรือแยกสำรองไฟล์ `.npz` ไว้ (เพื่อไม่ให้โดนเซฟทับ) สามารถส่งตัวแปรสภาพแวดล้อม `FIXTURE_PATH` เพื่อสลับไปดึงข้อมูลจากไฟล์ดังกล่าวได้:
  ```bash
  FIXTURE_PATH=backend/tests/test_kkn240_frames_backup.npz PYTHONPATH=backend ./backend/.venv/bin/python backend/tests/test_kkn240_run.py
  ```

* **การเจาะจงรูปภาพเรดาร์และคัดลอกลง Backup อัตโนมัติ (`TEST_FRAME_URLS`):**
  คุณสามารถระบุรายการ URL ภาพเรดาร์ที่ต้องการให้ระบบนำมาสร้างเป็น Fixture ได้โดยตรง ผ่านตัวแปรสภาพแวดล้อม `TEST_FRAME_URLS` โดยเมื่อดาวน์โหลดมาแล้ว ระบบจะช่วย**อัปโหลดสำเนาไปยังโฟลเดอร์ backup บน Firebase Storage** ให้โดยอัตโนมัติหากยังไม่มีการเก็บสำรองไว้:
  ```bash
  UPDATE_FIXTURE=true TEST_FRAME_URLS="radar/kkn240/kkn240_1784568338.gif,radar/kkn240/kkn240_1784569137.gif,radar/kkn240/kkn240_1784570148.gif,radar/kkn240/kkn240_1784570879.gif,radar/kkn240/kkn240_1784571811.gif,radar/kkn240/kkn240_1784572996.gif" PYTHONPATH=backend ./backend/.venv/bin/python backend/tests/test_kkn240_run.py
  ```
