# Insights API Comparison Feature (Batch E)

ระบบนี้จะช่วยแก้ปัญหาผู้ใช้เจอ False Positive ด้วยการดึงข้อมูลจากทุก API (Tomorrow.io, Rainbow Local, Rainbow Global) มาแสดงเปรียบเทียบพร้อมกัน เพื่อให้ผู้ใช้ตัดสินใจได้เองว่าสภาพอากาศตอนนี้น่าจะอิงจากค่ายไหนดี

## User Review Required

> [!IMPORTANT]
> **ข้อจำกัดของ Telegram Table:** Telegram ไม่รองรับการแสดงผลตาราง (Table) แบบ Markdown ทั่วไปในข้อความแชท แผนนี้จึงเสนอให้ใช้การจัด Format ข้อความด้วย `Monospace block` (`<pre>`) หรือจัดเรียงเป็น List ที่อ่านง่ายแทน รบกวนยืนยันว่าโอเคกับข้อจำกัดนี้ไหมครับ?

## Open Questions

> [!TIP]
> 1. ปุ่ม **"📊 Insights (เปรียบเทียบ API)"** ควรแสดงให้ผู้ใช้ทุกคนเห็นเลยไหมครับ? หรือจะสงวนไว้ให้เฉพาะผู้ดูแลระบบ (Developer) เหมือนปุ่ม "ดูข้อมูลดิบ" ?
> 2. ถ้าหากมี API ตัวไหน Error หรือ Timeout ไป (เช่น Tomorrow.io คีย์พัง) ให้แสดงผลในตารางว่า `Error` ข้ามไปเลยใช่ไหมครับ?

## Proposed Changes

### 1. `backend/app/services/weather_manager.py`
เพิ่มฟังก์ชันใหม่สำหรับการดึงข้อมูลขนานกัน (Concurrent) เพื่อไม่ให้ผู้ใช้ต้องรอนาน:
#### [MODIFY] [weather_manager.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/weather_manager.py)
- สร้างเมธอด `compare_apis(self, lat: float, lng: float)` 
- ใช้ `asyncio.gather` สั่งให้ `TomorrowService`, `RainbowService (local)`, และ `RainbowService (global)` ยิง API ไปพร้อมๆ กัน
- สกัดเอาตัวแปรสำคัญจากแต่ละค่าย (เช่น ฝนจะตกในกี่นาที, ความรุนแรงสูงสุด) มาจัดใส่ Dictionary เพื่อเตรียมส่งให้ Telegram

### 2. `backend/app/services/telegram.py`
เพิ่มปุ่ม Insights ลงใน Keyboard:
#### [MODIFY] [telegram.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/telegram.py)
- ในฟังก์ชัน `get_radar_inline_keyboard` หรือในข้อความแจ้งเตือนฝนตก ให้เพิ่มปุ่ม `callback_data` รูปแบบ `insights_{lat}_{lng}`

### 3. `backend/app/routers/webhook.py`
จัดการตอนที่ผู้ใช้กดปุ่ม:
#### [MODIFY] [webhook.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/webhook.py)
- เพิ่มเงื่อนไขจับ `callback_data` ที่ขึ้นต้นด้วย `insights_`
- เรียกใช้ `compare_apis`
- สร้างข้อความเปรียบเทียบ เช่น:
  ```text
  📊 เปรียบเทียบข้อมูลพยากรณ์ฝน

  🌦️ Tomorrow.io
  - สถานะ: ตกปานกลาง (12.5 mm/hr)
  - เริ่มตกใน: 15 นาที

  🌧️ Rainbow (Local)
  - สถานะ: ไม่มีฝน (0.0 mm/hr)
  - เริ่มตกใน: -

  ⛈️ Rainbow (Global)
  - สถานะ: Error (ไม่สามารถเชื่อมต่อได้)
  ```
- ส่งข้อความกลับไปให้ผู้ใช้ในแชท

## Verification Plan

### Manual Verification
1. ส่ง Location เข้าบอท แล้วกดปุ่ม `📊 Insights (เปรียบเทียบ API)`
2. ตรวจสอบว่าบอทประมวลผลไม่เกิน 3-5 วินาที (เพราะยิง API ขนานกัน)
3. ตรวจสอบว่าข้อความเปรียบเทียบแสดงข้อมูลของ 3 API ครบถ้วนและอ่านง่าย
4. ลองปิดเน็ต/เปลี่ยน API Key ให้พัง 1 ตัว แล้วกด Insights ดูว่าระบบแสดงสถานะ Error ของค่ายนั้นถูกต้องและไม่ดับทั้งระบบ
