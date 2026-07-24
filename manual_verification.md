# Manual Verification Plan - Real-time Leaderboard & Event Broadcaster & Testing Infrastructure

- **Branch**: `feat/148-157-realtime-leaderboard`
- **MR / Issue ID**: `#148, #157`
- **Date**: `2026-07-24`

## 📌 Prerequisites & Environment Setup
1. **Node.js** (v18+) and npm installed for frontend.
2. **Python 3.10+** and `uv`/`poetry` installed for backend.
3. Shell commands to launch the services locally:
   
   **Backend:**
   ```bash
   cd backend
   source .venv/bin/activate
   uv run uvicorn app.main:app --reload --port 8000
   ```
   
   **Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

---

## 🧪 Verification Scenarios

### Scenario 1: SSE Connection & Broadcasting (Issue #157)
- **Goal**: Verify that the client can connect to the Server-Sent Events endpoint and receive real-time data and periodic heartbeats.
- **Steps**:
  1. Open a terminal and connect to the stream endpoint using cURL:
     ```bash
     curl -N -H "Accept: text/event-stream" http://localhost:8000/api/v1/events/stream
     ```
  2. Wait up to 15 seconds to observe the automated heartbeat.
  3. In a separate terminal, trigger a mock event (e.g. by hitting an endpoint that calls `EventBroadcaster().broadcast_event()`).
- **Expected Outcome**:
  - HTTP Status: `200 OK`
  - Response Body: Stream remains open.
  - Heartbeat: Receives `event: ping\ndata: {}\n\n`.
  - Custom Event: Receives `event: <type>\ndata: <json_payload>\n\n`.

---

### Scenario 2: Leaderboard Data Aggregation & Badges (Issue #148)
- **Goal**: Verify that the financial leaderboard groups donations by pseudonym/token, sums amounts correctly, and assigns proper tier badges.
- **Steps**:
  1. Send mock donations to simulate donors.
     ```bash
     curl -X POST http://localhost:8000/auth/generate-token \
       -H "Content-Type: application/json" \
       -d '{"transaction_id": "tx1", "amount": 1050, "timestamp": "2026-07-24T12:00:00Z"}'
     ```
  2. Fetch the leaderboard data:
     ```bash
     curl -X GET http://localhost:8000/api/v1/financial/leaderboard
     ```
- **Expected Outcome**:
  - HTTP Status: `200 OK`
  - Response Body: JSON array sorted by `total_amount` descending.
  - Badge Logic: The user with `1050` amount should have the `"badge": "Ecosystem Guardian"` (since amount > 1000).

---

### Scenario 3: Arcade Leaderboard UI & SSE Hook
- **Goal**: Verify the frontend glassmorphic UI renders correctly and reacts to real-time events.
- **Steps**:
  1. Open `http://localhost:3000` in the browser and navigate to the Financial Dashboard.
  2. Inspect the "Top Operators" leaderboard card.
  3. Use the browser DevTools (Network tab) to ensure the `EventSource` connection to `/api/v1/events/stream` is established.
  4. Manually trigger a donation via the backend API.
- **Expected Outcome**:
  - The UI uses a retro-arcade, glassmorphic aesthetic (neon text, glowing borders).
  - Rank #1 has a gold/amber glow.
  - The UI updates automatically without a page refresh when the new donation event is received via SSE.
  - Disconnecting the backend turns the status indicator red and triggers an auto-retry every 3 seconds.

---

### Scenario 4: Verify Backend Tests
1. Navigate to the backend directory: `cd backend`
2. Activate the virtual environment: `source .venv/bin/activate`
3. Run the tests: `pytest tests/test_db.py`
4. Expected outcome: The tests should execute and pass without dependency errors.

### Scenario 5: Verify Frontend Unit Tests
1. Navigate to the frontend directory: `cd frontend`
2. Run the tests: `npm run test`
3. Expected outcome: Jest should run the `GlassNavbar.test.tsx` file and pass.

### Scenario 6: Verify E2E Setup
1. Navigate to the frontend directory: `cd frontend`
2. Run the E2E tests: `npm run test:e2e`
3. Expected outcome: Playwright should attempt to run the `home.spec.ts` test. (Note: initial browser download may be required via `npx playwright install` if running for the first time).

### Scenario 7: Verify CI/CD Pipeline
1. Check the GitLab Merge Request pipeline.
2. Expected outcome: `test_frontend` and `test_e2e` jobs should appear and execute alongside `unit_tests`.
