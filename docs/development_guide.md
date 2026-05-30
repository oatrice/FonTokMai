# FonTokMai Development Guide

## การพัฒนาและทดสอบด้วย Two Bots Strategy

เพื่อป้องกันปัญหา Webhook ตีกันระหว่าง Local Development และ Production เราได้วางกลยุทธ์ "Two Bots Strategy" ดังนี้:

### 1. Production Bot (`@FonTokMaiBot`)
- **สถานะ:** ใช้งานจริง
- **Webhook:** ชี้ไปที่ Google Cloud Run URL ที่ Deploy โดยอัตโนมัติจาก GitLab CI (เช่น `https://fontokmai-api-422715657056.us-central1.run.app/api/v1/telegram/webhook`)
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
   cd backend
   uvicorn main:app --reload --port 8000
   ```

3. **เปิด LocalTunnel**
   เพื่อให้ Telegram ส่ง Webhook เข้ามาที่ Localhost ได้ เราจะใช้ `localtunnel` (ข้อดีคือสามารถใช้ `--subdomain` ได้หลาย endpoint ฟรีๆ)
   ```bash
   npx localtunnel --port 8000 --subdomain fontokmaidev
   ```
   *ระบบจะสร้าง URL ให้ เช่น `https://fontokmaidev.loca.lt`*

4. **อัปเดต Webhook ของ Dev Bot**
   นำ URL ที่ได้จาก LocalTunnel มาอัปเดตให้ Dev Bot:
   ```bash
   curl -s -X POST "https://api.telegram.org/bot<your_dev_bot_token>/setWebhook" -d url="https://fontokmaidev.loca.lt/api/v1/telegram/webhook"
   ```

5. **เริ่มทดสอบ**
   ส่งข้อความหรือแชร์ Location ไปที่ `@FonTokMaiDevBot` ใน Telegram ระบบ Local ของคุณจะได้รับการแจ้งเตือนและทำงานได้ตามปกติ
