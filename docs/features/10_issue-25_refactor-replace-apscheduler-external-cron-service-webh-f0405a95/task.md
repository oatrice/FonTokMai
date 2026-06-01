# Tasks: Issue #25 (Replace APScheduler with Webhook Endpoint)

- [x] Write failing test for the new `/api/v1/cron/check-rain` endpoint in `backend/tests/test_scheduler.py`
- [x] Update `backend/app/routers/scheduler.py` to make the test pass (rename endpoint)
- [x] Remove `apscheduler` from `backend/app/main.py` and remove lifespan job adding
- [x] Remove `apscheduler` from `backend/requirements.txt`
- [x] Run automated tests to verify changes
- [x] Update `walkthrough.md`
