# FonMaYang 🌧️

**v0.52.0** — ระบบพยากรณ์ฝนแบบ Real-Time สำหรับพื้นที่ภาคอีสาน ประเทศไทย  
ใช้ภาพเรดาร์ TMD + Optical Flow เพื่อคาดการณ์ฝนล่วงหน้า 15–90 นาที

---

## Features

- **TMD Radar Processing** — ดาวน์โหลดและประมวลผลภาพเรดาร์ TMD (kkn120, kkn240, skn240) ด้วย Optical Flow
- **Rain Prediction** — คาดการณ์เวลาฝนจะมาถึง (ETA) และความเข้ม (dBZ) ล่วงหน้าสูงสุด 90 นาที
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

### Developer Commands (DEVELOPER_CHAT_IDS only)
| Command | Description |
|---|---|
| `/bypass <password>` | ยืนยันรหัสผ่านเพื่อเปิดใช้งาน Emergency Admin Bypass (1 ชั่วโมง) |
| `/bypass_logout` | ออกจากระบบ Emergency Admin Bypass |
| `/metrics [days]` | ส่งออกประวัติการรัน Cron metrics เป็นไฟล์ CSV |
| `/setbudget <amount>` | ปรับเปลี่ยนวงเงินงบประมาณ GCP แบบ Dynamic |
| `/devmock help` | แสดงทุก command |
| `/devmock rain` | จำลองฝนตกหนัก (Boost เมฆจริง) |
| `/devmock storm` | จำลองพายุ (สร้างเมฆปลอม 5 ก้อน) |
| `/devmock clear` | จำลองท้องฟ้าแจ่มใส |
| `/devmock error` | จำลอง API ล้มเหลวทั้งหมด |
| `/devmock off` | ปิด mock mode |
| `/devmock scenario <params>` | **จำลองสถานการณ์ฝนแบบ Parametric** (ดูด้านล่าง) |

#### `/devmock scenario` Parameters
```
rain_in:N        ฝนจะมาใน N นาที
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
    ├── TMDRadarProcessor  ← Optical Flow + Cloud Tracking
    ├── TomorrowService    ← Fallback 1
    ├── XweatherService    ← Fallback 2 (disabled by default)
    ├── RainbowService     ← Fallback 3
    └── OpenMeteoService   ← Fallback 4 (wind data)
```

**Key Services:**
- `backend/app/services/weather_manager.py` — Orchestrator, mock state handler
- `backend/app/services/tmd_radar_processor.py` — Image processing, optical flow, visualization
- `backend/app/services/notification.py` — Abstract notification dispatcher (Telegram & LINE)
- `backend/app/routers/webhook.py` — Telegram webhook entry point
- `backend/app/routers/line_webhook.py` — LINE webhook entry point
- `backend/app/scheduler_tasks.py` — Scheduled rain alerts

---

## DevOps Scripts

| Script | Description |
|---|---|
| `backend/scripts/check_public_access.sh` | Audit Cloud Run IAM public access |
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

---

## Version History

See [CHANGELOG.md](CHANGELOG.md) for full history.

Current: **v0.52.0** — ปรับปรุงระบบแจ้งเตือนงบประมาณให้รองรับการเช็กแบบประหยัดสเตทส่งเตือนภัยผ่าน Dev Bot และใช้การสลับ Token ใน .env; อัปเดต LINE Bot การดึงค่า Config แบบไดนามิกและย้ายคำสั่งคุยตอบกลับมาผ่าน Free Reply API; เพิ่มตัวคำสั่งขอภาพด่วนเป็นชิ้นเพื่อประหยัดข้อมูลโควต้า (/radar, /tracking, /timeline, /nowcast).
