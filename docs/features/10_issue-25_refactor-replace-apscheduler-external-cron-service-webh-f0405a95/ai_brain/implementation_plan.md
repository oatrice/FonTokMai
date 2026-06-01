# Issue #8 — Phase 4b: Settings Panel for Web Dashboard

## ภาพรวม (Overview)

เพิ่ม **Settings Page** ใน CastBuddy Web Dashboard เพื่อให้ผู้ใช้ตั้งค่าได้จาก UI โดยตรง
ไม่ต้องแก้ config file ด้วยมือ

ขอบเขตงาน:
1. **Config file** — อ่าน/เขียน `config.json` ใน root project
2. **Backend API** — `GET /api/settings` และ `POST /api/settings`
3. **Frontend UI** — Settings tab ใน sidebar + Form UI
4. **E2E Tests** — Playwright test 3 ชุดตาม TDD Workflow

---

## การตั้งค่า (Settings Fields)

| Field | Key | Type | Default |
|---|---|---|---|
| TTS Voice | `tts_voice` | string (dropdown) | `th-TH-NiwatNeural` |
| TTS Rate | `tts_rate` | string (`+0%` format) | `+0%` |
| OBS Subtitle Path | `obs_subtitle_path` | string (path) | `subtitle.txt` |
| Replay Folder | `replay_folder` | string (path) | `""` |

---

## User Review Required

> [!IMPORTANT]
> **TTS Voice Dropdown**: มีเสียงภาษาไทยที่ edge-tts รองรับหลายตัว (`th-TH-NiwatNeural`, `th-TH-PremwadeeNeural`) จะ hardcode ไว้เป็น preset ก่อน ถ้าต้องการ dynamic fetch voice list จาก edge-tts สามารถขยายได้ภายหลัง

> [!NOTE]
> **Config file location**: จะเก็บ `config.json` ไว้ใน root project (`/Users/oatrice/Software-projects/CastBuddy/config.json`) เป็น JSON ธรรมดา ไม่ encrypt — ถ้าภายหลังต้องการ secure path ที่มี credentials ค่อยขยาย

---

## Proposed Changes

### 1. Backend — Config Manager

#### [NEW] `core/config_manager.py`
- Class `ConfigManager` อ่าน/เขียน `config.json`
- Default values ถ้าไฟล์ยังไม่มี
- Method: `load() -> dict`, `save(data: dict) -> None`, `get_defaults() -> dict`

---

### 2. Backend — API Endpoints

#### [MODIFY] `api/server.py`
- Import `ConfigManager` เข้า `AppState`
- เพิ่ม endpoint:
  - `GET /api/settings` — return current config dict
  - `POST /api/settings` — validate + save config, return `{"ok": True}`
- `TTSPlayer` และ `OBSWriter` ใน `AppState` ต้องใช้ค่าจาก config เมื่อ start session

---

### 3. Frontend — Settings Tab

#### [MODIFY] `gui/index.html`
- เพิ่ม `<a id="nav-settings">` ใน sidebar nav (⚙️ Settings)
- เพิ่ม `<div id="view-settings">` มี form fields:
  - TTS Voice (select dropdown)
  - TTS Rate (range slider + live label)
  - OBS Subtitle Path (text input + placeholder)
  - Replay Folder (text input + placeholder)
- Save button + toast notification บน success/error

#### [MODIFY] `gui/app.js`
- เพิ่ม navigation logic สำหรับ Settings tab
- `loadSettings()` — fetch GET /api/settings, populate form
- `saveSettings()` — serialize form → POST /api/settings
- Toast notification ระบบ (slide-in, auto-dismiss 3s)

#### [MODIFY] `gui/styles.css`
- `.settings-form`, `.form-group`, `.form-label`, `.form-input`, `.form-select`
- `.range-row` สำหรับ slider + value label
- `.toast` component (bottom-right, slide-in animation)

---

### 4. Tests (TDD: Red → Green → Refactor)

#### [NEW] `tests/test_config_manager.py`
- Unit tests สำหรับ `ConfigManager`:
  - `test_default_config_returned_when_no_file_exists`
  - `test_save_and_load_roundtrip`
  - `test_load_partial_config_merges_defaults`

#### [MODIFY] `tests/e2e/test_dashboard.py`
- เพิ่ม E2E test:
  - `test_settings_tab_loads` — คลิก Settings tab, form โหลดค่า default
  - `test_settings_save_shows_toast` — กรอก + save แล้ว toast แสดง
  - `test_settings_persisted_on_reload` — reload แล้วค่าเดิมยังอยู่

---

## TDD Workflow

```
🟥 RED   → เขียน test_config_manager.py ก่อน (fail)
🟢 GREEN → implement ConfigManager ให้ pass
✨ REFACTOR → cleanup + เพิ่ม E2E tests
```

---

## Verification Plan

### Automated Tests
```bash
# Unit tests (ไม่รวม e2e)
uv run pytest tests/ --ignore=tests/e2e -v

# E2E tests (ต้องรัน server ก่อน)
uv run uvicorn api.server:app --port 8000 &
uv run pytest tests/e2e/ -v
```

### Manual Verification
- เปิด http://localhost:8000 → คลิก Settings → ฟอร์มโหลด → แก้ค่า → Save → toast แสดง
- Reload page → ค่าที่บันทึกไว้ยังอยู่
