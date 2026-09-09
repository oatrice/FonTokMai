import pytest
import pytest_asyncio
import base64
import json
import io
import csv
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from app.main import app
from app.routers.webhook import telegram_webhook
import app.services.billing_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_cloud_tasks():
    with patch("app.services.cloud_tasks.CloudTasksService") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.enqueue_task = AsyncMock(return_value=None)
        mock_cls.return_value = mock_instance
        yield mock_instance

def create_webhook_request(chat_id: int, text: str):
    request = AsyncMock()
    request.json.return_value = {
        "message": {
            "chat": {"id": chat_id},
            "from": {"username": "test_user"},
            "text": text
        }
    }
    return request

@pytest.mark.asyncio
async def test_metrics_command_security():
    chat_id = 999
    # Unauthorized request (not in DEVELOPER_CHAT_IDS, no active bypass)
    req = create_webhook_request(chat_id, "/metrics")
    bg_tasks = BackgroundTasks()

    with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
        with patch("app.services.telegram.DEVELOPER_CHAT_IDS", ["123"]):
            with patch("app.dependencies.get_repo_context") as mock_ctx:
                mock_repo = AsyncMock()
                mock_repo.has_active_admin_bypass.return_value = False
                mock_ctx.return_value.__aenter__.return_value = mock_repo
                
                with patch("app.services.telegram.send_telegram_message") as mock_send:
                    await telegram_webhook(req, bg_tasks)
                    # Execute bg task
                    for t in bg_tasks.tasks:
                        await t.func(*t.args, **t.kwargs)
                    mock_send.assert_called_with(chat_id, "⚠️ ขออภัยครับ คำสั่งนี้ไม่เปิดให้ใช้งานในระบบปัจจุบัน")

@pytest.mark.asyncio
async def test_metrics_command_success():
    chat_id = 123
    req = create_webhook_request(chat_id, "/metrics 5")
    bg_tasks = BackgroundTasks()

    dummy_logs = [
        {
            "routine_name": "fetch_tmd_radar",
            "run_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            "duration_s": 5.4,
            "alerts_sent": 2,
            "locations_checked": 10,
            "errors": 0,
            "extra_data": {"test": "data"}
        }
    ]

    with patch("app.services.telegram.DEVELOPER_CHAT_IDS", [str(chat_id)]):
        with patch("app.dependencies.get_repo_context") as mock_ctx:
            mock_repo = AsyncMock()
            mock_repo.has_active_admin_bypass.return_value = True
            mock_repo.get_cron_metrics.return_value = dummy_logs
            mock_ctx.return_value.__aenter__.return_value = mock_repo
            
            with patch("app.services.telegram.send_telegram_document") as mock_send_doc:
                await telegram_webhook(req, bg_tasks)
                for t in bg_tasks.tasks:
                    await t.func(*t.args, **t.kwargs)
                
                # Verify repo.get_cron_metrics was called with days=5
                mock_repo.get_cron_metrics.assert_called_with(days=5)
                
                # Verify document was sent
                mock_send_doc.assert_called_once()
                args, kwargs = mock_send_doc.call_args
                assert args[0] == chat_id
                assert args[2] == "metrics_5_days.csv"
                # Check CSV contents
                csv_bytes = args[1]
                csv_str = csv_bytes.decode("utf-8")
                assert "routine_name,run_at,duration_s,alerts_sent,locations_checked,errors,extra_data" in csv_str
                assert "fetch_tmd_radar" in csv_str

@pytest.mark.asyncio
async def test_setbudget_command_security():
    chat_id = 999
    req = create_webhook_request(chat_id, "/setbudget 20")
    bg_tasks = BackgroundTasks()

    with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
        with patch("app.services.telegram.DEVELOPER_CHAT_IDS", ["123"]):
            with patch("app.dependencies.get_repo_context") as mock_ctx:
                mock_repo = AsyncMock()
                mock_repo.has_active_admin_bypass.return_value = False
                mock_ctx.return_value.__aenter__.return_value = mock_repo
                
                with patch("app.services.telegram.send_telegram_message") as mock_send:
                    await telegram_webhook(req, bg_tasks)
                    for t in bg_tasks.tasks:
                        await t.func(*t.args, **t.kwargs)
                    mock_send.assert_called_with(chat_id, "⚠️ ขออภัยครับ คำสั่งนี้ไม่เปิดให้ใช้งานในระบบปัจจุบัน")

