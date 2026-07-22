from dataclasses import dataclass

@dataclass
class BudgetState:
    salary_jar: float = 0.0
    infra_jar: float = 0.0
    api_jar: float = 0.0

class BudgetJarManager:
    def __init__(self):
        self.state = BudgetState()
        # default allocation: 50% salary, 30% infra, 20% API
        self.alloc_salary = 0.5
        self.alloc_infra = 0.3
        self.alloc_api = 0.2

    def get_state(self) -> BudgetState:
        return self.state

    def add_donation(self, amount: float):
        self.state.salary_jar += amount * self.alloc_salary
        self.state.infra_jar += amount * self.alloc_infra
        self.state.api_jar += amount * self.alloc_api

    def deduct_daily_costs(self, salary: float, infra: float, api: float):
        self.state.salary_jar -= salary
        self.state.infra_jar -= infra
        self.state.api_jar -= api
