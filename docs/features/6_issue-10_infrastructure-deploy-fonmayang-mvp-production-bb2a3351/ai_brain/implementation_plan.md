# Feature: Multi-Source Radar References

เพิ่มแหล่งอ้างอิงเรดาร์ฝน (Source/Ref) จากหลายๆ แหล่งในคำสั่ง `/radar` เพื่อให้ผู้ใช้สามารถตรวจสอบข้อมูลจากแหล่งที่เชื่อถือได้ด้วยตัวเอง

## Requirement Analysis

**ปัญหาปัจจุบัน:** 
คำสั่ง `/radar` แจ้งเพียง Link ของ Zoom Earth ซึ่งแม้จะใช้งานง่ายและเห็นภาพรวมได้ดี แต่ผู้ใช้อาจต้องการความแม่นยำเพิ่มเติมจากการตรวจสอบข้อมูลจากหน่วยงานราชการหรือแหล่งข้อมูลอื่นประกอบการตัดสินใจ (Fact check)

**เป้าหมาย:**
เพิ่มรายการแหล่งอ้างอิงเรดาร์สภาพอากาศที่น่าเชื่อถือลงในข้อความที่ตอบกลับจากคำสั่ง `/radar` (และอาจรวมถึงข้อความแจ้งเตือนฝนตกด้วย)

**แหล่งข้อมูลที่แนะนำ (Sources/Refs):**
1. **Zoom Earth (Interactive)**: (มีอยู่แล้ว) ใช้พิกัดผู้ใช้เพื่อแสดงภาพรวมแบบ Interactive
2. **กรมอุตุนิยมวิทยา (TMD)**: 
   - เรดาร์รวมทั่วประเทศ: `https://weather.tmd.go.th/`
   - *ข้อจำกัด*: TMD ไม่มี URL parameter แบบ Interactive ที่รับค่า lat/lng แล้ว zoom ไปตรงนั้นได้ทันที จึงต้องให้ลิงก์หน้าหลัก
3. **Windy (Weather Radar)**:
   - URL สามารถรับพิกัดได้: `https://www.windy.com/-Weather-radar-radar?radar,{lat},{lng},9`
4. **กทม. เรดาร์ (BMA Radar)** (เป็น Option):
   - `http://weather.bangkok.go.th/radar/` (มีประโยชน์มากสำหรับผู้ใช้ในกรุงเทพฯ)

## Proposed Changes

### `backend/app/routers/webhook.py`
#### [MODIFY] `webhook.py`
- แก้ไขฟังก์ชัน `handle_radar_command(chat_id: int)` 
- ปรับปรุงข้อความ (Text) ให้มีลักษณะเป็นรายการ (List) ของช่องทางต่างๆ
  - 📡 Zoom Earth (Interactive)
  - 🌪️ Windy (Interactive)
  - 🇹🇭 กรมอุตุนิยมวิทยา (TMD)
- (ถ้าต้องการ) อาจส่งเป็น Inline Keyboard Button แทนที่จะเป็นข้อความยาวๆ เพื่อความสวยงามใน Telegram UI

### `backend/app/scheduler_tasks.py`
#### [MODIFY] `scheduler_tasks.py`
- ควรอัปเดตข้อความแจ้งเตือนฝนเชิงรุก (Proactive Alert) ให้รวมลิงก์เหล่านี้ด้วยหรือไม่? 
- *ข้อเสนอแนะ*: เพื่อไม่ให้ข้อความแจ้งเตือนยาวเกินไป อาจแนบแค่ Zoom Earth + TMD หรือทำเป็นปุ่ม Inline Keyboard

## Final Decisions
- **รูปแบบการแสดงผล:** ใช้เป็น **ปุ่มกด (Inline Keyboard)** เพื่อความสะอาดตา
- **ขอบเขตการทำงาน:** ให้แสดงปุ่มกดเหล่านี้ **ทั้งใน** ข้อความตอบกลับคำสั่ง `/radar` และข้อความแจ้งเตือนอัตโนมัติ (Proactive Alerts)

