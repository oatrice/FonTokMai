# Manual Verification for Event Broadcaster (Issue #157)

## 1. Start the server
Run the backend server locally:
```bash
uvicorn backend.app.main:app --reload
```

## 2. Connect to the SSE stream
In a new terminal, connect using curl:
```bash
curl -N -H "Accept: text/event-stream" http://localhost:8000/api/v1/events/stream
```

You should see periodic `ping` events (every 15 seconds) if no events are broadcasted:
```
event: ping
data: {}
```

## 3. Broadcast an event (Test/Mock)
To manually broadcast an event, you can trigger any application logic that calls `event_broadcaster.broadcast_event('type', data)`, and you will see the event appear in your curl stream:
```
event: <type>
data: <data_json>
```
