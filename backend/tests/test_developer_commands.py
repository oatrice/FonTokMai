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
        mock_instance.enqueue_task.return_value = None
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

    with patch("app.routers.webhook.DEVELOPER_CHAT_IDS", ["123"]):
        with patch("app.routers.webhook.get_repo_context") as mock_ctx:
            mock_repo = AsyncMock()
            mock_repo.has_active_admin_bypass.return_value = False
            mock_ctx.return_value.__aenter__.return_value = mock_repo
            
            with patch("app.routers.webhook.send_telegram_message") as mock_send:
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

    with patch("app.routers.webhook.DEVELOPER_CHAT_IDS", [str(chat_id)]):
        with patch("app.routers.webhook.get_repo_context") as mock_ctx:
            mock_repo = AsyncMock()
            mock_repo.has_active_admin_bypass.return_value = True
            mock_repo.get_cron_metrics.return_value = dummy_logs
            mock_ctx.return_value.__aenter__.return_value = mock_repo
            
            with patch("app.routers.webhook.send_telegram_document") as mock_send_doc:
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

    with patch("app.routers.webhook.DEVELOPER_CHAT_IDS", ["123"]):
        with patch("app.routers.webhook.get_repo_context") as mock_ctx:
            mock_repo = AsyncMock()
            mock_repo.has_active_admin_bypass.return_value = False
            mock_ctx.return_value.__aenter__.return_value = mock_repo
            
            with patch("app.routers.webhook.send_telegram_message") as mock_send:
                await telegram_webhook(req, bg_tasks)
                for t in bg_tasks.tasks:
                    await t.func(*t.args, **t.kwargs)
                mock_send.assert_called_with(chat_id, "⚠️ ขออภัยครับ คำสั่งนี้ไม่เปิดให้ใช้งานในระบบปัจจุบัน")

@pytest.mark.asyncio
async def test_setbudget_command_success():
    chat_id = 123
    req = create_webhook_request(chat_id, "/setbudget 15.5")
    bg_tasks = BackgroundTasks()

    with patch("app.routers.webhook.DEVELOPER_CHAT_IDS", [str(chat_id)]):
        with patch("app.routers.webhook.get_repo_context") as mock_ctx:
            mock_repo = AsyncMock()
            mock_repo.has_active_admin_bypass.return_value = True
            mock_ctx.return_value.__aenter__.return_value = mock_repo
            
            with patch("app.routers.webhook.send_telegram_message") as mock_send:
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

    with patch("app.routers.webhook.DEVELOPER_CHAT_IDS", [str(chat_id)]):
        with patch("app.routers.webhook.get_repo_context") as mock_ctx:
            mock_repo = AsyncMock()
            mock_repo.has_active_admin_bypass.return_value = True
            mock_ctx.return_value.__aenter__.return_value = mock_repo
            
            with patch("app.routers.webhook.send_telegram_message") as mock_send:
                await telegram_webhook(req, bg_tasks)
                for t in bg_tasks.tasks:
                    await t.func(*t.args, **t.kwargs)
                
                mock_send.assert_called_with(
                    chat_id, "❌ รูปแบบการใช้งานไม่ถูกต้อง กรุณาพิมพ์: /setbudget <จำนวนงบประมาณ (ตัวเลข)>"
                )
