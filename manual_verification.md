# Manual Verification: Architecture Refactor Phase 2

This MR encapsulates the global TMD radar cache from a raw dictionary and tuple representation into the `RadarFrameCache` deep module, exposing `get`, `set`, and `invalidate`.

## Verification Steps

### 1. Check application boot
Start the server to ensure cache initialization succeeds.
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
**Expected:** The app boots up cleanly without any global state definition errors.

### 2. Verify cache inspection via DevMock
Use the telegram devmock admin command to check the cache state.
```bash
curl -X POST "http://localhost:8000/api/webhook/devmock" -H "Content-Type: application/json" -d '{"command": "/devmock status", "chat_id": 123}'
```
**Expected:** The response should list `📦 In-Memory (RadarFrameCache)` along with the current cached stations.

### 3. Verify weather prediction via cache
Trigger a `/rain` command multiple times. The first time, it should fetch from the external TMD source or firestore. The second time, it should hit the `RadarFrameCache`.
```bash
curl -X POST "http://localhost:8000/api/webhook/telegram" -H "Content-Type: application/json" -d '{"message": {"text": "/rain", "chat": {"id": 123}}}'
```
**Expected:** Both calls should return successfully, and server logs should explicitly show `[LOCAL FIXTURE MODE] Successfully loaded ... frames from local fixture` or `Firestore cache LOADED`.

## Scope Checked
- Replaced `_GLOBAL_TMD_CACHE` dict with `RadarFrameCache`.
- Replaced tuple access with object property access on `RadarCacheEntry`.
- Verified that async locking uses `RadarFrameCache.get_lock(station_code)`.
