# แผนการย้ายระบบ (Migration) ไปยัง Edgetunnel (cmliu)

จากข้อตกลง เราจะทำการรื้อระบบ Web Proxy แบบเดิมทิ้งทั้งหมด และแทนที่ด้วย **Edgetunnel** (`cmliu/edgetunnel`) ซึ่งเป็น VLESS/Trojan Proxy Protocol เพื่อให้การมุดเว็บมีประสิทธิภาพสูงสุด รองรับการเปิดดูหน้าเว็บและวิดีโอแบบไม่มีสะดุด

## ⚠️ User Review Required

แผนนี้จะทำการ **ลบโค้ดเดิมทั้งหมด** และแทนที่ด้วยโค้ดจาก Repository ของ Edgetunnel รบกวนพิจารณาข้อจำกัดและตอบคำถามเพื่อความถูกต้องครับ

> [!IMPORTANT]
> **คำถามเพื่อ Clarify ก่อนเริ่มงาน:**
> 1. **รหัสผ่านสำหรับเข้าหน้า Dashboard:** ระบบของ cmliu มีหน้าแผงควบคุม (Dashboard) คุณต้องการตั้งรหัสผ่าน (`ADMIN`) เป็นอะไรครับ? (ค่าเริ่มต้นถ้าไม่กำหนดคือ `admin`)
> 2. **รหัสผู้ใช้งาน (UUID):** คุณมี UUID ของ VLESS ที่อยากใช้เป็นพิเศษไหมครับ? หรือจะให้ผม Generate UUID ใหม่แบบสุ่มให้เลย?
> 3. โค้ดของ cmliu เป็น JavaScript ล้วน (ไม่ใช่ TypeScript) ผมจะทำการปรับโครงสร้างไฟล์ลบไฟล์ TypeScript เดิมทิ้งทั้งหมดนะครับ (เห็นด้วยหรือไม่?)

---

## 🛠 Proposed Changes (แผนการแก้ไข)

เราจะทำการเปลี่ยนโครงสร้างจาก `src/index.ts` ไปเป็นไฟล์ของ Edgetunnel

### โครงสร้างโปรเจกต์ (Project Structure)
- ลบไฟล์ `src/index.ts` และ `test/index.spec.ts` ทิ้งทั้งหมด เนื่องจากไม่ได้ใช้แล้ว
- ลบการตั้งค่า TypeScript (`tsconfig.json` และ `worker-configuration.d.ts`) เพื่อลดความซับซ้อน

### การดึงโค้ด Edgetunnel (Worker Code)
#### [NEW] `src/index.js`
- ทำการดาวน์โหลดโค้ดต้นฉบับจาก [`https://raw.githubusercontent.com/cmliu/edgetunnel/main/_worker.js`] มาใส่เป็นไฟล์หลักของโปรเจกต์เรา

### การตั้งค่า (Configuration)
#### [MODIFY] `wrangler.jsonc`
- แก้ไข `main` ชี้ไปที่ `src/index.js`
- เพิ่มส่วน `[vars]` เพื่อประกาศตัวแปร `ADMIN` (รหัสผ่าน) และ `UUID`
- เพิ่มส่วน `[[kv_namespaces]]` ผูกตัวแปรชื่อ `KV` (ตามที่โค้ดต้นฉบับต้องการใช้เก็บข้อมูล) สำหรับใช้เก็บตั้งค่าใน Dashboard

#### [MODIFY] `package.json`
- อัปเดตคำสั่ง (Scripts) ให้สอดคล้องกับไฟล์ `index.js`

---

## 🔍 Verification Plan (แผนการทดสอบ)

### การจำลองสภาพแวดล้อม (Local Development)
- รัน `npm run dev` เพื่อดูว่า Worker สามารถลุกขึ้นทำงานได้โดยไม่พัง
- ทดสอบเข้า `http://localhost:8787/` (หรือตามพาธที่กำหนด) และต่อท้ายด้วย `/admin` เพื่อดูว่าหน้า Dashboard ของ cmliu แสดงผลถูกต้องและรับรหัสผ่าน `ADMIN` หรือไม่

### หลังการขึ้นระบบ (Post-Deployment)
- คุณสามารถเอา Subscription Link จากหน้า Dashboard ไปใส่ในแอปอย่าง **v2rayN** หรือ **Clash** บนคอม/มือถือ และทดสอบเปิดเว็บดูวิดีโอที่โดนบล็อกได้ทันที
