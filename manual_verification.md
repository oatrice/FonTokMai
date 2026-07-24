# Manual Verification: Arcade Leaderboard & SSE Integration (Issues #148 & #157)

## Part 1: Frontend UI & SSE (Issue #157)
### Prerequisites
- Node.js (v18+) and npm installed.
- Ensure the backend SSE endpoint `/api/v1/events/stream` is running or can be mocked.
- For testing the UI without the backend, you can temporarily mock `useEventStream.ts` to simulate data.

### Test 1: Gamified UI and Animations
1. Start the Next.js development server:
   ```bash
   cd frontend
   npm run dev
   ```
2. Open the application at `http://localhost:3000` and navigate to the Financial Dashboard.
3. **Verify Glassmorphism & Retro-Arcade Vibe:**
   - Look for the `Top Operators` leaderboard section.
   - It should have a purple glow `GlassCard`, an arcade-like grid background, and neon typography.
   - Check that the `Top Operators` text has a glowing text-shadow.
4. **Verify Micro-Animations:**
   - If mock data is updated, observe the `framer-motion` smooth entry and exit animations.
   - Hover over a leaderboard row. It should highlight nicely.
   - The connection status dot (e.g., green for connected) should have a pinging animation.

### Test 2: SSE Connection (EventSource) State
1. In the browser Developer Tools -> Network tab, check that a connection to `/api/v1/events/stream` is made using EventSource.
2. If the connection fails, the indicator should turn red (`disconnected`), and it will auto-retry every 3 seconds.
3. If connected, the dot should pulse green.

### Test 3: Leaderboard Data Rendering
1. Emit a mock `leaderboard_update` event from the backend (or simulate it).
   ```json
   {
     "type": "leaderboard_update",
     "payload": [
       { "id": "u1", "name": "CyberNinja", "score": 95000, "avatar": "", "trend": "up", "combo": 4 },
       { "id": "u2", "name": "CryptoKing", "score": 82000, "avatar": "", "trend": "flat" },
       { "id": "u3", "name": "HackThePlanet", "score": 75000, "avatar": "", "trend": "down" }
     ]
   }
   ```
2. **Verify Output:**
   - Rank #1 should have an amber/gold glowing border and text.
   - Rank #2 should have a silver styling.
   - Rank #3 should have a bronze styling.
   - Players with `combo > 2` should have a pulsing red flame combo badge (e.g., `x4`).
   - The scores should be formatted with commas.
   - Trends (`up`, `down`, `flat`) should show correct Chevrons and Minus icons with corresponding colors.

### Expected Outcomes
- The UI perfectly matches the rich aesthetics and gamified requirements.
- The `useEventStream` hook manages connection states and prevents duplicate SSE instances, properly triggering global React state updates using `useSyncExternalStore`.

## Part 2: Backend Leaderboard API (Issue #148)
### Overview
This feature introduces a new `GET /api/v1/financial/leaderboard` endpoint to display user donations, grouped by user (pseudonym/token), summed, and ordered by total amount descending. It also assigns badges like "Ecosystem Guardian" for donations > 1000 THB.

### Prerequisites
- The backend application is running.
- You have tools to perform HTTP requests (e.g., `curl`, Postman, or a web browser).

### Verification Steps

#### Step 1: Simulate Donations
We will call the `/auth/generate-token` endpoint to simulate users donating (which creates `Donor` records).
*(Assuming local server on port 8000)*
```bash
# User 1 (Alice) donates 500
curl -X POST http://localhost:8000/auth/generate-token -H "Content-Type: application/json" -d '{"transaction_id": "tx1", "amount": 500, "timestamp": "2026-07-24T12:00:00Z"}'

# User 1 (Alice) donates another 600
curl -X POST http://localhost:8000/auth/generate-token -H "Content-Type: application/json" -d '{"transaction_id": "tx2", "amount": 600, "timestamp": "2026-07-24T12:05:00Z"}'

# User 2 (Bob) donates 50
curl -X POST http://localhost:8000/auth/generate-token -H "Content-Type: application/json" -d '{"transaction_id": "tx3", "amount": 50, "timestamp": "2026-07-24T12:10:00Z"}'
```
*(Note: Because tokens are generated randomly in generate-token currently without an explicit token passing, to manually verify grouping you might need to manually set the same token for two records in SQLite, or just verify the endpoint returns valid structures.)*

#### Step 2: Fetch the Leaderboard
```bash
curl -X GET http://localhost:8000/api/v1/financial/leaderboard
```

#### Expected Outcome
The response should be a JSON array sorted by `total_amount` descending:
```json
[
  {
    "token": "<some_token_for_alice>",
    "pseudonym": "Anonymous",
    "total_amount": 1100.0,
    "badge": "Ecosystem Guardian"
  },
  {
    "token": "<some_token_for_bob>",
    "pseudonym": "Anonymous",
    "total_amount": 50.0,
    "badge": "Supporter"
  }
]
```
(The `Ecosystem Guardian` badge is assigned because 1100.0 > 1000).

#### Step 3: Event Broadcasting Verification
Observe the application logs to ensure `EventBroadcaster().broadcast_event('new_donation', ...)` does not crash the server when new donations are processed via `/auth/generate-token`.
