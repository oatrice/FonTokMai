"""
E2E Test: EMSC Earthquake Alert Webhook
ทดสอบว่า POST /api/v1/internal/emsc-webhook ทำงานครบ pipeline:
1. รับ event payload ของแผ่นดินไหว
2. ตรวจสอบว่าอยู่ในรัศมีผลกระทบหรือไม่
3. ส่ง Telegram alert ไปหา user ที่อยู่ในรัศมี
4. กรณีแผ่นดินไหวเล็ก (< 4.5) ต้องไม่ส่ง alert
"""
import pytest
import asyncio
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock, call
from app.main import app
from app.services.disaster_manager import process_disaster_event, get_impact_radius_km

INTERNAL_SECRET = "dev_secret"  # ค่า default ใน internal.py


# ────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return TestClient(app)


def make_mock_location(chat_id=111, lat=13.75, lng=100.5, name="home"):
    loc = MagicMock()
    loc.latitude = lat
    loc.longitude = lng
    loc.name = name
    loc.chat_id = chat_id
    loc.expires_at = None
    return loc


# ────────────────────────────────────────────────────────────
# Unit Tests: get_impact_radius_km
# ────────────────────────────────────────────────────────────

def test_impact_radius_large_earthquake():
    """แผ่นดินไหว M7.0+ ต้องมีรัศมี 1000 km"""
    radius = get_impact_radius_km("earthquake", {"mag": 7.5})
    assert radius == 1000.0


def test_impact_radius_medium_earthquake():
    """แผ่นดินไหว M6.0-6.9 ต้องมีรัศมี 800 km"""
    radius = get_impact_radius_km("earthquake", {"mag": 6.2})
    assert radius == 800.0


def test_impact_radius_moderate_earthquake():
    """แผ่นดินไหว M4.5-5.9 ต้องมีรัศมี 300 km"""
    radius = get_impact_radius_km("earthquake", {"mag": 5.0})
    assert radius == 300.0


def test_impact_radius_small_earthquake_ignored():
    """แผ่นดินไหวเล็ก (< 4.5) ต้อง return 0 (ไม่แจ้งเตือน)"""
    radius = get_impact_radius_km("earthquake", {"mag": 3.9})
    assert radius == 0.0


def test_impact_radius_cyclone():
    """พายุไซโคลนต้องมีรัศมี 1000 km"""
    radius = get_impact_radius_km("cyclone", {})
    assert radius == 1000.0


# ────────────────────────────────────────────────────────────
# E2E: process_disaster_event → send Telegram alert
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_earthquake_in_radius_sends_alert():
    """
    แผ่นดินไหว M7.0 ใกล้กับ user ในรัศมี 1000 km
    ต้องส่ง alert ผ่าน Telegram
    """
    # User อยู่ที่กรุงเทพ (13.75, 100.5)
    # แผ่นดินไหวอยู่ที่เมียนมา (21.0, 96.0) ซึ่งห่างประมาณ 1000 km
    user_loc = make_mock_location(chat_id=111, lat=13.75, lng=100.5)

    mock_repo = AsyncMock()
    mock_repo.get_active_locations.return_value = [user_loc]
    mock_repo.has_disaster_alert_been_sent.return_value = False
    mock_repo.mark_disaster_alert_sent.return_value = None

    earthquake_event = {
        "id": "EQ_TEST_001",
        "lat": 21.0,
        "lng": 96.0,
        "mag": 7.2,
        "depth": 10,
        "title": "M 7.2 - Myanmar",
    }

    with patch("app.services.disaster_manager.send_grouped_disaster_alert", new_callable=AsyncMock) as mock_alert:
        await process_disaster_event(mock_repo, "earthquake", earthquake_event)

    mock_alert.assert_called_once()
    call_args = mock_alert.call_args[0]
    assert call_args[0] == 111  # chat_id
    assert call_args[1] == "earthquake"


