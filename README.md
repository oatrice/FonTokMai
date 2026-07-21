# FonMaYang 🌧️

**v0.57.0** — ระบบพยากรณ์ฝนแบบ Real-Time สำหรับพื้นที่ภาคอีสาน ประเทศไทย  
ใช้ภาพเรดาร์ TMD + Optical Flow เพื่อคาดการณ์ฝนล่วงหน้า 15–90+ นาที

---

## Features

- **TMD Radar Processing** — ดาวน์โหลดและประมวลผลภาพเรดาร์ TMD (kkn120, kkn240, skn240) ด้วย Optical Flow
- **Rain Prediction** — คาดการณ์เวลาฝนจะมาถึง (ETA) และความเข้ม (dBZ) ล่วงหน้าสูงสุด 90+ นาที
- **Manual Target Locking** — เลือกล็อคเป้าหมายกลุ่มฝนที่สนใจเพื่อดูทิศทางและระยะทางเคลื่อนที่บนภาพเรดาร์ได้แบบเจาะจง
- **Multi-Provider Fallback** — รองรับ Tomorrow.io, Rainbow API, Xweather, Open-Meteo เป็น fallback
- **Telegram Bot** — แจ้งเตือนผ่าน Telegram พร้อมภาพเรดาร์ tracking, timeline, และ multi-frame analysis
- **LINE Bot** — แจ้งเตือนและรับส่งพิกัด/คำสั่งทาง LINE OA พร้อมส่งภาพเรดาร์ล่าสุด และแผนภูมิวิเคราะห์กลุ่มฝน
- **Multi-Frame Radar Analysis** — ภาพ strip แสดงสูงสุด 6 frames เรียงตามเวลา พร้อม trajectory overlay และ growth/decay % ต่อ frame
- **Scheduler** — Cloud Scheduler ส่งแจ้งเตือนอัตโนมัติทุก 15 นาที

---

## Bot Commands (Telegram & LINE)

---

### User Commands
| Command | Description |
|---|---|
| (ส่ง Location) | พยากรณ์ฝน ณ ตำแหน่งนั้น และบันทึกเพื่อสมัครรับแจ้งเตือน |
| `/rain` | ดูสภาพอากาศตำแหน่งล่าสุด |
| `/rain tmd-radar` | บังคับใช้ TMD Radar endpoint |
| `/rain <location_name>` | ดูสภาพอากาศตำแหน่งที่บันทึกไว้ |
| `/radar` | ดูภาพเรดาร์ล่าสุด (Static Radar) สำหรับพิกัดล่าสุด |
| `/tracking` | ดูภาพวิเคราะห์ทิศทางกลุ่มฝน (Tracking Radar) สำหรับพิกัดล่าสุด |
| `/timeline` | ดูภาพกราฟไทม์ไลน์ระยะเวลาฝน (Timeline Graph) สำหรับพิกัดล่าสุด |
| `/nowcast` | ดูภาพเคลื่อนไหวพยากรณ์ฝน (GIF Nowcast) สำหรับพิกัดล่าสุด |
| `/lock <grid>` | ล็อคเป้าหมายกลุ่มฝนตามช่องตาราง (เช่น `/lock C4`) หรือตำแหน่งแมนนวล |
| `/unlock` | ยกเลิกการล็อคเป้าหมายกลุ่มฝน |

### Developer Commands (DEVELOPER_CHAT_IDS only)
| Command | Description |
|---|---|
| `/bypass <password>` | ยืนยันรหัสผ่านเพื่อเปิดใช้งาน Emergency Admin Bypass (1 ชั่วโมง) |
| `/bypass_logout` | ออกจากระบบ Emergency Admin Bypass |
| `/metrics [days]` | ส่งออกประวัติการรัน Cron metrics เป็นไฟล์ CSV |
| `/setbudget <amount>` | ปรับเปลี่ยนวงเงินงบประมาณ GCP แบบ Dynamic |
| `/job <pause/resume> <job_name>` | พักการทำงานหรือเปิดใช้งาน Cloud Scheduler Jobs ล่าสุด |
| `/status` | ตรวจสอบข้อมูลสถานะระบบหลังบ้าน งบประมาณคงเหลือ และ Cloud Scheduler Jobs |
| `/restore_public_access` | กู้คืนสิทธิ์ Public Access ให้กับ API ของ Cloud Run |
| `/disable_public_access` | ยกเลิกสิทธิ์ Public Access ของ API ให้เป็นโหมด Private |
| `/devmock help` | แสดงทุก command |
| `/devmock rain` | จำลองฝนตกหนัก (Boost เมฆจริง) |
| `/devmock storm` | จำลองพายุ (สร้างเมฆปลอม 5 ก้อน) |
| `/devmock clear` | จำลองท้องฟ้าแจ่มใส |
| `/devmock error` | จำลอง API ล้มเหลวทั้งหมด |
| `/devmock off` | ปิด mock mode |
| `/devmock config` | ดูและปรับการตั้งค่าการวิเคราะห์ (รวมถึง decay_enabled และ prediction_steps) |
| `/devmock scenario <params>` | **จำลองสถานการณ์ฝนแบบ Parametric** (ดูด้านล่าง) |

