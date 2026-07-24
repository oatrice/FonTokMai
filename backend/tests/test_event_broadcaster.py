import pytest
import asyncio
import json
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.services.event_broadcaster import EventBroadcaster

@pytest.fixture
def broadcaster():
    return EventBroadcaster()

@pytest.mark.asyncio
async def test_event_broadcaster_subscribe(broadcaster):
    queue = broadcaster.subscribe()
    assert isinstance(queue, asyncio.Queue)
    assert queue in broadcaster.subscribers
    broadcaster.unsubscribe(queue)
    assert queue not in broadcaster.subscribers

@pytest.mark.asyncio
async def test_event_broadcaster_broadcast(broadcaster):
    queue1 = broadcaster.subscribe()
    queue2 = broadcaster.subscribe()

    await broadcaster.broadcast_event('test_event', {'message': 'hello'})

    event1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
    event2 = await asyncio.wait_for(queue2.get(), timeout=1.0)

    assert event1['event'] == 'test_event'
    assert event1['data'] == {'message': 'hello'}
    
    assert event2['event'] == 'test_event'
    assert event2['data'] == {'message': 'hello'}

    broadcaster.unsubscribe(queue1)
    broadcaster.unsubscribe(queue2)

@pytest.mark.asyncio
async def test_sse_endpoint(mocker):
    from app.routers.events import router as events_router
    from app.services.event_broadcaster import event_broadcaster
    
    app = FastAPI()
    app.include_router(events_router)

    fake_queue = asyncio.Queue()
    await fake_queue.put({'event': 'custom_event', 'data': {'foo': 'bar'}})
    
    original_get = fake_queue.get
    call_count = 0
    async def mock_get():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return await original_get()
        else:
            raise asyncio.CancelledError()
            
    fake_queue.get = mock_get
    
    mocker.patch.object(event_broadcaster, 'subscribe', return_value=fake_queue)
    mocker.patch.object(event_broadcaster, 'unsubscribe')

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://testserver') as client:
        response = await client.get('/api/v1/events/stream')
        assert response.status_code == 200
        assert 'text/event-stream' in response.headers['content-type']
        assert 'event: custom_event' in response.text
        assert 'data: {"foo": "bar"}' in response.text