@pytest.mark.asyncio
async def test_earthquake_too_far_no_alert():
    """
    แผ่นดินไหว M6.0 แต่ user อยู่ไกลเกินรัศมี 800 km
    ต้องไม่ส่ง alert
    """
    # User อยู่ที่กรุงเทพ
    user_loc = make_mock_location(chat_id=222, lat=13.75, lng=100.5)

    mock_repo = AsyncMock()
    mock_repo.get_active_locations.return_value = [user_loc]
    mock_repo.has_disaster_alert_been_sent.return_value = False

    # แผ่นดินไหวอยู่ที่ญี่ปุ่น ห่างมาก >4000 km
    earthquake_event = {
        "id": "EQ_TEST_002",
        "lat": 35.0,
        "lng": 135.0,
        "mag": 6.5,
        "depth": 30,
        "title": "M 6.5 - Japan",
    }

    with patch("app.services.disaster_manager.send_grouped_disaster_alert", new_callable=AsyncMock) as mock_alert:
        await process_disaster_event(mock_repo, "earthquake", earthquake_event)

    mock_alert.assert_not_called()


@pytest.mark.asyncio
async def test_small_earthquake_no_alert():
    """
    แผ่นดินไหวขนาดเล็ก M3.0 ต้องไม่ส่ง alert (impact radius = 0)
    """
    user_loc = make_mock_location(chat_id=333, lat=13.75, lng=100.5)

    mock_repo = AsyncMock()
    mock_repo.get_active_locations.return_value = [user_loc]

    earthquake_event = {
        "id": "EQ_TEST_003",
        "lat": 14.0,
        "lng": 101.0,
        "mag": 3.0,  # เล็กมาก
        "depth": 5,
        "title": "M 3.0 - Thailand",
    }

    with patch("app.services.disaster_manager.send_grouped_disaster_alert", new_callable=AsyncMock) as mock_alert:
        await process_disaster_event(mock_repo, "earthquake", earthquake_event)

    mock_alert.assert_not_called()


@pytest.mark.asyncio
async def test_duplicate_alert_not_sent_twice():
    """
    ถ้าเคยส่ง alert แผ่นดินไหวตัวนี้ไปแล้ว (has_disaster_alert_been_sent=True)
    ต้องไม่ส่งซ้ำ
    """
    user_loc = make_mock_location(chat_id=444, lat=13.75, lng=100.5)

    mock_repo = AsyncMock()
    mock_repo.get_active_locations.return_value = [user_loc]
    mock_repo.has_disaster_alert_been_sent.return_value = True  # เคยส่งแล้ว

    earthquake_event = {
        "id": "EQ_TEST_DUP",
        "lat": 21.0,
        "lng": 96.0,
        "mag": 7.0,
        "depth": 10,
        "title": "M 7.0 - Myanmar (Duplicate)",
    }

    with patch("app.services.disaster_manager.send_grouped_disaster_alert", new_callable=AsyncMock) as mock_alert:
        await process_disaster_event(mock_repo, "earthquake", earthquake_event)

    mock_alert.assert_not_called()


# ────────────────────────────────────────────────────────────
# HTTP Endpoint Tests
# ────────────────────────────────────────────────────────────

def test_emsc_webhook_unauthorized(client):
    """POST /api/v1/internal/emsc-webhook โดยไม่มี secret ต้องได้ 401"""
    response = client.post(
        "/api/v1/internal/emsc-webhook",
        json={"id": "EQ001", "lat": 13.0, "lng": 100.0, "mag": 6.0}
    )
    assert response.status_code == 401


def test_emsc_webhook_missing_fields(client):
    """POST ที่ขาด id หรือ lat ต้องได้ 400"""
    response = client.post(
        "/api/v1/internal/emsc-webhook",
        json={"mag": 6.0},  # ไม่มี id, lat
        headers={"X-Internal-Secret": INTERNAL_SECRET}
    )
    assert response.status_code == 400


def test_emsc_webhook_accepts_valid_event(client):
    """
    POST event ที่ถูกต้องต้องได้ 200 และ status=ok
    (background task จะ process ทีหลัง)
    """
    mock_repo = AsyncMock()
    mock_repo.get_active_locations.return_value = []  # ไม่มี user → ไม่ต้องส่ง alert

    @asynccontextmanager
    async def mock_repo_ctx():
        yield mock_repo

    with patch("app.routers.internal.get_repo_context", mock_repo_ctx), \
         patch("app.services.disaster_manager.send_grouped_disaster_alert", new_callable=AsyncMock):

        response = client.post(
            "/api/v1/internal/emsc-webhook",
            json={
                "id": "EQ_HTTP_001",
                "lat": 21.0,
                "lng": 96.0,
                "mag": 7.2,
                "depth": 10,
                "title": "M 7.2 - Myanmar"
            },
            headers={"X-Internal-Secret": INTERNAL_SECRET}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
