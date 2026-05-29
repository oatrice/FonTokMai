# Walkthrough: In-Game ModAPI for 0-latency live events (Issue #9)

การพัฒนาระบบเพื่อให้แอป CastBuddy ของคุณสามารถรับข้อมูลแบบ Real-time แท้จริงได้ดำเนินการเสร็จสิ้นเรียบร้อยแล้ว! 

เราได้เปลี่ยนจากการอ่านไฟล์ `.wowsreplay` มาใช้การเปิดเซิร์ฟเวอร์รับ Webhook จาก In-game Mod ซึ่งจะลด Latency ลงเหลือใกล้เคียงศูนย์

## 🛠 สิ่งที่ดำเนินการ (Changes Made)

1. **ฝั่ง Server (FastAPI)**
   - เพิ่ม Endpoint `POST /api/events` ใน `api/server.py` เพื่อรับ Event Payload แบบ JSON
   - เพิ่มกระบวนการตรวจสอบสถานะ หากกด **Start** ในแอปแล้วถึงจะเริ่มรับ Event เพื่อป้องกันข้อมูลเข้ามากวนตอนเราพักสตรีม
   - ดำเนินการพัฒนาแบบ TDD พร้อมเขียน Automated Test ให้กับ Endpoint นี้ (`test_post_events_returns_ok`) ผลลัพธ์ผ่าน 100%

2. **ฝั่ง In-game Mod (Python 2.7)**
   - สร้างไฟล์ต้นแบบสำหรับ Mod: [CastBuddyMod.py](file:///Users/oatrice/Software-projects/CastBuddy/wows_mod/CastBuddyMod.py) 
   - รองรับโค้ดของ BigWorld Engine ซึ่งใช้งาน Python 2.7 (โดยใช้ `urllib2` ไม่พึ่งพิง `requests`)
   - มีฟังก์ชันหลักอย่าง `send_event()` สำหรับแพ็คข้อมูลต่างๆ เช่น `battle_start`, `ship_destroyed` ออกมาเป็น JSON และยิงมาที่พอร์ต 8000 แบบสดๆ

---

## 🔍 วิธีการทดสอบและนำไปติดตั้ง (Manual Verification)

เพื่อให้เห็นผลการทำงานได้ชัดเจน คุณสามารถทดสอบได้ตามขั้นตอนดังนี้:

### 1. รัน CastBuddy Server
เปิด Terminal เข้าโฟลเดอร์โปรเจกต์ และสั่ง:
```bash
uv run fastapi dev api/server.py
```
> [!NOTE]  
> อย่าลืมกดปุ่ม "Start" บน Dashboard ของ CastBuddy เพื่อให้ `state.is_running` เป็น `True` มิฉะนั้น Webhook จะถูกบล็อก

### 2. การติดตั้ง Mod ในตัวเกม World of Warships
1. ไปที่โฟลเดอร์เกมของ World of Warships
2. เข้าไปที่โฟลเดอร์ `bin/<build_number>/res_mods/`
3. ก๊อปปี้ไฟล์ `wows_mod/CastBuddyMod.py` และ `wows_mod/config.json` ไปใส่ตามโครงสร้าง Mod ของเกม 
4. **หากต้องการรันข้ามเครื่อง (Cross-Machine Setup):**
   - ฝั่ง Server ให้รันเซิร์ฟเวอร์ด้วยคำสั่ง `uv run fastapi dev api/server.py --host 0.0.0.0`
   - ฝั่ง Mod ให้แก้ไขไฟล์ `config.json` แล้วเปลี่ยนจาก `127.0.0.1` เป็น Local IP ของเครื่อง Mac เช่น `"http://192.168.1.50:8000/api/events"`

### 3. ทดสอบการเชื่อมต่อ
คุณสามารถส่ง Event ทดสอบแบบ Manual ไปที่แอปของคุณได้โดยตรง เพื่อเช็คความถูกต้องของ TTS และ UI
```bash
curl -X POST http://127.0.0.1:8000/api/events \
  -H "Content-Type: application/json" \
  -d '{"type": "ship_destroyed", "killer": "player1", "victim": "enemy1"}'
```
ถ้าสำเร็จ OBS และหน้า Dashboard จะแสดงข้อความมุกตลก และมีการเล่นเสียง TTS ออกมาทันที!

---

> [!TIP]
> ตอนนี้เรายังคงเก็บฟังก์ชัน `simulation_loop` ในแอปเอาไว้สำหรับโหมดนักพัฒนา เพื่อให้คุณสามารถทดสอบ UI ได้โดยไม่ต้องเปิดเกม และ Endpoint ใหม่ `/api/events` ก็พร้อมที่จะทำงานร่วมกันได้เลย