@pytest.mark.asyncio
async def test_setbudget_command_success():
    chat_id = 123
    req = create_webhook_request(chat_id, "/setbudget 15.5")
    bg_tasks = BackgroundTasks()

    with patch("app.services.telegram.DEVELOPER_CHAT_IDS", [str(chat_id)]):
        with patch("app.dependencies.get_repo_context") as mock_ctx:
            mock_repo = AsyncMock()
            mock_repo.has_active_admin_bypass.return_value = True
            mock_ctx.return_value.__aenter__.return_value = mock_repo
            
            with patch("app.services.telegram.send_telegram_message") as mock_send:
                with patch("app.services.billing_service.BillingService") as mock_billing_cls:
                    mock_billing_svc = AsyncMock()
                    mock_billing_svc.update_budget.return_value = True
                    mock_billing_cls.return_value = mock_billing_svc

                    await telegram_webhook(req, bg_tasks)
                    for t in bg_tasks.tasks:
                        await t.func(*t.args, **t.kwargs)
                    
                    mock_billing_svc.update_budget.assert_called_once_with(15.5)
                    mock_send.assert_called_with(
                        chat_id, "✅ ปรับงบประมาณ GCP สำเร็จเป็น 15.5 THB เรียบร้อยแล้ว"
                    )

@pytest.mark.asyncio
async def test_setbudget_command_invalid_args():
    chat_id = 123
    req = create_webhook_request(chat_id, "/setbudget abc")
    bg_tasks = BackgroundTasks()

    with patch("app.services.telegram.DEVELOPER_CHAT_IDS", [str(chat_id)]):
        with patch("app.dependencies.get_repo_context") as mock_ctx:
            mock_repo = AsyncMock()
            mock_repo.has_active_admin_bypass.return_value = True
            mock_ctx.return_value.__aenter__.return_value = mock_repo
            
            with patch("app.services.telegram.send_telegram_message") as mock_send:
                await telegram_webhook(req, bg_tasks)
                for t in bg_tasks.tasks:
                    await t.func(*t.args, **t.kwargs)
                
                mock_send.assert_called_with(
                    chat_id, "❌ รูปแบบการใช้งานไม่ถูกต้อง กรุณาพิมพ์: /setbudget <จำนวนงบประมาณ (ตัวเลข)>"
                )

@patch("app.routers.webhook_admin.check_admin_access", new_callable=AsyncMock, return_value=True)
@pytest.mark.asyncio
async def test_restore_public_access_command_resumes_schedulers(mock_admin_check):
    from app.routers.webhook_admin import handle_restore_public_access_command
    chat_id = 123

    with patch("app.dependencies.get_repo_context") as mock_ctx:
        mock_repo = AsyncMock()
        mock_repo.get_system_settings.return_value = {"emergency_shutdown": True}
        mock_ctx.return_value.__aenter__.return_value = mock_repo

        with patch("app.routers.webhook_admin._run_admin_script", new_callable=AsyncMock) as mock_run_script:
            with patch("app.routers.webhook_admin._resume_cloud_scheduler_jobs") as mock_resume:
                mock_resume.return_value = {"fonmayang-check-rain": "RESUMED"}
                await handle_restore_public_access_command(chat_id, "/restore_public_access")

                mock_repo.set_system_settings.assert_called_once_with({"emergency_shutdown": False})
                mock_resume.assert_called_once()
                mock_run_script.assert_called_once()

@patch("app.routers.webhook_admin.get_gcp_access_token")
def test_resume_cloud_scheduler_jobs_skips_permanently_paused_jobs(mock_get_token):
    from app.routers.webhook_admin import _resume_cloud_scheduler_jobs
    import respx
    from httpx import Response

    mock_get_token.return_value = "fake-token"

    with respx.mock:
        respx.post(url__regex=r"https://cloudscheduler\.googleapis\.com/v1/projects/.*/locations/.*/jobs/.*:resume").mock(
            return_value=Response(200, json={})
        )

        results = _resume_cloud_scheduler_jobs()
        assert isinstance(results, dict)
        assert len(results) > 0
        for job_name, status in results.items():
            assert status == "RESUMED"
        # Should not resume jobs configured as PAUSED by default (like fonmayang-disasters-freq)
        assert "fonmayang-disasters-freq" not in results


