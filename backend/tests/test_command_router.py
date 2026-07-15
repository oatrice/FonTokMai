import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import BackgroundTasks
from app.services.command_router import TelegramCommandRouter

@pytest.mark.asyncio
async def test_command_router_binding_and_matching():
    router = TelegramCommandRouter()
    
    @router.bind("/rain")
    async def handle_rain():
        pass
        
    @router.bind("/rain_pro")
    async def handle_rain_pro():
        pass
        
    # Longest prefix match check
    match1 = router.match("/rain_pro test")
    assert match1 is not None
    assert match1[0] == "/rain_pro"
    
    match2 = router.match("/rain test")
    assert match2 is not None
    assert match2[0] == "/rain"
    
    # No match check
    match3 = router.match("/unregistered")
    assert match3 is None

@pytest.mark.asyncio
async def test_command_router_dispatch_success_cloud_tasks():
    router = TelegramCommandRouter()
    
    handler_called = False
    @router.bind("/test_cmd", task_route="worker/test-route", loading_text="Loading...")
    async def test_handler(chat_id, command, message_id_to_edit):
        nonlocal handler_called
        handler_called = True

    background_tasks = BackgroundTasks()
    check_admin = AsyncMock(return_value=True)
    send_msg = AsyncMock()
    send_msg_id = AsyncMock(return_value=123)
    enqueue_task = AsyncMock(return_value=True) # Success enqueuing
    
    handled = await router.dispatch(
        text="/test_cmd arg",
        chat_id=111,
        username="user",
        background_tasks=background_tasks,
        check_admin_access_fn=check_admin,
        send_telegram_message_fn=send_msg,
        send_telegram_message_return_id_fn=send_msg_id,
        enqueue_task_fn=enqueue_task
    )
    
    assert handled is True
    # Should send loading message
    send_msg_id.assert_called_once_with(111, "Loading...")
    # Should enqueue to Cloud Tasks
    enqueue_task.assert_called_once_with("worker/test-route", {
        "chat_id": 111,
        "command": "/test_cmd arg",
        "username": "user",
        "message_id_to_edit": 123
    })
    # Handler should NOT be called locally
    assert handler_called is False

@pytest.mark.asyncio
async def test_command_router_dispatch_fallback_background_tasks():
    router = TelegramCommandRouter()
    
    handler_args = {}
    @router.bind("/test_fallback", task_route="worker/test-fallback", loading_text="Loading...")
    async def test_handler(chat_id, command, message_id_to_edit):
        handler_args["chat_id"] = chat_id
        handler_args["command"] = command
        handler_args["message_id_to_edit"] = message_id_to_edit

    background_tasks = BackgroundTasks()
    check_admin = AsyncMock(return_value=True)
    send_msg = AsyncMock()
    send_msg_id = AsyncMock(return_value=123)
    enqueue_task = AsyncMock(return_value=False) # Failed enqueuing
    
    handled = await router.dispatch(
        text="/test_fallback arg",
        chat_id=111,
        username="user",
        background_tasks=background_tasks,
        check_admin_access_fn=check_admin,
        send_telegram_message_fn=send_msg,
        send_telegram_message_return_id_fn=send_msg_id,
        enqueue_task_fn=enqueue_task
    )
    
    assert handled is True
    # Trigger background tasks execution manually
    for task in background_tasks.tasks:
        await task()
        
    assert handler_args["chat_id"] == 111
    assert handler_args["command"] == "/test_fallback arg"
    assert handler_args["message_id_to_edit"] == 123

@pytest.mark.asyncio
async def test_command_router_command_override_and_extra_kwargs():
    router = TelegramCommandRouter()
    
    handler_args = {}
    @router.bind("/check_alias", task_route="worker/rain", loading_text="Loading...", command_override="/rain tmd-radar", show_advanced=True)
    async def test_handler(chat_id, command, show_advanced, message_id_to_edit):
        handler_args["chat_id"] = chat_id
        handler_args["command"] = command
        handler_args["show_advanced"] = show_advanced
        handler_args["message_id_to_edit"] = message_id_to_edit

    background_tasks = BackgroundTasks()
    check_admin = AsyncMock(return_value=True)
    send_msg = AsyncMock()
    send_msg_id = AsyncMock(return_value=123)
    enqueue_task = AsyncMock(return_value=False) # Fallback to test local invocation
    
    handled = await router.dispatch(
        text="/check_alias",
        chat_id=111,
        username="user",
        background_tasks=background_tasks,
        check_admin_access_fn=check_admin,
        send_telegram_message_fn=send_msg,
        send_telegram_message_return_id_fn=send_msg_id,
        enqueue_task_fn=enqueue_task
    )
    
    assert handled is True
    # Trigger background tasks execution manually
    for task in background_tasks.tasks:
        await task()
        
    assert handler_args["command"] == "/rain tmd-radar"
    assert handler_args["show_advanced"] is True
    assert handler_args["message_id_to_edit"] == 123
