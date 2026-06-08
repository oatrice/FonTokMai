# แผนการพัฒนา Issue #62: Export Google Cloud Run Dashboard Metrics for Analysis

## ภาพรวม

Issue #62 ต้องการให้ FonMaYang บันทึก runtime metrics ของแต่ละ cron routine (เช่น latency, จำนวน alerts, error count) และ expose endpoint สำหรับดึงข้อมูลเหล่านั้นออกมาวิเคราะห์ได้ เป็น lightweight in-process telemetry โดยไม่ต้องพึ่ง Google Cloud Monitoring (ซึ่งมีค่าใช้จ่าย) เหมาะสำหรับ self-service analysis

## User Review Required

> [!IMPORTANT]
> **ขอ Confirm Scope:** Feature นี้จะ implement "lightweight in-process metrics" ที่เก็บใน Firestore และ expose ผ่าน API endpoint `/api/v1/metrics/export` พร้อม Google Sheets-friendly CSV export หรือต้องการ integration กับ Google Cloud Monitoring จริงๆ?

> [!WARNING]
> **ไม่มีการ export ไปยัง external system:** แผนนี้จะ export เป็น JSON/CSV ผ่าน HTTP endpoint เท่านั้น ไม่มี push ไปยัง BigQuery หรือ Cloud Monitoring โดยตรง (สามารถทำเพิ่มในอนาคตได้)

## Proposed Changes

### 1. Metrics Service (ใหม่)

#### [NEW] `backend/app/services/metrics_service.py`

Service สำหรับบันทึกและดึง run metrics:
- `record_cron_run(routine_name, duration_s, alerts_sent, errors, extra_data)`
- `get_metrics_summary(days=7)` → คืน JSON summary
- เก็บข้อมูลใน Firestore collection `cron_metrics`

**Metrics ที่บันทึก:**
| Field | คำอธิบาย |
|---|---|
| `routine_name` | เช่น `check_rain`, `fetch_tmd_radar` |
| `run_at` | UTC timestamp |
| `duration_s` | เวลาที่ใช้ run (วินาที) |
| `alerts_sent` | จำนวน alerts ที่ส่งออกไป |
| `locations_checked` | จำนวน locations ที่ตรวจสอบ |
| `errors` | จำนวน errors ที่เกิดขึ้น |
| `source` | เช่น `tomorrow`, `xweather` ฯลฯ |

---

### 2. Repository Layer

#### [MODIFY] `backend/app/repositories/base.py`
เพิ่ม 2 abstract methods:
- `record_cron_run(...)` 
- `get_cron_metrics(routine_name, days)` 

#### [MODIFY] `backend/app/repositories/firestore.py`
implement 2 methods ใหม่

#### [MODIFY] `backend/app/repositories/sqlite.py`  
implement 2 methods ใหม่ (สำหรับ local dev)

#### [MODIFY] `backend/app/models.py`
เพิ่ม SQLAlchemy model `CronRunLog`

---

### 3. Scheduler Integration

#### [MODIFY] `backend/app/scheduler_tasks.py`
ใส่ timing wrapper รอบ routine ทั้งหมด:
- `check_rain_and_alert()` → บันทึก `alerts_sent`, `locations_checked`, `duration_s`
- `fetch_tmd_radar_routine()` → บันทึก `duration_s`, `stations_updated`, `errors`

---

### 4. Metrics Router (ใหม่)

#### [NEW] `backend/app/routers/metrics.py`
```
GET /api/v1/metrics/export
  - Query params: ?days=7&format=json|csv&routine=check_rain
  - Auth: X-Cron-Secret header (reuse existing pattern)
  - Response: JSON summary หรือ CSV สำหรับ Google Sheets
```

#### [MODIFY] `backend/app/main.py`
Register metrics router ใหม่

---

### 5. Tests (TDD: Red → Green → Refactor)

#### [NEW] `backend/tests/test_metrics.py`
Tests สำหรับ:
- `MetricsService.record_cron_run()` 
- `MetricsService.get_metrics_summary()`
- GET `/api/v1/metrics/export` endpoint (authorized/unauthorized)
- CSV export format

---

### 6. Documentation Updates

#### [MODIFY] `CHANGELOG.md`
เพิ่ม version `0.26.0` (Unreleased)

#### [MODIFY] `README.md`
เพิ่มส่วน Metrics section

#### [MODIFY] `VERSION`
bump เป็น `0.26.0`

#### [MODIFY] `docs/features/26_issue-62_.../spec.md`
เขียน spec ที่สมบูรณ์

## Verification Plan

### Automated Tests
```bash
cd /Users/oatrice/Software-projects/FonMaYang/backend
pytest tests/test_metrics.py -v
```

### Manual Verification
1. รัน FastAPI locally: `uvicorn app.main:app --reload`
2. เรียก `POST /api/v1/cron/check-rain` → ตรวจว่า metrics ถูกบันทึก
3. เรียก `GET /api/v1/metrics/export?days=7` → ดู JSON output
4. เรียก `GET /api/v1/metrics/export?format=csv` → ดาวน์โหลด CSV

## โครงสร้างข้อมูลใน Firestore

```
cron_metrics/
  {auto_id}/
    routine_name: "check_rain"
    run_at: Timestamp
    duration_s: 3.14
    alerts_sent: 2
    locations_checked: 5
    errors: 0
    source: "xweather"
```
