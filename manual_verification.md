# Manual Verification Plan - MR 6: Milestone Progress Bar & Donation Lock

- **Branch**: `feat/198-milestone-lock`
- **MR / Issue ID**: Issue #198
- **Date**: 2026-07-23

---

## 📌 Prerequisites & Environment Setup
1. Ensure database migrations are applied or SQLite test database is populated.
2. Start the local backend server:
   ```bash
   poetry run uvicorn backend.app.main:app --reload --port 8000
   ```

---

## 🧪 Verification Scenarios

### Scenario 1: Unlocked Milestone State & Progress Bar Details
- **Goal**: Verify `GET /api/milestones` when `milestone_lock` is `False` or not set in `SystemConfig`.
- **Steps**:
  1. Send GET request to endpoint:
     ```bash
     curl -X GET "http://localhost:8000/api/milestones"
     ```
- **Expected Outcome**:
  - HTTP Status: `200 OK`
  - Response Body:
    ```json
    {"total_amount": 0.0, "is_locked": false, "waiting_list": false, "recent_donations": []}
    ```

---

### Scenario 2: Locked Milestone & Donation Lock Behavior
- **Goal**: Verify `GET /api/milestones` when `milestone_lock` is set to `{"locked": true}` in `SystemConfig`.
- **Method A (via `pytest` - Recommended)**:
  - Run the specific locked state test:
    ```bash
    pytest tests/test_milestone_lock.py -k "test_milestone_locked_state" -v
    ```
- **Method B (via SQLite CLI / Python)**:
  1. Insert/Update `SystemConfig` key `milestone_lock` in SQLite database (`fonmayang.db`):
     ```bash
     sqlite3 fonmayang.db "INSERT OR REPLACE INTO system_config (key, value_json) VALUES ('milestone_lock', '{\"locked\": true}');"
     ```
  2. Send request to endpoint:
     ```bash
     curl -X GET "http://localhost:8000/api/milestones"
     ```
- **Expected Outcome**:
  - HTTP Status: `200 OK`
  - Response Body (Verified Output):
    ```json
    {"total_amount": 0.0, "is_locked": true, "waiting_list": true, "recent_donations": []}
    ```

---

## 📸 Proof of Verification (Artifacts & Logs)
- **Milestone Locked Test Output**:
  ```text
  tests/test_milestone_lock.py::test_milestone_locked_state PASSED [100%]
  1 passed, 1 deselected, 2 warnings in 1.16s
  ```
- **Automated Verification Summary**:
  ```text
  pytest tests/test_milestone_lock.py
  tests/test_milestone_lock.py .. [100%]
  2 passed, 2 warnings in 1.30s
  Full backend suite: 282 passed, 4 skipped
  ```
