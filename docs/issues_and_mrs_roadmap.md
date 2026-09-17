# FonMaYang – Implementation Roadmap: Location Management, Presence Check & Cost Dashboard

บันทึกแผนงานการพัฒนา 9 Issues แบ่งเป็น 3 MR Batches ตามผลการวิเคราะห์สถาปัตยกรรม (C4 & DDD) และ Grilling Interview

---

## 🗺️ MR & Issue Overview

| MR Batch | Branch Name | Issues Included | Scope & Objectives | Target Version |
| :--- | :--- | :--- | :--- | :--- |
| **MR 1** | `feat/287-288-location-crud-snooze` | [#287](https://gitlab.com/oatricedev/FonMaYang/-/work_items/287), [#288](https://gitlab.com/oatricedev/FonMaYang/-/work_items/288) | **Location CRUD & Snooze**<br>- Schema `is_snoozed`, `snooze_until`<br>- Bot commands `/locations`, `/rename`, Inline Mute | `v0.74.0` |
| **MR 2** | `feat/289-290-291-presence-check` | [#289](https://gitlab.com/oatricedev/FonMaYang/-/work_items/289), [#290](https://gitlab.com/oatricedev/FonMaYang/-/work_items/290), [#291](https://gitlab.com/oatricedev/FonMaYang/-/work_items/291) | **Presence Verification System**<br>- Table `presence_answer_cache`<br>- Per-location Policy & Time Schedule<br>- Worker Decision Flow & Countdown TTL | `v0.75.0` |
| **MR 3** | `feat/292-296-dashboard-metrics` | [#292](https://gitlab.com/oatricedev/FonMaYang/-/work_items/292), [#293](https://gitlab.com/oatricedev/FonMaYang/-/work_items/293), [#294](https://gitlab.com/oatricedev/FonMaYang/-/work_items/294), [#295](https://gitlab.com/oatricedev/FonMaYang/-/work_items/295), [#296](https://gitlab.com/oatricedev/FonMaYang/-/work_items/296) | **Accuracy Dashboard & Cost Breakdown**<br>- Table `alert_notification_log` + Auto-verify (+30m)<br>- Monthly Metrics & Cost API (GCP + External)<br>- Web Admin Dashboard (Recharts)<br>- Telegram `/stats` & `/cost` (Admin-only)<br>- Location Schedule Web Settings | `v0.76.0` |

---

## 📦 Batch Details

### MR 1: Location Management & Snooze (`feat/287-288-location-crud-snooze`)
- **Issue #287:** `feat(backend): Add Location Name CRUD and Snooze Columns to UserLocation`
  - คอลัมน์ `is_snoozed`, `snooze_until`
  - Repository methods: `rename_location()`, `snooze_location()`, `unsnooze_location()`
  - อัปเดต `get_active_locations()` ให้กรองพิกัดที่ติด Snooze ออก
- **Issue #288:** `feat(telegram): Add /locations, /rename, /mute and /unmute Bot Commands for Location Management`
  - เมนู `/locations` พร้อมสถานะ badge `[🟢 Active]` หรือ `[🔕 Snoozed until HH:MM]`
  - ปุ่ม Inline: `[🔕 Mute 1hr]` `[🔕 Mute 4hr]` `[🔕 Mute 24hr]` `[✅ Re-enable]`
  - คำสั่ง `/rename <old_name> <new_name>`

### MR 2: Presence Verification System (`feat/289-290-291-presence-check`)
- **Issue #289:** `feat(backend): Add PresenceAnswerCache Table and Presence Policy Columns to UserLocation`
  - ตาราง `presence_answer_cache`: `chat_id`, `location_name`, `answer`, `expires_at`
  - คอลัมน์ Policy ใน `UserLocation`: `presence_policy`, `schedule_active_days`, `schedule_active_start`, `schedule_active_end`, `presence_answer_ttl_minutes`, `default_fallback_policy`
- **Issue #290:** `feat(telegram): Add /presence Inline Settings Command for Per-Location Policy and Schedule Configuration`
  - Inline flow ตั้งค่ารายพิกัด: เลือก Policy, ตั้ง Schedule วัน/เวลา, ตั้ง TTL Countdown, ตั้ง Timeout Fallback
- **Issue #291:** `feat(worker): Implement Presence Check Decision Flow in Rain Analysis Worker`
  - Decision Tree: `Snooze Check` → `Policy Check` → `Schedule Check` → `Cache Check` → `Presence Ping (Pre-calc)` → `Countdown TTL` → `Timeout Fallback`

### MR 3: Accuracy Dashboard & Cost Breakdown (`feat/292-296-dashboard-metrics`)
- **Issue #292:** `feat(backend): Create AlertNotificationLog Table and Auto False-Alarm Verification Worker`
  - ตาราง `alert_notification_log` บันทึกทุก Alert
  - Worker Auto-verify หลังจากส่งเตือนไปแล้ว 30 นาที Re-fetch เรดาร์ตรวจสอบฝนจริง
- **Issue #293:** `feat(backend): Create Monthly Metrics and Cost Aggregation API Endpoints`
  - `GET /api/metrics/monthly`: Total Alerts, True Alarms, False Alarms (User + Auto)
  - `GET /api/metrics/cost`: GCP Cost + External API/Proxy Cost, Cost per Alert, Cost per True Alert
- **Issue #294:** `feat(frontend): Build Alert Accuracy Dashboard with Bar/Line Charts and Cost Breakdown`
  - Next.js Web Admin `/admin/metrics`: กราฟแท่งเปรียบเทียบ, กราฟเส้นแนวโน้ม, การ์ดต้นทุนต่อ Alert
- **Issue #295:** `feat(telegram): Add /stats and /cost Admin-Only Summary Commands`
  - สรุปตัวเลขสถิติและค่าใช้จ่ายส่งเข้า Telegram แอดมิน
- **Issue #296:** `feat(frontend): Add Location Schedule and Presence Policy Settings Panel in Web Admin`
  - หน้าจัดการพิกัด `/admin/locations` บน Web Admin

---

## 🛠️ Execution & Branching Policy
1. Base Branch: `staging` (ตาม `Git Branch Integration & PR Target Hierarchy Rule`)
2. TDD First: เขียน Unit Test ก่อน Implementation เสมอ
3. Git Worktree: รันงานใน Worktree เพื่อแยก Workspace ชัดเจน
4. Versioning: ขยับทีละ Minor version ต่อ 1 MR (`v0.74.0` -> `v0.75.0` -> `v0.76.0`)
