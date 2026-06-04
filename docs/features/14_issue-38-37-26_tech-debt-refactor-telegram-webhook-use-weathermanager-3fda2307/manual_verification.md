# Manual Verification Guide — Batch D (Issue #38, #37, #26)

## Prerequisites

- Local server รันอยู่: `cd backend && uvicorn app.main:app --reload`
- Telegram Bot Token ถูกต้องใน `.env`
- มีบอท Telegram ที่เชื่อมกับ webhook ไปยัง `localhost` ผ่าน `ngrok` หรือใช้ `curl` จำลองได้

---

## Test 1 — Issue #38: Webhook ใช้ WeatherManager (Fallback Chain)

**วัตถุประสงค์:** ยืนยันว่า Webhook ใช้ `WeatherManager` แล้วจริง ไม่ใช่ `RainbowService` โดยตรง

### Step 1: ตรวจสอบ Log เมื่อ TOMORROW_API_KEY ว่าง

เปิด `.env` แล้วลบหรือตั้งค่า `TOMORROW_API_KEY=INVALID_KEY` แล้ว restart server

### Step 2: ส่งพิกัดเข้าบอท Telegram

ส่ง location ไปในแชทบอท

### Step 3: ดู Log ในเทอร์มินัล

```
Expected Result:
[WARNING] Tomorrow.io failed: ... Falling back to Rainbow (Local).
[WARNING] Rainbow Local failed: ... Falling back to Rainbow (Global).
[INFO] Successfully fetched weather from Rainbow (Global)
```

**หากเห็น log fallback → Issue #38 ทำงานถูกต้อง** ✅

### Step 4: คืนค่า API Key กลับ แล้วส่ง location ซ้ำ

```
Expected Result:
[INFO] Successfully fetched weather from Tomorrow.io
```

---

## Test 2 — Issue #37: Loading State (Immediate Reply)

**วัตถุประสงค์:** ยืนยันว่าบอทตอบ "กำลังประมวลผล..." ทันทีก่อนผลลัพธ์จะออก

### Step 1: เปิด Telegram แล้วส่ง Location ไปบอท

กด Attachment icon → Location → ส่ง Current Location

### Step 2: จับเวลา

สังเกตว่าบอทตอบกลับ **ภายใน 1 วินาที** ด้วยข้อความประมาณ:

```
Expected Result (ทันที):
⏳ กำลังประมวลผลเรดาร์และพยากรณ์อากาศ กรุณารอสักครู่...
```

### Step 3: รอจนประมวลผลเสร็จ (11-15 วินาที)

```
Expected Result (หลังประมวลผล):
ข้อความเดิม "⏳ กำลังประมวลผล..." จะถูกแก้ไขเป็นผลพยากรณ์จริง เช่น:
🌧️ ฝนกำลังเคลื่อนมาทางทิศของคุณ จะเริ่มตกในอีก 25 นาที (ตรวจสอบด้วย: Tomorrow.io)
💧 ความรุนแรง: ปานกลาง
...
```

**ข้อความต้องถูก edit เป็นผลจริง ไม่ใช่ส่งข้อความใหม่** ✅

### Step 4: ทดสอบ Error Handling

ปิด network ชั่วคราว แล้วส่ง Location

```
Expected Result:
ข้อความ "⏳ กำลังประมวลผล..." จะถูกแก้ไขเป็น:
"ขออภัย ไม่สามารถดึงข้อมูลพยากรณ์ฝนได้ในขณะนี้"
```

---

## Test 3 — Issue #26: Smart Cooldown (Severity Override)

**วัตถุประสงค์:** ยืนยันว่าระบบยังบล็อก 120 นาทีปกติ แต่ทะลุบล็อกได้เมื่อฝนรุนแรงขึ้น

### Step 1: ใช้ `/devmock rain` เพื่อจำลองฝนตกครั้งแรก

