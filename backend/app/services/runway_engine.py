class RunwayEngine:
    def calculate_remaining_days(
        self,
        current_budget: float,
        fixed_daily_cost: float,
        variable_usage_cost: float,
        emergency_overdrive: bool = False,
        elapsed_days: float = 0.0,
    ) -> float:
        if emergency_overdrive:
            return float('inf')
        total_daily_cost = fixed_daily_cost + variable_usage_cost
        if total_daily_cost <= 0:
            return float('inf')

        # Deduct budget based on elapsed time since snapshot
        effective_budget = max(0.0, current_budget - (total_daily_cost * max(0.0, elapsed_days)))
        return effective_budget / total_daily_cost

    def calculate_target_exhaustion_time(
        self,
        remaining_days: float,
        base_timestamp: float,
    ) -> float:
        """Calculate the absolute target exhaustion timestamp (in seconds).
        Returns -1 if runway is infinite (emergency overdrive)."""
        if remaining_days == float('inf') or remaining_days < 0:
            return -1.0
        return round(base_timestamp + (remaining_days * 86400.0), 3)
