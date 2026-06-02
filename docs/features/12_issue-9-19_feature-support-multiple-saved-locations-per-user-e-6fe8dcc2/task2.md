# Tasks: Developer Mock Mode (Issue #19)

- `[x]` 1. Update Database Models
  - `[x]` 1.1. Add `DeveloperMock` model to `app/models.py`.
- `[x]` 2. Update Repositories (TDD)
  - `[x]` 2.1. Add `get_mock_state` and `set_mock_state` to `base.py`.
  - `[x]` 2.2. Write failing tests for SQLite & Firestore mock state.
  - `[x]` 2.3. Implement mock state logic in `sqlite.py` & `firestore.py`.
- `[x]` 3. Update Weather Service (TDD)
  - `[x]` 3.1. Write failing tests for `predict_rain_by_location` with `mock_state` parameter.
  - `[x]` 3.2. Implement `mock_state` parameter in `RainbowService`.
- `[ ]` 4. Update Business Logic (TDD)
  - `[ ]` 4.1. Write failing tests for `/devmock` command in `test_webhook.py`.
  - `[ ]` 4.2. Implement `/devmock` command in `webhook.py`.
  - `[ ]` 4.3. Implement mock state injection in `scheduler_tasks.py`.
- `[ ]` 5. Verify the integration manually.
