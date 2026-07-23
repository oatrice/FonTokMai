# Manual Verification Plan - MR 5: Resiliency & Circuit Breaker

- **Branch**: `feat/196-197-resiliency`
- **MR / Issue ID**: Issue #196, #197
- **Date**: 2026-07-23

---

## 📌 Prerequisites & Environment Setup
1. Ensure Python virtual environment dependencies are installed (`poetry install` or `pip install -r requirements.txt`).
2. Start the local backend server:
   ```bash
   poetry run uvicorn backend.app.main:app --reload --port 8000
   ```
3. Set environment variable or config state if testing specific API keys (TMD / LINE).

---

## 🧪 Verification Scenarios

### Scenario 1: Verify Dynamic Circuit Breaker State & API Fallback (Issue #196)
- **Goal**: Confirm that when an external service (e.g. TMD API) hits failure threshold or Jar HP <= 0, `CircuitBreaker` trips open and routes to the free fallback routine gracefully.
- **Steps**:
  1. Run the Python `CircuitBreaker` service test suite directly:
     ```bash
     pytest backend/tests/test_circuit_breaker.py -k "test_circuit_breaker_failure_threshold_and_recovery" -v
     ```
  2. Or invoke `CircuitBreaker` in a Python shell / worker routine:
     ```python
     from app.services.circuit_breaker import CircuitBreaker

     breaker = CircuitBreaker(failure_threshold=2)
     # Simulate 2 API failures to trip circuit
     breaker.execute_with_fallback(10.0, False, failing_api, fallback_api, service_name="tmd")
     breaker.execute_with_fallback(10.0, False, failing_api, fallback_api, service_name="tmd")
     # Verify fallback behavior
     assert breaker.is_api_allowed(10.0, False, service_name="tmd") == False
     ```
- **Expected Outcome**:
  - `CircuitBreaker` trips to `OPEN` state after failure threshold is met.
  - Automatically routes to free fallback function without throwing exceptions or crashing.

---

### Scenario 2: Emergency Overdrive & Infinite Runway Mode (Issue #197)
- **Goal**: Verify that setting `emergency_overdrive=True` puts the Runway engine in `INVINCIBLE` status and bypasses rate limits/circuit breakers.
- **Steps**:
  1. Connect to SSE stream or check runway status endpoint:
     ```bash
     curl -N "http://localhost:8000/api/v1/runway/stream?emergency_overdrive=true"
     ```
- **Expected Outcome**:
  - Response status stream outputs:
    ```json
    {
      "status": "INVINCIBLE",
      "runway_seconds": "Infinity",
      "decay_frozen": true
    }
    ```
  - Runway decay timer remains frozen and does not deplete HP.

---

## 📸 Proof of Verification (Artifacts & Logs)
- **Circuit Breaker Threshold Test Output**:
  ```text
  tests/test_circuit_breaker.py::test_circuit_breaker_failure_threshold_and_recovery PASSED [100%]
  1 passed, 5 deselected in 0.01s
  ```
- **Emergency Overdrive SSE Stream (`curl -N`)**:
  ```text
  data: {"remaining_days": "Infinity", "budget": 500.0, "daily_burn": 15.0, "emergency_overdrive": true, "status": "INVINCIBLE"}
  ```
- **Automated Verification Summary**:
  ```text
  pytest tests/test_circuit_breaker.py tests/test_runway_engine.py
  ====== 10 passed in 0.02s ======
  Full backend suite: 288 passed, 4 skipped
  ```