ส่งข้อความ `/devmock rain` ในแชทบอท (เฉพาะบัญชีที่อยู่ใน `DEVELOPER_CHAT_IDS`)
*หมายเหตุ: คำสั่งนี้จะทำการ Reset Cooldown เสมอ เพื่อให้มั่นใจว่าแจ้งเตือนครั้งแรกจะถูกส่งออกไป*

```
Expected Result:
🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌧️ ฝนตกหนัก
⏳ กำลังสร้างแจ้งเตือน...
[ตามด้วยข้อความแจ้งเตือนฝนจริง ความรุนแรง 15.0 mm/hr]
```

### Step 2: ทดสอบว่า Cooldown บล็อกการแจ้งเตือนสำเร็จ (ความรุนแรงเท่าเดิม)

**ห้ามพิมพ์ `/devmock rain` ซ้ำ** (เพราะคำสั่งนี้ตั้งใจเขียนมาให้ reset cooldown)
ให้ทดสอบโดยจำลองการทำงานของ Cron Job แทน เปิด Terminal แล้วพิมพ์:

```bash
curl -X POST http://localhost:8000/api/v1/cron/check-rain -H "X-Cron-Secret: default_secret_for_local_testing"
```

```
Expected Result (ดูใน Log ของ Server เท่านั้น):
Skipping chat_id ... (cooldown, rain 15.0 mm/hr ≤ last 15.0 mm/hr)
(จะไม่มีข้อความแจ้งเตือนใหม่ส่งเข้า Telegram)
```

### Step 3: ทดสอบ Smart Cooldown ทะลุบล็อก (จำลองความรุนแรงเพิ่มขึ้น)

จำลองสถานการณ์ว่าครั้งที่แล้วระบบเตือนตอนฝนตกเบา แต่รอบนี้ฝนตกหนักขึ้น
ให้แก้ไขค่าความรุนแรงครั้งล่าสุดใน Database ให้น้อยลง (เช่น 0.3) โดยเลือกทำตาม Database ที่คุณใช้งาน:

**สำหรับ SQLite:**
```bash
sqlite3 backend/fonmayang.db \
  "UPDATE user_locations SET last_alert_max_rain=0.3 WHERE chat_id=<YOUR_CHAT_ID>;"
```

**สำหรับ Firestore (ถ้าตั้งค่าใช้งานอยู่):**
1. เข้าไปที่ Firebase Console -> Firestore Database
2. ไปที่คอลเลกชัน `user_locations` -> หา Document ของ Chat ID คุณ
3. แก้ไขค่า (หรือเพิ่ม field) `last_alert_max_rain` เป็น `0.3` (number)

จากนั้นสั่งรัน Cron จำลองอีกครั้ง:

```bash
curl -X POST http://localhost:8000/api/v1/cron/check-rain -H "X-Cron-Secret: default_secret_for_local_testing"
```

```
Expected Result (Log + Telegram):
[INFO] Smart Cooldown override for chat_id ...: rain 0.3 → 15.0 mm/hr
[ข้อความแจ้งเตือนบน Telegram จะถูกส่งทะลุบล็อกออกมาทันที พร้อมส่วนหัวพิเศษ]:
⚠️ *อัปเดต: ฝนทวีความรุนแรงขึ้น!*
(0.3 mm/hr → 15.0 mm/hr)
🌧️ ฝนกำลัง...
```

**หากบอทแจ้งเตือนพร้อมข้อความ "ทวีความรุนแรงขึ้น" → Issue #26 ทำงานถูกต้องสมบูรณ์** ✅

---

## Quick Sanity via curl (ไม่ต้องใช้ Telegram)

```bash
# จำลอง Webhook location event
curl -X POST http://localhost:8000/api/v1/telegram/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 99999,
    "message": {
      "message_id": 1,
      "chat": {"id": 123456},
      "location": {"latitude": 13.756, "longitude": 100.502}
    }
  }'
```

```
Expected Result:
{"status": "ok"}   ← ตอบทันที (ไม่ block รอผล API)
```

ดู Log ใน terminal เพื่อยืนยัน fallback chain และ loading message
