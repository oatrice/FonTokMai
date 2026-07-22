# Manual Verification Steps

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
