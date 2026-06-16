# Task: Batch 2 — Infrastructure Safeguards & Billing Fine-Tuning

## Issue #69 — Cloud Run Parameter Tuning
- [x] Modify `.gitlab-ci.yml` — ปรับ memory 512Mi, concurrency 40, timeout 120s

## Issue #69 — Code Optimization (Sub-tasks เพิ่มเติม)

### Sub-task 1: Fix Dead URL (kkn120Loop.gif → 404)
- [x] Verify URL จริงของ TMD Loop GIF via curl
- [x] Modify `backend/app/services/tmd_radar_config.py` — เพิ่ม `loop_gif_url` field + verified URLs
- [x] Modify `backend/app/services/tmd_radar_processor.py` — fix fallback URL logic
- [x] Modify `backend/app/scheduler_tasks.py` — fix URL construction + guard

### Sub-task 2: Async Parallel Processing
- [x] Refactor `fetch_tmd_radar_routine()` → asyncio.gather (parallel 3 stations)

### Sub-task 3: Cloud Logging Noise Reduction
- [x] Modify `backend/app/services/earthquake.py` — ลด log level EMSC noise (Python-level)
- [x] Modify `backend/scripts/setup_gcp.sh` — เพิ่ม Cloud Logging exclusion filter (GCP-level)

## Issue #72 — Budget Auto-shutdown Mechanism
- [x] Create `backend/scripts/setup_budget_alert.sh`
- [x] Create `backend/app/routers/budget_webhook.py`
- [x] Modify `backend/app/main.py` — register budget_webhook router
- [x] Modify `backend/.env.example` — เพิ่ม budget env vars
- [x] Modify `.gitlab-ci.yml` — เพิ่ม setup_budget step ใน deploy

## Docs
- [x] Create `docs/features/29_issue-72-69.../manual_verification.md`
