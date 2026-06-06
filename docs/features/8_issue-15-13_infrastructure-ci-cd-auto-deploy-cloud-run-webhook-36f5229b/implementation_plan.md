# Batch A: DevOps & Quick Win

เป้าหมายของ Batch A คือการปรับปรุงระบบ CI/CD ให้รองรับการ Auto-deploy ไปยัง Cloud Run (Issue #15) และเพิ่มข้อมูลสภาพอากาศแบบละเอียดในข้อความแจ้งเตือนฝนตก (Issue #13)

## User Review Required

> [!WARNING]
> การตั้งค่า CI/CD สำหรับ Cloud Run จำเป็นต้องใช้ Service Account Key ที่มีสิทธิ์ในการ Deploy โปรดตรวจสอบให้แน่ใจว่าได้เตรียมตัวแปรเหล่านี้ไว้ใน GitLab CI/CD Variables แล้ว

## Open Questions

> [!IMPORTANT]
> 1. **แหล่งข้อมูลสำหรับ Issue #13**: API ของ Rainbow.ai (Nowcast) มักจะให้ข้อมูลแค่ปริมาณฝน `rain` (mm/h) และเวลา `time` เราจะคำนวณ **ความรุนแรง (Intensity)** โดยอิงจากเกณฑ์มาตรฐาน (เช่น < 2.5 mm/h = เบา, 2.5 - 10 = ปานกลาง, > 10 = หนัก) และคำนวณ **ระยะเวลา (Duration)** จากจำนวนช่วงเวลา (interval) ที่คาดว่าจะมีฝนตกต่อเนื่อง ใช่หรือไม่?
> 2. **ข้อมูลลม (Wind Data)**: Rainbow.ai อาจจะไม่มีข้อมูลความเร็วลม หากต้องการแสดงข้อมูลลมด้วย คุณต้องการให้ดึงข้อมูลจาก API ฟรีตัวอื่น (เช่น Open-Meteo) เพิ่มเติมหรือไม่? หรือให้ข้ามเรื่องลมไปก่อนใน Batch นี้?
> 3. **GitLab CI Variables**: ใน `.gitlab-ci.yml` ผมจะเขียนคำสั่ง `gcloud run deploy` คุณได้เตรียม `GCP_PROJECT_ID` และ `GCP_SA_KEY` (หรือ Workload Identity) ไว้ใน GitLab CI แล้วใช่หรือไม่?
> 4. **Two Bots Strategy**: บอทสำหรับทดสอบ (Dev Bot) ที่จะใช้ร่วมกับ `localtunnel` คือ `@FonTokMaiDevBot` ถูกต้องหรือไม่? เพื่อที่ผมจะได้ระบุในคู่มือให้ชัดเจน

## Proposed Changes

### CI/CD Auto-deploy & Webhook Management (Issue #15)

#### [MODIFY] [FonMaYang/.gitlab-ci.yml](file:///Users/oatrice/Software-projects/FonMaYang/.gitlab-ci.yml)
- เพิ่ม Stage `deploy` ต่อจาก `test` 
- ใช้ image ที่มี `gcloud` ติดตั้งอยู่ (เช่น `google/cloud-sdk`) เพื่อรันคำสั่ง `gcloud run deploy` โดยอัตโนมัติเมื่อมีการ push เข้า branch `main`
- หลังจาก deploy สำเร็จ จะมีการรัน `curl` ไปยัง Telegram API เพื่ออัปเดต Webhook ของ Production Bot ให้ชี้ไปที่ URL ของ Cloud Run ทันที (ป้องกันปัญหา Webhook ตีกันระหว่าง Local กับ Production)

#### [NEW] [docs/development_guide.md](file:///Users/oatrice/Software-projects/FonMaYang/docs/development_guide.md)
- เขียนคู่มือ "Two Bots Strategy" สั้นๆ อธิบายวิธีใช้ Dev Bot ควบคู่กับ `localtunnel` (เช่น `lt --port 8001 --subdomain fontokmaidev`) ในการทดสอบ Local แบบไม่ให้กระทบ Production

---

### Extended Meteorological Data (Issue #13)

#### [MODIFY] [backend/app/services/rainbow.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/rainbow.py)
- ปรับปรุง `predict_rain_by_location` ให้วิเคราะห์ข้อมูลดิบ `predictions` เพิ่มเติม 
- คำนวณ `intensity` (ความรุนแรงของฝน) จากค่า max `rain` ในช่วงที่ฝนตก
- คำนวณ `duration` (ระยะเวลาตกต่อเนื่อง) จากเวลาเริ่มต้นจนถึงเวลาสิ้นสุดของกลุ่มเมฆฝนใน predictions

#### [MODIFY] [backend/app/scheduler_tasks.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/scheduler_tasks.py)
#### [MODIFY] [backend/app/routers/webhook.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/webhook.py)
- เปลี่ยนข้อความแจ้งเตือนจากเดิมที่มีแค่ "จะตกหนักในอีก X นาที"
- เพิ่มข้อมูลความรุนแรงและระยะเวลา เช่น:
  ```text
  🌧️ ฝนกำลังเคลื่อนมาทางทิศของคุณ จะเริ่มตกในอีก X นาที
  💧 ความรุนแรง: ปานกลาง (Moderate)
  ⏱️ คาดว่าจะตกต่อเนื่องประมาณ: 40 นาที
  ```

## Verification Plan

### Automated Tests
- เขียน Unit Test เพิ่มเติมใน `backend/tests/test_services.py` เพื่อทดสอบ logic การจัดกลุ่ม/คำนวณ `intensity` และ `duration` 
- ตรวจสอบให้ผ่าน (TDD Cycle) ด้วยคำสั่ง `pytest backend/tests/ -v`

### Manual Verification
- ขอให้ผู้ใช้สร้าง MR และ Merge เข้า Main เพื่อดูว่า GitLab CI วิ่งไปทำ Deploy บน Cloud Run สำเร็จหรือไม่
- รันบอทจำลองและลองกดส่ง Location เพื่อดูว่าข้อความ Alert ใหม่แสดงข้อมูล Intensity และ Duration อย่างถูกต้อง
