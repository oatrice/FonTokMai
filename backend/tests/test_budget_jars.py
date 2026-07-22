import pytest
from app.services.budget_jars import BudgetJarManager, BudgetState

def test_initial_jars():
    manager = BudgetJarManager()
    state = manager.get_state()
    assert state.salary_jar == 0.0
    assert state.infra_jar == 0.0
    assert state.api_jar == 0.0

def test_allocation():
    manager = BudgetJarManager()
    # 50% salary, 30% infra, 20% API (for example)
    manager.add_donation(100.0)
    state = manager.get_state()
    assert state.salary_jar == 50.0
    assert state.infra_jar == 30.0
    assert state.api_jar == 20.0

def test_daily_deduction():
    manager = BudgetJarManager()
    manager.add_donation(1000.0)
    # Deduct daily costs
    manager.deduct_daily_costs(salary=10.0, infra=5.0, api=2.0)
    state = manager.get_state()
    assert state.salary_jar == 490.0
    assert state.infra_jar == 295.0
    assert state.api_jar == 198.0
