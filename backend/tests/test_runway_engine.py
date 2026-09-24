import pytest
from app.services.runway_engine import RunwayEngine

def test_runway_calculation():
    engine = RunwayEngine()
    current_budget = 100.0
    fixed_daily_cost = 5.0
    variable_usage_cost = 5.0
    # Remaining Days = Current Budget / (Fixed Daily Cost + Variable Usage Cost)
    days = engine.calculate_remaining_days(current_budget, fixed_daily_cost, variable_usage_cost)
    assert days == 10.0

def test_runway_zero_cost():
    engine = RunwayEngine()
    current_budget = 100.0
    days = engine.calculate_remaining_days(current_budget, 0.0, 0.0)
    assert days == float('inf')

def test_runway_zero_budget():
    engine = RunwayEngine()
    days = engine.calculate_remaining_days(0.0, 10.0, 5.0)
    assert days == 0.0

def test_emergency_overdrive_freezes_decay():
    engine = RunwayEngine()
    days = engine.calculate_remaining_days(0.0, 10.0, 5.0, emergency_overdrive=True)
    assert days == float('inf')

def test_runway_with_elapsed_time():
    engine = RunwayEngine()
    current_budget = 100.0
    fixed_daily_cost = 5.0
    variable_usage_cost = 5.0  # total burn rate = 10.0 THB/day
    # If 2 days have elapsed, remaining budget is 100 - (10 * 2) = 80, remaining days = 8.0
    days = engine.calculate_remaining_days(
        current_budget, fixed_daily_cost, variable_usage_cost, elapsed_days=2.0
    )
    assert days == 8.0

def test_runway_elapsed_time_exceeds_budget():
    engine = RunwayEngine()
    current_budget = 50.0
    fixed_daily_cost = 5.0
    variable_usage_cost = 5.0  # total burn rate = 10.0 THB/day
    # If 10 days elapsed, remaining budget = 0, remaining days = 0
    days = engine.calculate_remaining_days(
        current_budget, fixed_daily_cost, variable_usage_cost, elapsed_days=10.0
    )
    assert days == 0.0

def test_target_exhaustion_time():
    engine = RunwayEngine()
    now_ts = 1700000000.0
    # 10 days remaining -> exhaustion time = now_ts + (10 * 86400)
    exhaustion_time = engine.calculate_target_exhaustion_time(
        remaining_days=10.0, base_timestamp=now_ts
    )
    assert exhaustion_time == 1700000000.0 + (10.0 * 86400)

def test_target_exhaustion_time_overdrive():
    engine = RunwayEngine()
    now_ts = 1700000000.0
    # In emergency overdrive (infinite days), target exhaustion time is -1
    exhaustion_time = engine.calculate_target_exhaustion_time(
        remaining_days=float('inf'), base_timestamp=now_ts
    )
    assert exhaustion_time == -1
