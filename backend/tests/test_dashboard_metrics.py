import pytest
from datetime import datetime, timezone
from app.database import engine, Base, AsyncSessionLocal
from app.models import AlertNotificationLog, ExternalCostConfig
from app.routers.metrics import get_monthly_metrics, get_monthly_cost
from app.scheduler_tasks import auto_verify_false_alarms_routine
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_alert_log_metrics_and_cost():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    current_month = now.strftime("%Y-%m")

    async with AsyncSessionLocal() as session:
        # Seed 3 alert logs: 1 true alarm, 1 user false alarm, 1 pending verification
        l1 = AlertNotificationLog(
            chat_id="user_1",
            location_name="home",
            latitude=13.75,
            longitude=100.5,
            alerted_at=now,
            rain_intensity_mm=5.0,
            alert_type="rain",
            user_feedback_result=None,
            auto_verify_result="true_alarm"
        )
        l2 = AlertNotificationLog(
            chat_id="user_2",
            location_name="condo",
            latitude=13.75,
            longitude=100.5,
            alerted_at=now,
            rain_intensity_mm=1.0,
            alert_type="rain",
            user_feedback_result="false_alarm",
            auto_verify_result=None
        )
        session.add_all([l1, l2])

        # Seed external cost config
        ext = ExternalCostConfig(
            service_name="tmd_proxy",
            month=current_month,
            amount_thb=200.0
        )
        session.add(ext)
        await session.commit()

    # 1. Test GET /monthly endpoint
    res_metrics = await get_monthly_metrics(month=current_month)
    assert res_metrics["total_alerts"] >= 2
    assert res_metrics["false_alarms_user"] >= 1
    assert res_metrics["false_alarm_rate_pct"] > 0

    # 2. Test GET /cost endpoint
    res_cost = await get_monthly_cost(month=current_month)
    assert res_cost["external_cost_thb"] >= 200.0
    assert res_cost["total_cost_thb"] > 0
    assert res_cost["cost_per_alert"] > 0
    assert res_cost["cost_per_true_alert"] > 0

    # 3. Test auto_verify_false_alarms_routine
    with patch("app.services.weather_manager.WeatherManager.predict_rain", new_callable=AsyncMock) as mock_predict:
        mock_predict.return_value = {"max_rain": 0.0} # Rain stopped -> false alarm
        result = await auto_verify_false_alarms_routine()
        assert result["status"] == "ok"
