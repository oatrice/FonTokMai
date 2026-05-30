# แผนการ Deploy ระบบ FonMaYang ไปยัง Firebase

หลังจากที่เราเตรียมโครงสร้าง Adapter Pattern เสร็จแล้ว ขั้นตอนต่อไปคือการนำโค้ด FastAPI ของเราขึ้นไปรันบน **Firebase Cloud Functions (Python Gen 2)** และใช้ **Firestore** เป็นฐานข้อมูลหลักครับ

## ขั้นตอนการดำเนินการ (Proposed Changes)

### 1. การตั้งค่า Firebase Project (ผ่าน CLI)
- ตรวจสอบ/ล็อกอินเข้าสู่ระบบด้วย `npx -y firebase-tools@latest login`
- เลือกโปรเจกต์ (หรือสร้างใหม่) ด้วย `npx -y firebase-tools@latest use <PROJECT_ID>`
- ติดตั้งและตั้งค่า (Init) ส่วนของ Cloud Functions (สำหรับรัน FastAPI) และ Firestore (สำหรับฐานข้อมูล) ในโฟลเดอร์โปรเจกต์

### 2. สร้าง Wrapper สำหรับ Cloud Functions
เราจะสร้างไฟล์ `main.py` ภายในโฟลเดอร์ `functions` (ที่ได้จากการ init) เพื่อทำหน้าที่รับ Request จาก Firebase และส่งต่อให้ FastAPI ของเราทำงาน

#### [NEW] [functions/main.py](file:///Users/oatrice/Software-projects/FonMaYang/functions/main.py)
```python
from firebase_functions import https_fn
from firebase_admin import initialize_app

# โหลด FastAPI app ตัวเดิมของเรา
from app.main import app 

initialize_app()

# สร้าง Webhook Endpoint สำหรับ Firebase Cloud Functions โดยห่อ FastAPI ไว้
@https_fn.on_request()
def api(req: https_fn.Request) -> https_fn.Response:
    return https_fn.asgi_app(app)(req)
```

### 3. การย้าย/เชื่อมโยงโค้ด Backend
เพื่อให้ `functions/main.py` มองเห็นโฟลเดอร์ `app/` (FastAPI) ของเรา เราสามารถ:
- ย้ายโฟลเดอร์ `backend/app` ไปไว้ใน `functions/` 
- หรือ ใช้การตั้งค่า `requirements.txt` ของ Functions ให้อ่านโค้ดแบบ Package
- เพิ่ม Environment Variable บน Cloud Functions:
  - `STORAGE_BACKEND=firestore`
  - `SCHEDULER_TYPE=external`
  - `TELEGRAM_BOT_TOKEN=...`
  - `CRON_SECRET=...`

### 4. สั่ง Deploy
- ทำการรัน `npx -y firebase-tools@latest deploy --only functions,firestore`
- นำ URL ที่ได้จาก Cloud Functions ไปตั้งค่าใน Telegram Webhook
- นำ URL `/api/v1/internal/trigger-rain-check` ไปตั้งค่าใน **Google Cloud Scheduler** เพื่อให้ยิงเข้ามารันทุกๆ 5 นาทีแทนที่ APScheduler

## ⚠️ User Review Required

> [!IMPORTANT]
> **การใช้ Cloud Functions สำหรับ Python จำเป็นต้องมีการผูกบัตรเครดิต (Blaze Plan)** ในโปรเจกต์ Firebase ของคุณ แม้ว่าจะมีโควต้าฟรี (Free Tier) ต่อเดือนที่เพียงพอสำหรับโปรเจกต์ขนาดเล็กก็ตาม 
>
> **สิ่งที่ผมต้องการทราบก่อนเริ่มทำงาน:**
> 1. คุณมีโปรเจกต์ Firebase (Project ID) ที่พร้อมใช้งานและเปิด Blaze Plan แล้วหรือยังครับ?
> 2. ต้องการให้ผมปรับโครงสร้างโฟลเดอร์ (ย้าย `backend` เข้าไปรวมใน `functions` ตอนทำ Firebase Init) เลยไหมครับ หรืออยากให้แยกโฟลเดอร์ไว้แบบเดิมแล้วใช้ symbolic link (หรือวิธีอื่น) ในการรัน?

หากพร้อมที่จะให้ผมตั้งค่า Firebase ในโฟลเดอร์โปรเจกต์แล้ว รบกวนแจ้ง **Project ID** ให้ผมทราบด้วยครับ!
