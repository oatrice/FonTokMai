# คู่มือการทดสอบระบบ (Manual Verification Guide)
สำหรับการแก้ไข Issue #21: ย้ายการจัดเก็บข้อมูลพิกัดการแจ้งเตือนจาก SQLite ไปยัง Firestore

การทดสอบนี้มีเป้าหมายเพื่อพิสูจน์ว่า หากเซิร์ฟเวอร์ (หรือ Cloud Run container) ถูกปิดหรือรีสตาร์ท (Cold Start) ข้อมูลพิกัด (Location) ของผู้ใช้ที่บันทึกไว้จะไม่สูญหายไป

---

### ขั้นตอนที่ 1: เตรียม Environment สำหรับ Firestore
เพื่อให้เซิร์ฟเวอร์จำลองการรันผ่าน Firestore บนเครื่องของคุณ
1. ติดตั้ง Firebase Admin SDK ให้เรียบร้อย (มีใน `requirements.txt` แล้ว)
2. ไปที่ [Google Cloud Console](https://console.cloud.google.com/) เลือกโปรเจกต์ของคุณ
3. สร้าง Service Account Key (`.json`) แล้วบันทึกไว้ในเครื่อง (เช่น `~/Downloads/key.json`)
4. เปิด Terminal แล้วตั้งค่า Environment Variable สำหรับโปรเจกต์นี้:
   ```bash
   export STORAGE_BACKEND=firestore
   export GOOGLE_APPLICATION_CREDENTIALS="~/Downloads/key.json"
   ```
*(หมายเหตุ: หากคุณใช้ Firestore Emulator สามารถข้ามข้อ 3-4 และใช้ `export FIRESTORE_EMULATOR_HOST="127.0.0.1:8080"` แทนได้)*

### ขั้นตอนที่ 2: รันแอปพลิเคชัน (FastAPI)
1. เปิด Terminal ใหม่ (หรือใช้ตัวเดิมที่ตั้งค่า Environment แล้ว) เข้าไปที่โฟลเดอร์ `backend`
2. เข้า Virtual Environment: `source venv/bin/activate` หรือ `.venv/bin/activate`
3. สั่งรันเซิร์ฟเวอร์:
   ```bash
   uvicorn app.main:app --reload
   ```
   *ตรวจสอบว่าเซิร์ฟเวอร์ทำงานที่พอร์ต 8001 โดยไม่มี Error*

### ขั้นตอนที่ 3: บันทึกพิกัดผ่าน Telegram
1. เปิดแอปพลิเคชัน Telegram ในโทรศัพท์หรือในคอมพิวเตอร์
2. เข้าไปที่แชทบอท FonMaYang ของคุณ
3. ส่งพิกัด Location ของคุณให้บอท (ในโทรศัพท์กดปุ่ม 📎 > Location > Send my current location)
4. บอทจะตอบกลับมาพร้อมแสดงปุ่มให้เลือก ให้คุณกดปุ่ม **"⏳ จำ 2 เดือน"** หรือ **"♾️ จำตลอดไป"** เพื่อให้ระบบบันทึกลงฐานข้อมูล
5. บอทต้องตอบกลับข้อความว่า "บันทึกข้อมูลพิกัดเรียบร้อยแล้ว"

### ขั้นตอนที่ 4: ตรวจสอบใน Firestore
1. ไปที่เมนู Firestore Database ใน [Google Cloud Console](https://console.cloud.google.com/firestore)
2. ดูในคอลเลกชัน `user_locations`
3. **สิ่งที่ต้องเจอ**: จะต้องมี Document ใหม่ที่ชื่อตรงกับ `chat_id` ของคุณ
4. ภายใน Document ต้องมี field `latitude`, `longitude`, `retention_type`, และ `expires_at` แสดงอยู่ครบถ้วน

### ขั้นตอนที่ 5: จำลองเหตุการณ์ Cold Start (เซิร์ฟเวอร์ดับ)
1. กลับไปที่ Terminal ที่รันคำสั่ง `uvicorn` อยู่
2. กด `Ctrl + C` เพื่อหยุดการทำงานของเซิร์ฟเวอร์ (เป็นการปิดแอปพลิเคชันโดยสมบูรณ์)
3. ระบบจะตัดการเชื่อมต่อชั่วคราว (เหมือนกรณี Cloud Run ลบ Container ทิ้งเมื่อไม่มีคนใช้งาน)

### ขั้นตอนที่ 6: เปิดเซิร์ฟเวอร์ขึ้นมาใหม่
1. ใน Terminal เดิม ให้สั่งรันเซิร์ฟเวอร์อีกครั้ง:
   ```bash
   uvicorn app.main:app --reload
   ```

### ขั้นตอนที่ 7: ทดสอบว่าข้อมูลยังอยู่หรือไม่
1. กลับไปที่แอปพลิเคชัน Telegram ของคุณ
2. พิมพ์คำสั่ง `/mylocation` แล้วส่งหาบอท

---
### 🎉 ผลลัพธ์ที่คาดหวัง (Expected Result)
- บอทจะต้องสามารถตอบกลับได้ว่า **"📍 พิกัดปัจจุบันของคุณ: [เลขละติจูด], [เลขลองจิจูด]"** พร้อมบอกวันหมดอายุได้อย่างถูกต้อง
- ข้อความนี้ต้อง **ไม่เป็น** "คุณยังไม่ได้บันทึกตำแหน่งใดๆ ไว้ในระบบ"
- การทดสอบนี้เป็นการยืนยัน 100% ว่าข้อมูลพิกัดได้ถูกนำไปฝากไว้ที่ Firestore และจะไม่สูญหายไปกับ Cold Start ของ Cloud Run อีกต่อไป
