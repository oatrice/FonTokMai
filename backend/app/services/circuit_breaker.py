import inspect
from typing import Callable, Any

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5):
        self.failure_threshold = failure_threshold
        self._failures: dict[str, int] = {}
        self._open_circuits: dict[str, bool] = {}

    def is_api_allowed(self, jar_hp: float, emergency_overdrive: bool = False, service_name: str = "default") -> bool:
        if emergency_overdrive:
            return True
        if self._open_circuits.get(service_name, False):
            return False
        return jar_hp > 0.0

    def record_failure(self, service_name: str = "default"):
        self._failures[service_name] = self._failures.get(service_name, 0) + 1
        if self._failures[service_name] >= self.failure_threshold:
            self._open_circuits[service_name] = True

    def record_success(self, service_name: str = "default"):
        self._failures[service_name] = 0
        self._open_circuits[service_name] = False

    def reset(self, service_name: str = "default"):
        self._failures[service_name] = 0
        self._open_circuits[service_name] = False

    def execute_with_fallback(
        self,
        jar_hp: float,
        emergency_overdrive: bool,
        main_func: Callable,
        fallback_func: Callable,
        service_name: str = "default"
    ) -> Any:
        is_main_async = inspect.iscoroutinefunction(main_func)
        is_fallback_async = inspect.iscoroutinefunction(fallback_func)

        if is_main_async or is_fallback_async:
            async def _async_exec():
                if self.is_api_allowed(jar_hp, emergency_overdrive, service_name):
                    try:
                        res = await main_func() if is_main_async else main_func()
                        self.record_success(service_name)
                        return res
                    except Exception:
                        self.record_failure(service_name)
                        return await fallback_func() if is_fallback_async else fallback_func()
                else:
                    return await fallback_func() if is_fallback_async else fallback_func()

            return _async_exec()

        if self.is_api_allowed(jar_hp, emergency_overdrive, service_name):
            try:
                res = main_func()
                self.record_success(service_name)
                return res
            except Exception:
                self.record_failure(service_name)
                return fallback_func()
        else:
            return fallback_func()
