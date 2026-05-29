# งานสำหรับ Issue #6: User Location Persistence with Expiry

- [x] Update `requirements.txt` with `sqlalchemy` and `aiosqlite`.
- [x] Create `app/database.py` for SQLite connection.
- [x] Create `app/models.py` with `UserLocation` model.
- [x] Update `app/main.py` to initialize DB tables on startup.
- [x] Write failing tests for Database Operations (`tests/test_db.py`).
- [x] Implement DB CRUD logic to pass the DB tests.
- [x] Write failing tests for Webhook & `/mylocation` logic (`tests/test_apis.py`).
- [x] Update `app/routers/webhook.py` to implement `/mylocation`, existing location checks, inline keyboards, and callback queries.
- [x] Verify all tests pass.
- [x] Perform manual verification.
