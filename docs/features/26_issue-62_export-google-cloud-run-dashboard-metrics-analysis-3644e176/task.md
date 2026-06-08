# Task: Issue #62 — Export Google Cloud Run Dashboard Metrics

## Phase 1: 🟥 RED (เขียน Failing Tests ก่อน)
- [ ] สร้าง `backend/tests/test_metrics.py` พร้อม failing tests ทั้งหมด

## Phase 2: 🟢 GREEN (เขียน Production Code ให้ผ่าน)
- [ ] เพิ่ม `CronRunLog` model ใน `backend/app/models.py`
- [ ] เพิ่ม abstract methods ใน `backend/app/repositories/base.py`
- [ ] implement ใน `backend/app/repositories/firestore.py`
- [ ] implement ใน `backend/app/repositories/sqlite.py`
- [ ] สร้าง `backend/app/services/metrics_service.py`
- [ ] สร้าง `backend/app/routers/metrics.py`
- [ ] register router ใน `backend/app/main.py`
- [ ] integrate timing wrapper ใน `backend/app/scheduler_tasks.py`

## Phase 3: ✨ REFACTOR
- [ ] ตรวจสอบ code ซ้ำซ้อน / cleanup

## Phase 4: Documentation
- [ ] อัปเดต `CHANGELOG.md` (0.26.0)
- [ ] อัปเดต `README.md`
- [ ] bump `VERSION` → 0.26.0
- [ ] อัปเดต `docs/features/26.../spec.md`

## Phase 5: Verify
- [ ] รัน `pytest tests/test_metrics.py -v` ผ่านทั้งหมด
- [ ] รัน `pytest tests/ -v` ผ่านทั้งหมด (regression)
