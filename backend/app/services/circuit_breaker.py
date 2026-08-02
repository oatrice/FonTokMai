import inspect
import logging
from typing import Callable, Any, Awaitable

logger = logging.getLogger(__name__)


async def _persist_circuit_breaker_state(is_tripped: bool) -> None:
    """Persist circuit_breaker_active flag to NeonDB (SystemConfig table)."""
    try:
        from app.database import AsyncSessionLocal
        from app.models import SystemConfig
        from sqlalchemy import select
        import json

        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt = select(SystemConfig).where(SystemConfig.key == "circuit_breaker_active")
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()
                new_val = json.dumps("true" if is_tripped else "false")
                if record:
                    record.value_json = new_val
                else:
                    session.add(SystemConfig(key="circuit_breaker_active", value_json=new_val))
    except Exception as e:
        logger.warning(f"circuit_breaker: failed to persist state to DB: {e}")


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

    def is_tripped(self, service_name: str = "default") -> bool:
        """Return True if any circuit is open (tripped)."""
        return any(self._open_circuits.values())

    def record_failure(self, service_name: str = "default"):
        self._failures[service_name] = self._failures.get(service_name, 0) + 1
        was_tripped = self._open_circuits.get(service_name, False)
        if self._failures[service_name] >= self.failure_threshold:
            self._open_circuits[service_name] = True
            if not was_tripped:
                # Newly tripped — persist to DB asynchronously
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(_persist_circuit_breaker_state(True))
                    else:
                        loop.run_until_complete(_persist_circuit_breaker_state(True))
                except RuntimeError:
                    pass  # No event loop available (e.g., during tests)

    def record_success(self, service_name: str = "default"):
        was_tripped = self._open_circuits.get(service_name, False)
        self._failures[service_name] = 0
        self._open_circuits[service_name] = False
        if was_tripped and not self.is_tripped():
            # All circuits reset — persist to DB asynchronously
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(_persist_circuit_breaker_state(False))
                else:
                    loop.run_until_complete(_persist_circuit_breaker_state(False))
            except RuntimeError:
                pass

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
