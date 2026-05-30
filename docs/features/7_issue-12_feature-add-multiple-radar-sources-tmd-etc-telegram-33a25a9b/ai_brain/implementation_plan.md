# Issue #12: Multi-Source Radar References

เพิ่มแหล่งอ้างอิงเรดาร์ฝน (Source/Ref) จากหลายๆ แหล่งในคำสั่ง `/radar` และการแจ้งเตือนเชิงรุก เพื่อให้ผู้ใช้สามารถตรวจสอบข้อมูลจากแหล่งที่เชื่อถือได้ด้วยตัวเอง

## 📝 User Review Required

> [!NOTE]
> ฟีเจอร์นี้จะนำ Inline Keyboard Button มาใช้กับลิงก์เรดาร์ต่างๆ เพื่อความสวยงามและไม่ทำให้ข้อความยาวจนเกินไป 
> แหล่งข้อมูลที่เลือกมานำเสนอ ได้แก่:
> 1. **Zoom Earth**: Interactive map ที่เลื่อนดูพิกัดตัวเองได้
> 2. **Windy**: Weather radar ของ Windy ที่ Interactive รับค่าพิกัดได้
> 3. **TMD Radar**: ลิงก์ตรงไปยังกรมอุตุนิยมวิทยาเพื่อ Fact check แบบ official (ไม่ Interactive แต่แม่นยำสูง)

## 📌 Proposed Changes

### `backend/app/routers/webhook.py`
#### [MODIFY] [webhook.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/webhook.py)
- ปรับปรุงฟังก์ชัน `handle_radar_command` 
- ลบ URL ยาวๆ ออกจากข้อความ Text หลัก และเปลี่ยนไปสร้าง `reply_markup` ที่เป็น Inline Keyboard โดยใช้โครงสร้าง:
  ```json
  {
    "inline_keyboard": [
      [{"text": "📡 Zoom Earth", "url": "..."}],
      [{"text": "🌪️ Windy Radar", "url": "..."}],
      [{"text": "🇹🇭 TMD Radar", "url": "https://weather.tmd.go.th/"}]
    ]
  }
  ```

### `backend/app/scheduler_tasks.py`
#### [MODIFY] [scheduler_tasks.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/scheduler_tasks.py)
- ปรับปรุงข้อความในส่วนแจ้งเตือนฝนเชิงรุก (Proactive Alert)
- แทนที่จะใส่ลิงก์ Zoom Earth ต่อท้ายข้อความเฉยๆ จะส่ง Inline Keyboard แบบเดียวกับ `/radar` แนบไปด้วย

## 🧪 Verification Plan

### Automated Tests
- อัปเดต Unit Test `test_webhook.py` ให้ครอบคลุมการตรวจสอบ `reply_markup` ในฟังก์ชัน mock `send_telegram_message`
- อัปเดต Unit Test `test_scheduler.py` ให้ครอบคลุมการตรวจสอบ `reply_markup` เช่นกัน

### Manual Verification
- รัน server ในเครื่อง และจำลองการส่งคำสั่ง `/radar`
- ตรวจสอบว่ามีปุ่มปรากฏขึ้นอย่างถูกต้อง และสามารถคลิกไปยังแต่ละ Web Source ได้
- รันสคริปต์ `force_test_alert.py` เพื่อจำลองการส่ง Proactive Alert และดูปุ่มเรดาร์ที่แจ้งเตือน