#### `/devmock scenario` Parameters
```
rain_in:N        ฝนจะมา in N นาที
rain_stopping:N  ฝนจะหยุดใน N นาที
no_rain          ไม่มีฝน (ทดสอบลมอย่างเดียว)
dbz:N            ความเข้มฝน dBZ (15–75, default 35)
wind:N           ความเร็วลม km/h (default 20)
wind_dir:X       ทิศลม: N/NE/E/SE/S/SW/W/NW (16 จุด)
growth:N         อัตราการเติบโต ±0.0–1.0
clusters:N       จำนวนก้อนเมฆ 1–5 (default 1)
```

**ตัวอย่าง:**
```
/devmock scenario rain_in:20 dbz:40 wind:60 wind_dir:N
/devmock scenario rain_stopping:10 dbz:30
/devmock scenario no_rain wind:45 wind_dir:SE
/devmock scenario rain_in:5 dbz:55 growth:0.3 clusters:3
```

---

## Architecture

```
Telegram / LINE Webhook
    │
    │
    ▼
WeatherManager.predict_rain()
    ├── TMDRadarProcessor  ← Optical Flow + Cloud Tracking + Target Lock
    ├── TomorrowService    ← Fallback 1
    ├── XweatherService    ← Fallback 2 (disabled by default)
    ├── RainbowService     ← Fallback 3
    └── OpenMeteoService   ← Fallback 4 (wind data)
```

**Key Services:**
- `backend/app/services/weather_manager.py` — Orchestrator, mock state handler, manual target tracking
- `backend/app/services/tmd_radar/clustering.py` — OpenCV contours, rain cluster detection, circular masking
- `backend/app/services/tmd_radar/tracking.py` — Optical flow wind vectors, cloud tracking, trajectory predictions
- `backend/app/services/tmd_radar/processor.py` — Main orchestrator for TMD Radar processing
- `backend/app/services/notification.py` — Abstract notification dispatcher (Telegram & LINE)
- `backend/app/routers/webhook.py` — Telegram webhook entry point
- `backend/app/routers/line_webhook.py` — LINE webhook entry point
- `backend/app/scheduler_tasks.py` — Scheduled rain alerts

---

## DevOps Scripts

| Script | Description |
|---|---|
| `backend/scripts/check_public_access.sh` | Audit Cloud Run IAM public access |
| `backend/scripts/disable_public_access.sh` | Disable API public access and configure private mode |
| `backend/scripts/setup_iam_roles.sh` | Configure IAM roles for Cloud Run Service Account |
| `backend/scripts/setup_schedulers.sh` | Apply Cloud Scheduler jobs from config |
| `backend/scripts/sync_schedulers.py` | Sync scheduler config from GCP |
| `backend/scripts/migrate_issue145.py` | Migrate user location for Nong Khai House and deprecate stale home coordinates |

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

Key test files:
- `tests/test_tmd_radar_e2e.py` — End-to-end TMD radar processing
- `tests/test_e2e_mock_scenario.py` — Parametric mock scenario (33 tests)
- `tests/test_multiframe_analysis.py` — Multi-frame visualization (16 tests)
- `tests/test_line_integration.py` — LINE integration, commands, and webhook handling
- `tests/test_grpc_fork_config.py` — gRPC fork configuration and lazy tasks client tests
- `tests/test_async_enqueue_task.py` — Async tasks enqueue verification tests
- `tests/test_decay_logic.py` — Cloud decay toggle and prediction steps verification tests
- `tests/test_manual_targeting.py` — Manual target tracking, override logic, and visual indicators tests
- `tests/test_tracking_nowcast_commands.py` — Telegram `/tracking` and `/nowcast` command router & dispatch execution tests

---

## Version History

See [CHANGELOG.md](CHANGELOG.md) for full history.

Current: **v0.57.0** — เพิ่มคำสั่ง `/tracking` และ `/nowcast` สำหรับ Telegram Bot, ปรับปรุงการล็อกตำแหน่งกลุ่มฝน (Cluster Locking) และระบบจัดการ Label A-Z
