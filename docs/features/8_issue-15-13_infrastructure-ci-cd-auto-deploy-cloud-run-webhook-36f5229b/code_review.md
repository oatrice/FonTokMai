There is a minor logic error in `duration_minutes` calculation for a single rain interval, and some missing type hints.

**1. Logic Error in Duration Calculation (`backend/app/services/rainbow.py`)**
When rain only occurs in a single 10-minute interval (e.g., `rain_start` == `rain_end`), `diff` will evaluate to `0`. 
The current code executes:
```python
duration_minutes = diff if diff > 0 else 10 # Evaluates to 10
duration_minutes += 10 # Becomes 20
```
This means a single 10-minute rain block is incorrectly reported as lasting 20 minutes. 

*Fix:*
Simply add 10 to the `diff` to account for the interval block size. If `diff` is 0, duration is 10. If `diff` is 10, duration is 20, etc.
```python
diff = int((rain_end - rain_start).total_seconds() / 60)
duration_minutes = diff + 10
```

**2. Type Hinting (`backend/app/services/rainbow.py`)**
The `max_rain` and `duration_minutes` variables should ideally have type hints for better PEP8/typing compliance:
```python
max_rain: float = 0.0
duration_minutes: int = 0
```

Otherwise, the code logic, CI/CD setup, and test cases look solid. No infinite loops or memory leaks found.
