# เป้าหมาย (Goal Description)
ปรับปรุงแจ้งเตือนฝนตกและคำสั่ง `/radar` ทาง Telegram เพื่อเพิ่มปุ่ม Inline Keyboard สำหรับตรวจสอบเรดาร์จากหลายแหล่ง (Zoom Earth, Windy, TMD Radar) และเพิ่มปุ่มพิเศษ "📊 ดูข้อมูลดิบ" สำหรับนักพัฒนาเพื่อใช้ดึงข้อมูลพยากรณ์ล่วงหน้า 120 นาทีจาก Rainbow API

## ข้อเสนอการเปลี่ยนแปลง (Proposed Changes)

### บริการ Telegram (`backend/app/services/telegram.py`)
- สร้างฟังก์ชัน `get_radar_inline_keyboard` สำหรับสร้าง UI ปุ่มกดลิงก์เรดาร์ต่างๆ
- สร้างฟังก์ชัน `send_telegram_document` สำหรับส่งไฟล์ JSON กลับไปที่แชท Telegram
- เพิ่มการรับตัวแปร `DEVELOPER_CHAT_IDS` เพื่อตรวจสอบสิทธิ์

### ระบบ Webhook (`backend/app/routers/webhook.py`)
- [MODIFY] เรียกใช้ `get_radar_inline_keyboard` เมื่อผู้ใช้พิมพ์คำสั่ง `/radar`
- [MODIFY] เพิ่มเงื่อนไขตรวจสอบ Callback Query ที่ขึ้นต้นด้วย `raw_` เพื่อดึงข้อมูลดิบจาก API และส่งเป็นไฟล์กลับไป

### ระบบแจ้งเตือนอัตโนมัติ (`backend/app/scheduler_tasks.py`)
- [MODIFY] เมื่อตรวจพบฝนกำลังจะตก ให้แนบปุ่ม Inline Keyboard เข้าไปกับข้อความแจ้งเตือนด้วย พร้อมเช็คว่าเป็นนักพัฒนาหรือไม่

## แผนการทดสอบ (Verification Plan)
### การทดสอบแบบอัตโนมัติ (Automated Tests)
- รัน `pytest` เพื่อทดสอบฟังก์ชันต่างๆ
### การทดสอบด้วยตนเอง (Manual Verification)
- อ้างอิงจากไฟล์ `manual_verification.md` ในโฟลเดอร์เดียวกัน
