"""Tests for /overdrive Telegram admin command (handle_overdrive_command)."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, call


def _make_mock_session(record):
    """Build a mock AsyncSessionLocal context manager that returns `record` from execute()."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=record)

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_begin = AsyncMock()
    mock_begin.__aenter__ = AsyncMock(return_value=None)
    mock_begin.__aexit__ = AsyncMock(return_value=False)
    mock_session.begin = MagicMock(return_value=mock_begin)

    mock_session_cls = MagicMock(return_value=mock_session)
    return mock_session_cls, mock_session


@pytest.mark.asyncio
async def test_overdrive_on_writes_true_to_db():
    """Turning overdrive ON should upsert emergency_overdrive='true' in SystemConfig."""
    mock_record = MagicMock()
    mock_record.value_json = json.dumps("false")
    mock_session_cls, mock_session = _make_mock_session(mock_record)

    with (
        patch("app.routers.webhook_admin.check_admin_access", AsyncMock(return_value=True)),
        patch("app.database.AsyncSessionLocal", mock_session_cls),
        patch("app.routers.webhook_admin._reply", AsyncMock()) as mock_reply,
        patch("app.routers.webhook_admin.log_audit_event"),
    ):
        from app.routers.webhook_admin import handle_overdrive_command
        await handle_overdrive_command(chat_id=12345, command="/overdrive on", username="admin")

        # Value should have been set to "true"
        assert mock_record.value_json == json.dumps("true")
        # Reply should mention "Extended Lifespan Mode"
        reply_text = mock_reply.call_args[0][1]
        assert "Extended Lifespan Mode" in reply_text


@pytest.mark.asyncio
async def test_overdrive_off_writes_false_to_db():
    """Turning overdrive OFF should upsert emergency_overdrive='false' in SystemConfig."""
    mock_record = MagicMock()
    mock_record.value_json = json.dumps("true")
    mock_session_cls, mock_session = _make_mock_session(mock_record)

    with (
        patch("app.routers.webhook_admin.check_admin_access", AsyncMock(return_value=True)),
        patch("app.database.AsyncSessionLocal", mock_session_cls),
        patch("app.routers.webhook_admin._reply", AsyncMock()) as mock_reply,
        patch("app.routers.webhook_admin.log_audit_event"),
    ):
        from app.routers.webhook_admin import handle_overdrive_command
        await handle_overdrive_command(chat_id=12345, command="/overdrive off", username="admin")

        assert mock_record.value_json == json.dumps("false")
        reply_text = mock_reply.call_args[0][1]
        assert "ปิดแล้ว" in reply_text


@pytest.mark.asyncio
async def test_overdrive_status_reads_current_value():
    """'/overdrive status' should read and display current value without writing."""
    mock_record = MagicMock()
    mock_record.value_json = json.dumps("true")
    mock_session_cls, mock_session = _make_mock_session(mock_record)

    with (
        patch("app.routers.webhook_admin.check_admin_access", AsyncMock(return_value=True)),
        patch("app.database.AsyncSessionLocal", mock_session_cls),
        patch("app.routers.webhook_admin._reply", AsyncMock()) as mock_reply,
    ):
        from app.routers.webhook_admin import handle_overdrive_command
        await handle_overdrive_command(chat_id=12345, command="/overdrive status")

        reply_text = mock_reply.call_args[0][1]
        assert "ACTIVE" in reply_text


@pytest.mark.asyncio
async def test_overdrive_invalid_action_sends_help():
    """Unknown action should reply with usage help (no DB access)."""
    with (
        patch("app.routers.webhook_admin.check_admin_access", AsyncMock(return_value=True)),
        patch("app.routers.webhook_admin._reply", AsyncMock()) as mock_reply,
    ):
        from app.routers.webhook_admin import handle_overdrive_command
        await handle_overdrive_command(chat_id=12345, command="/overdrive blah")

        reply_text = mock_reply.call_args[0][1]
        assert "รูปแบบการใช้งาน" in reply_text


@pytest.mark.asyncio
async def test_overdrive_no_admin_access_exits_silently():
    """Non-admin calling /overdrive should exit silently without making DB calls."""
    with (
        patch("app.routers.webhook_admin.check_admin_access", AsyncMock(return_value=False)),
        patch("app.database.AsyncSessionLocal") as mock_db,
    ):
        from app.routers.webhook_admin import handle_overdrive_command
        await handle_overdrive_command(chat_id=99999, command="/overdrive on")
        mock_db.assert_not_called()
