import asyncio

class EventBroadcaster:
    def __init__(self):
        self.subscribers = set()

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    async def broadcast_event(self, event_type: str, data: dict):
        event = {
            "event": event_type,
            "data": data
        }
        for queue in list(self.subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

event_broadcaster = EventBroadcaster()
