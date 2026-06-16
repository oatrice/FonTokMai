# Task: Batch 2 — Infrastructure Safeguards & Billing Fine-Tuning

## Issue #69 — Cloud Run Parameter Tuning
- [x] Modify `.gitlab-ci.yml` — ปรับ memory 512Mi, concurrency 40, timeout 120s

## Issue #72 — Budget Auto-shutdown Mechanism
- [x] Create `backend/scripts/setup_budget_alert.sh`
- [x] Create `backend/app/routers/budget_webhook.py`
- [x] Modify `backend/app/main.py` — register budget_webhook router
- [x] Modify `backend/.env.example` — เพิ่ม budget env vars
- [x] Modify `.gitlab-ci.yml` — เพิ่ม setup_budget step ใน deploy

## Docs
- [x] Create `docs/features/69-72_issue-infra-billing-batch2/manual_verification.md`
