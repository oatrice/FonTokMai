import pytest
from datetime import datetime, timezone
from app.database import engine, Base, AsyncSessionLocal
from app.models import SystemUsageEvent, ExternalCostConfig
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
        # Seed 4 usage events:
        # 1 true proactive alarm
        # 1 false proactive alarm
        # 1 on-demand query
        # 1 mock test (should be ignored in costs and accuracy)
        l1 = SystemUsageEvent(
            chat_id="user_1",
            location_name="home",
            latitude=13.75,
            longitude=100.5,
            alerted_at=now,
            rain_intensity_mm=5.0,
            alert_type="rain",
            user_feedback_result=None,
            auto_verify_result="true_alarm",
            event_category="proactive_alert",
            command_name="proactive_scheduler",
            is_mock=False
        )
        l2 = SystemUsageEvent(
            chat_id="user_2",
            location_name="condo",
            latitude=13.75,
            longitude=100.5,
            alerted_at=now,
            rain_intensity_mm=1.0,
            alert_type="rain",
            user_feedback_result="false_alarm",
            auto_verify_result=None,
            event_category="proactive_alert",
            command_name="proactive_scheduler",
            is_mock=False
        )
        l3 = SystemUsageEvent(
            chat_id="user_1",
            location_name="office",
            latitude=13.75,
            longitude=100.5,
            alerted_at=now,
            rain_intensity_mm=0.0,
            alert_type="rain",
            user_feedback_result=None,
            auto_verify_result=None,
            event_category="ondemand_query",
            command_name="/check",
            is_mock=False
        )
        l4 = SystemUsageEvent(
            chat_id="user_3",
            location_name="test",
            latitude=13.75,
            longitude=100.5,
            alerted_at=now,
            rain_intensity_mm=5.0,
            alert_type="rain",
            user_feedback_result=None,
            auto_verify_result="true_alarm",
            event_category="mock_test",
            command_name="/mock_rain",
            is_mock=True
        )
        session.add_all([l1, l2, l3, l4])

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
    assert res_metrics["total_alerts"] == 2  # Only proactive alerts, mock excluded
    assert res_metrics["false_alarms_user"] == 1
    assert res_metrics["false_alarm_rate_pct"] == 50.0

    # 2. Test GET /cost endpoint
    res_cost = await get_monthly_cost(month=current_month)
    assert res_cost["external_cost_thb"] >= 200.0
    assert res_cost["total_cost_thb"] > 0
    assert "cost_per_proactive_alert" in res_cost
    assert "cost_per_ondemand_query" in res_cost
    assert "blended_cost_per_active_user" in res_cost

    # 3. Test auto_verify_false_alarms_routine
    with patch("app.services.weather_manager.WeatherManager.predict_rain", new_callable=AsyncMock) as mock_predict:
        mock_predict.return_value = {"max_rain": 0.0} # Rain stopped -> false alarm
        result = await auto_verify_false_alarms_routine()
        assert result["status"] == "ok"

    # 4. Test admin Telegram commands: /stats and /cost
    from app.routers.webhook_commands import handle_stats_command, handle_cost_command
    with patch("app.routers.webhook_commands._reply", new_callable=AsyncMock) as mock_reply:
        await handle_stats_command(998877, f"/stats {current_month}")
        assert mock_reply.called
        stats_text = mock_reply.call_args[0][1]
        assert "สรุปความแม่นยำเรดาร์" in stats_text
        assert current_month in stats_text

    with patch("app.routers.webhook_commands._reply", new_callable=AsyncMock) as mock_reply:
        await handle_cost_command(998877, f"/cost {current_month}")
        assert mock_reply.called
        cost_text = mock_reply.call_args[0][1]
        assert "สรุปต้นทุนระบบ" in cost_text
        assert current_month in cost_text
