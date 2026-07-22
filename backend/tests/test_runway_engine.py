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
