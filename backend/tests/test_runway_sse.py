import pytest
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_runway_stream():
    # Test the SSE endpoint. We can use a streaming client request.
    with client.stream("GET", "/api/v1/runway/stream") as response:
        assert response.status_code == 200
        # Check first line is event or data
        first_line = next(response.iter_lines())
        assert first_line.startswith("data: ") or first_line.startswith("event: ")

def test_runway_stream_emergency_overdrive():
    with client.stream("GET", "/api/v1/runway/stream?emergency_overdrive=true") as response:
        assert response.status_code == 200
        first_line = next(response.iter_lines())
        assert first_line.startswith("data: ")
        payload = json.loads(first_line.replace("data: ", ""))
        assert payload["emergency_overdrive"] is True
        assert payload["remaining_days"] == "Infinity"
        assert payload["status"] == "INVINCIBLE"
