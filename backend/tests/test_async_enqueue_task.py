import inspect
import pytest
from app.services.cloud_tasks import CloudTasksService

def test_enqueue_task_is_async():
    """Assert that CloudTasksService.enqueue_task is a coroutine function (async def)."""
    assert inspect.iscoroutinefunction(CloudTasksService.enqueue_task), "enqueue_task must be an async function"
