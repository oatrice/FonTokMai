class RunwayEngine:
    def calculate_remaining_days(self, current_budget: float, fixed_daily_cost: float, variable_usage_cost: float, emergency_overdrive: bool = False) -> float:
        if emergency_overdrive:
            return float('inf')
        total_daily_cost = fixed_daily_cost + variable_usage_cost
        if total_daily_cost <= 0:
            return float('inf')
        return current_budget / total_daily_cost
