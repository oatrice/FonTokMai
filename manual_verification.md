# Manual Verification: Arcade Leaderboard & SSE Integration (Issues #148 & #157)

## Prerequisites
- Node.js (v18+) and npm installed.
- Ensure the backend SSE endpoint `/api/v1/events/stream` is running or can be mocked.
- For testing the UI without the backend, you can temporarily mock `useEventStream.ts` to simulate data.

## Test 1: Gamified UI and Animations
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

## Test 2: SSE Connection (EventSource) State
1. In the browser Developer Tools -> Network tab, check that a connection to `/api/v1/events/stream` is made using EventSource.
2. If the connection fails, the indicator should turn red (`disconnected`), and it will auto-retry every 3 seconds.
3. If connected, the dot should pulse green.

## Test 3: Leaderboard Data Rendering
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

## Expected Outcomes
- The UI perfectly matches the rich aesthetics and gamified requirements.
- The `useEventStream` hook manages connection states and prevents duplicate SSE instances, properly triggering global React state updates using `useSyncExternalStore`.
