# Manual Verification Steps (MR 3)

1. Start the API locally (`uvicorn app.main:app --reload`).
2. Make a POST request to `/auth/generate-token` with the following body:
```json
{
  "transaction_id": "tx_test_123",
  "amount": 10.0,
  "timestamp": "2026-07-22T07:20:00Z"
}
```
3. Copy the returned `token`.
4. Make a POST request to `/auth/recover` with the correct exact parameters:
```json
{
  "transaction_id": "tx_test_123",
  "amount": 10.0,
  "timestamp": "2026-07-22T07:20:00Z"
}
```
5. Ensure the same token is returned.
6. Try changing `transaction_id` or `amount` in step 4 and ensure it fails with a 401 Unauthorized status.

---

# Manual Verification Instructions (MR 4)

1. **Start the API Server**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. **Verify SSE Endpoint (Runway Engine)**:
   - Open a terminal and use `curl` to listen to the SSE stream:
     ```bash
     curl -N http://127.0.0.1:8000/api/v1/runway/stream
     ```
   - **Expected Output**: You should see continuous data events streamed every 0.5 seconds, showing:
     ```
     data: {"remaining_days": 33.333333333333336, "budget": 500.0, "daily_burn": 15.0}
     ```

3. **Verify Budget Jars**:
   - Run the tests locally using:
     ```bash
     pytest tests/test_budget_jars.py -v
     ```
   - **Expected Output**: All 3 tests pass, confirming the 50/30/20 allocation logic and the daily cost deduction math is perfectly aligned.

4. **Verify No Regressions**:
   - Run the full test suite (if possible):
     ```bash
     pytest tests/ -v
     ```
   - Ensure the inclusion of `runway.router` in `main.py` did not break existing routes.
