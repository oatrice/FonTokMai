# คู่มือการตรวจสอบด้วยตนเอง (Manual Verification Guide)

- Step 1: เปิด Terminal แล้วไปยังโฟลเดอร์โปรเจกต์ จากนั้นรันคำสั่ง `cd backend && source venv/bin/activate && pytest tests/test_services.py -v` เพื่อให้แน่ใจว่าลอจิกการแกะข้อมูลใหม่ทำงานได้ปกติ
- Step 2: ตรวจสอบการดึงข้อมูลจากเซิร์ฟเวอร์ Rainbow จริง โดยกำหนดค่าตัวแปร `export RAINBOW_API_KEY="API_KEY_จริง"` แล้วใช้โค้ด Python เพื่อทดสอบยิงไปหา Endpoint (พิกัดอุดรธานี):
  ```bash
  python -c "
  import asyncio
  from app.services.rainbow import RainbowService
  async def test():
      service = RainbowService()
      print(await service.predict_rain_by_location(17.8399, 102.574))
  asyncio.run(test())"
  ```
- Step 3: เปิดหน้าต่าง Terminal ใหม่ แล้วสตาร์ทตัว FastAPI Server ให้ทำงานด้วยคำสั่ง `cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8080`
- Step 4: ยิงคำสั่ง `curl` เพื่อจำลองการส่ง Webhook Location (พิกัดอุดรธานี) จาก Telegram มาที่แอปของเรา:
  ```bash
  curl -X POST "http://localhost:8080/api/v1/telegram/webhook" \
  -H "Content-Type: application/json" \
  -d '{"update_id":123,"message":{"message_id":1,"from":{"id":123},"chat":{"id":123,"type":"private"},"date":1737570600,"location":{"latitude":17.8399,"longitude":102.574}}}'
  ```
- Step 5: (End-to-End Test) ในขณะที่รันเซิร์ฟเวอร์อยู่ ให้เปิด Terminal อีกหน้าต่างรัน `npx localtunnel --port 8080` จากนั้นนำ URL ที่ได้ไปตั้งค่า Webhook ด้วยคำสั่ง `curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=<LT_URL>/api/v1/telegram/webhook"` แล้วลองเปิดแอป Telegram ส่งพิกัดให้บอทจริงๆ
- Expected Result: 
  1. Unit tests จะต้องแสดงผล Passed 100%
  2. สคริปต์ทดสอบเรียก API จะต้องไม่พ่น Error 404 ออกมา และต้องคืนค่า Dictionary ที่มี `predictions`, `intensity` และ `duration_minutes` อย่างถูกต้อง
  3. เซิร์ฟเวอร์ API ควรส่งค่าตอบกลับ curl เป็น `{"status": "ok"}`
  4. สำหรับการเทส E2E (Step 5) แชทบอทในแอป Telegram จะต้องตอบกลับข้อมูลสภาพอากาศได้อย่างรวดเร็วและแม่นยำ
