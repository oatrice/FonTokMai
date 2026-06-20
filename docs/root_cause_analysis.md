# 🔬 Root Cause Analysis — fonmayang Cloud Run
**วันที่วิเคราะห์:** 20 มิ.ย. 2026 | **ผู้วิเคราะห์:** Antigravity AI
**อ้างอิง:** [fonmayang_cloudrun_metrics_report.md](./fonmayang_cloudrun_metrics_report.md)

---

## 📌 Executive Summary

การวิเคราะห์เชิงลึกพบว่าปัญหา Latency และ Instance Crash ทั้งหมดมีสาเหตุหลักจาก **3 ปัจจัยที่เชื่อมโยงกัน** ไม่ใช่ปัญหาเดี่ยว:

1. **EMSC WebSocket Memory Leak** — ทำให้ Memory พุ่งถึง 100% และ OOM Kill Instance (แก้ไขแล้วใน v0.30)
2. **`tmd_frames_cache` ใน WeatherManager ที่ไม่มี Expiry** — สะสม numpy arrays ไม่ปล่อย
3. **Budget Exhaustion (274.47/280 THB = 98%)** — ระบบอาจถูกระงับการให้บริการจาก GCP ใน 1-2 วัน

> [!CAUTION]
> Budget ปัจจุบัน 274.47/280 THB (98.0%) — ระบบอาจถูก auto-shutdown ภายใน 1-2 วัน ต้องตรวจสอบเรื่องค่าใช้จ่ายด่วน

---

## 🗓️ Git History ↔ Metrics Correlation

| Phase Metrics | วันที่ | Commit / Version | การเปลี่ยนแปลงสำคัญ | ผลกระทบ |
|---|---|---|---|---|
| **Phase 1 (ปกติ)** | 31 พ.ค. – 5 มิ.ย. | v0.9–v0.17 | ระบบพื้นฐาน Rainbow/Tomorrow API | Latency 5–35ms ✅ |
| **🔴 Phase 2 เริ่ม** | **6 มิ.ย. 00:43** | **v0.19 `11000bb`** | **เพิ่ม TMD Radar Processing + OCR Chain** | Latency พุ่ง 19:00 น. |
| **Phase 2 รุนแรง** | 6 มิ.ย. 20:19 | v0.21–v0.22 `11000bb` | **EMSC WebSocket เปิดตอน startup** | Memory ~100%, Latency 50k–279k ms |
| **🔴 Phase 3: Instance=0** | 9 มิ.ย. | v0.23–v0.25 | ยังคง EMSC WS + เพิ่ม Caching | OOM Kill 15hr downtime |
| **Phase 3 ต่อเนื่อง** | 8 มิ.ย. 11:09 | **v0.26 `fb9b377`** | เพิ่ม MetricsService | ยังคง Latency 30k–150k ms |
| **🔴 Phase 4 Traffic Surge** | **16 มิ.ย. 07:49** | **v0.27 `07fc051`** | **ย้าย Background Tasks → Cloud Tasks** | Traffic x100 |
| **Hotfix แรก** | 17 มิ.ย. 21:53 | **v0.30 `0a2226c`** | **Bypass OCR Chain + Disable EMSC WS** | Latency ดีขึ้นชั่วคราว |
| **Hotfix ที่สอง** | 18 มิ.ย. 19:59 | **v0.32 `4b87fd9`** | **เพิ่ม Memory 1GiB + `--cpu-throttling`** | Phase 5 เริ่มทรงตัว |
| **Phase 5 (ปัจจุบัน)** | 19 มิ.ย. 23:12 | v0.35 | E2E Tests + Path-based CI/CD | Latency กำลังไต่ระดับซ้ำ |

---

## 🔴 Findings จาก Cloud Run Logs (Live)

### 1. EMSC WebSocket (แก้แล้ว)
ระบบ EMSC ถูก Decouple ไปที่ VM Worker แล้วใน v0.31 — ไม่มีปัญหา Memory Leak จากส่วนนี้แล้ว

### 2. 🚨 `NameError: name 'gif_bytes' is not defined`
```
[2026-06-19T16:20:28] WARNING: Failed to process TMD radar kkn240: name 'gif_bytes' is not defined
```
**พบซ้ำ 180+ ครั้ง** — สาเหตุ: ตัวแปร `gif_bytes` ถูก disable แต่ยังมี code path ที่เรียกใช้

### 3. 🚨 `RuntimeWarning: coroutine 'render_hq_png' was never awaited`
```
[2026-06-19T15:08:49] RuntimeWarning: coroutine 'WeatherManager._get_tmd_prediction.<locals>.render_hq_png' was never awaited
```
ฟังก์ชัน `render_hq_png` ถูกเปลี่ยนเป็น sync แล้ว แต่ยังมี code ที่ใช้ `await` เรียกมัน ทำให้เกิด Coroutine Leak 

### 4. 🚨 Budget Alert กวนทุก 20 นาที
**Budget ปัจจุบัน 274.47/280 THB = 98%** — ส่ง alert รัวๆ 

### 5. 🚨 EMSC Webhook Flood
พบ Re-delivery storm 400+ events ใน 20 นาที จาก VM Worker มายัง Cloud Run

---

## 🔬 Code-Level: Memory Leak Analysis

### A. `tmd_frames_cache` — Instance-level Cache ไม่มี Max Size
```python
# weather_manager.py
self.tmd_frames_cache = {}  # 🚨 ไม่มี max size, ไม่มี eviction policy
```
แต่ละ `station_code` เก็บ tuple ของ numpy arrays ขนาดใหญ่ (radar frames) การที่ไม่มีการลบข้อมูลออก ทำให้หน่วยความจำเพิ่มขึ้นเรื่อยๆ จนเต็ม 

### B. OCR.space ถูกเรียกมากเกินไป
```
[2026-06-20T02:20:23] Running OCR: OCR.space (Hotfix Bypass)
```
108 API calls/ชั่วโมง ซึ่งกิน budget มาก

---

## ⚙️ Cloud Run Configuration Analysis

| Config | ค่าปัจจุบัน | ปัญหา | แนะนำ |
|---|---|---|---|
| `min-instances` | 0 | Scale-to-zero ขณะ Peak Traffic ทำให้ Cold Start ช้า | 1 |
| `timeout` | 60s | TMD radar + OCR อาจประมวลผลไม่ทัน | 300s |
| `concurrency` | 40 | สูงเกินไปสำหรับ task ที่ใช้ CPU หนัก | 10-20 |
| `--cpu-throttling` | เปิด | อาจทำให้ background tasks ค้าง | พิจารณาปิด |
| Memory | 1Gi | - | ✅ คงไว้ |

---

## 🛠️ Prioritized Fix Plan

### 🔴 ด่วนมาก (วันนี้)

- [ ] **ตรวจสอบ Budget** — ระบบอาจถูก shutdown ใน 1-2 วัน
- [ ] **Fix `gif_bytes` NameError** ใน `weather_manager.py`
- [ ] **Fix `render_hq_png` coroutine leak**

### 🟠 ด่วน (ภายใน 2-3 วัน)

- [ ] **แก้ `min-instances=1`, `timeout=300`, `concurrency=20`** ใน `.gitlab-ci.yml`
- [ ] **ตรวจสอบ Budget Webhook** (Dedup)

### 🟡 ระยะกลาง (สัปดาห์หน้า)

- [ ] **Deploy Alert Rules** ใน Cloud Monitoring 
- [ ] **Cache `WeatherManager` ที่ระดับ module** 
- [ ] **ตรวจสอบ EMSC Re-delivery**
