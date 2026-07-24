# Manual Verification for Issue #148 (Leaderboard API)

## Overview
This feature introduces a new `GET /api/v1/financial/leaderboard` endpoint to display user donations, grouped by user (pseudonym/token), summed, and ordered by total amount descending. It also assigns badges like "Ecosystem Guardian" for donations > 1000 THB.

## Prerequisites
- The backend application is running.
- You have tools to perform HTTP requests (e.g., `curl`, Postman, or a web browser).

## Verification Steps

### Step 1: Simulate Donations
We will call the `/auth/generate-token` endpoint to simulate users donating (which creates `Donor` records).
*(Assuming local server on port 8000)*
```bash
# User 1 (Alice) donates 500
curl -X POST http://localhost:8000/auth/generate-token   -H "Content-Type: application/json"   -d '{"transaction_id": "tx1", "amount": 500, "timestamp": "2026-07-24T12:00:00Z"}'

# User 1 (Alice) donates another 600
curl -X POST http://localhost:8000/auth/generate-token   -H "Content-Type: application/json"   -d '{"transaction_id": "tx2", "amount": 600, "timestamp": "2026-07-24T12:05:00Z"}'

# User 2 (Bob) donates 50
curl -X POST http://localhost:8000/auth/generate-token   -H "Content-Type: application/json"   -d '{"transaction_id": "tx3", "amount": 50, "timestamp": "2026-07-24T12:10:00Z"}'
```
*(Note: Because tokens are generated randomly in generate-token currently without an explicit token passing, to manually verify grouping you might need to manually set the same token for two records in SQLite, or just verify the endpoint returns valid structures.)*

### Step 2: Fetch the Leaderboard
```bash
curl -X GET http://localhost:8000/api/v1/financial/leaderboard
```

### Expected Outcome
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

### Step 3: Event Broadcasting Verification
Observe the application logs to ensure `EventBroadcaster().broadcast_event('new_donation', ...)` does not crash the server when new donations are processed via `/auth/generate-token`.
