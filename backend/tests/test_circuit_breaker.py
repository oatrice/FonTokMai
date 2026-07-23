import pytest
import asyncio
from app.services.circuit_breaker import CircuitBreaker

def test_circuit_breaker_allows_when_jar_positive():
    breaker = CircuitBreaker()
    assert breaker.is_api_allowed(jar_hp=10.0, emergency_overdrive=False) == True

def test_circuit_breaker_blocks_when_jar_empty():
    breaker = CircuitBreaker()
    assert breaker.is_api_allowed(jar_hp=0.0, emergency_overdrive=False) == False
    assert breaker.is_api_allowed(jar_hp=-5.0, emergency_overdrive=False) == False

def test_circuit_breaker_allows_when_jar_empty_but_emergency_overdrive():
    breaker = CircuitBreaker()
    # Even if HP <= 0, overdrive forces it ON
    assert breaker.is_api_allowed(jar_hp=0.0, emergency_overdrive=True) == True
    assert breaker.is_api_allowed(jar_hp=-5.0, emergency_overdrive=True) == True

def test_circuit_breaker_middleware_fallback():
    breaker = CircuitBreaker()
    
    def mock_paid_api():
        return "paid_data"
        
    def mock_free_api():
        return "free_data"
        
    # Case 1: Healthy
    result = breaker.execute_with_fallback(
        jar_hp=10.0, 
        emergency_overdrive=False, 
        main_func=mock_paid_api, 
        fallback_func=mock_free_api
    )
    assert result == "paid_data"
    
    # Case 2: Broken (Fallback)
    result = breaker.execute_with_fallback(
        jar_hp=0.0, 
        emergency_overdrive=False, 
        main_func=mock_paid_api, 
        fallback_func=mock_free_api
    )
    assert result == "free_data"

    # Case 3: Broken but Overdrive
    result = breaker.execute_with_fallback(
        jar_hp=0.0, 
        emergency_overdrive=True, 
        main_func=mock_paid_api, 
        fallback_func=mock_free_api
    )
    assert result == "paid_data"

@pytest.mark.asyncio
async def test_circuit_breaker_async_execution():
    breaker = CircuitBreaker()

    async def async_paid_api():
        await asyncio.sleep(0.001)
        return "async_paid_data"

    async def async_free_api():
        await asyncio.sleep(0.001)
        return "async_free_data"

    # Allowed async call
    res1 = await breaker.execute_with_fallback(
        jar_hp=10.0,
        emergency_overdrive=False,
        main_func=async_paid_api,
        fallback_func=async_free_api
    )
    assert res1 == "async_paid_data"

    # Fallback async call
    res2 = await breaker.execute_with_fallback(
        jar_hp=0.0,
        emergency_overdrive=False,
        main_func=async_paid_api,
        fallback_func=async_free_api
    )
    assert res2 == "async_free_data"

def test_circuit_breaker_failure_threshold_and_recovery():
    breaker = CircuitBreaker(failure_threshold=2)
    
    def failing_api():
        raise RuntimeError("API Error")
        
    def fallback_api():
        return "fallback"

    # 1st failure
    res1 = breaker.execute_with_fallback(10.0, False, failing_api, fallback_api, service_name="tmd")
    assert res1 == "fallback"
    assert breaker.is_api_allowed(10.0, False, service_name="tmd") == True

    # 2nd failure -> threshold reached, trips circuit
    res2 = breaker.execute_with_fallback(10.0, False, failing_api, fallback_api, service_name="tmd")
    assert res2 == "fallback"
    assert breaker.is_api_allowed(10.0, False, service_name="tmd") == False

    # Emergency overdrive bypasses tripped circuit
    assert breaker.is_api_allowed(10.0, True, service_name="tmd") == True

    # System recovery
    breaker.reset(service_name="tmd")
    assert breaker.is_api_allowed(10.0, False, service_name="tmd") == True

