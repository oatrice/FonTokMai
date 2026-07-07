import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from datetime import datetime, timezone

from app.models import Base
from app.repositories.sqlite import SQLiteLocationRepository
from app.repositories.firestore import FirestoreLocationRepository
from app.services.rainbow import RainbowService
from app.routers.webhook import handle_callback_query, telegram_webhook
from fastapi import Request, BackgroundTasks

# --- Autouse Fixtures ---
@pytest.fixture(autouse=True)
def mock_cloud_tasks():
    with patch("app.services.cloud_tasks.CloudTasksService") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.enqueue_task.return_value = None
        mock_cls.return_value = mock_instance
        yield mock_instance

# --- SQLite Mock State Tests ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

@pytest_asyncio.fixture(scope="function")
async def sqlite_repo():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield SQLiteLocationRepository(session)
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_sqlite_mock_state(sqlite_repo):
    chat_id = 123
    # Default is None
    state = await sqlite_repo.get_mock_state(chat_id)
    assert state is None
    
    # Set to 'rain'
    await sqlite_repo.set_mock_state(chat_id, "rain")
    assert await sqlite_repo.get_mock_state(chat_id) == "rain"
    
    # Update to 'clear'
    await sqlite_repo.set_mock_state(chat_id, "clear")
    assert await sqlite_repo.get_mock_state(chat_id) == "clear"
    
    # Disable mock (None)
    await sqlite_repo.set_mock_state(chat_id, None)
    assert await sqlite_repo.get_mock_state(chat_id) is None

# --- Firestore Mock State Tests ---
@pytest_asyncio.fixture(scope="function")
async def firestore_repo():
    with patch("app.repositories.firestore.firebase_admin"):
        with patch("app.repositories.firestore.credentials"):
            with patch("app.repositories.firestore.firestore_async") as mock_fs:
                mock_db = MagicMock()
                mock_collection = MagicMock()
                mock_db.collection.return_value = mock_collection
                mock_fs.client.return_value = mock_db
                repo = FirestoreLocationRepository()
                repo.db = mock_db
                yield repo

@pytest.mark.asyncio
async def test_firestore_mock_state(firestore_repo):
    chat_id = 456
    
    # get_mock_state when document does not exist
    mock_doc = MagicMock()
    mock_doc.exists = False
    firestore_repo.db.collection().document().get = AsyncMock(return_value=mock_doc)
    
    state = await firestore_repo.get_mock_state(chat_id)
    assert state is None
    
    # set_mock_state to 'rain'
    firestore_repo.db.collection().document().set = AsyncMock()
    await firestore_repo.set_mock_state(chat_id, "rain")
    firestore_repo.db.collection().document().set.assert_called_with({"state": "rain"})
    
    # set_mock_state to None (delete)
    firestore_repo.db.collection().document().delete = AsyncMock()
    await firestore_repo.set_mock_state(chat_id, None)
    firestore_repo.db.collection().document().delete.assert_called()

# --- RainbowService Tests ---
@pytest.mark.asyncio
async def test_rainbow_service_mock_state():
    svc = RainbowService()
    
    # Rain mock
    rain_res = await svc.predict_rain_by_location(13.0, 100.0, mock_state="rain")
    assert rain_res["intensity"] == "หนัก (Heavy)"
    assert rain_res["duration_minutes"] == 60
    assert rain_res["predictions"][0]["rain"] > 0
    
    # Clear mock
    clear_res = await svc.predict_rain_by_location(13.0, 100.0, mock_state="clear")
    assert clear_res["intensity"] == "ไม่มีฝน (No Rain)"
    assert clear_res["duration_minutes"] == 0


# --- Webhook & Scheduler Tests ---
from app.routers.webhook import telegram_webhook
from app.scheduler_tasks import check_rain_and_alert
from app.models import UserLocation

@pytest.mark.asyncio
async def test_webhook_devmock_command():
    chat_id = 999999
    
    async def call_webhook(text):
        request = AsyncMock()
        request.json.return_value = {
            "message": {
                "chat": {"id": chat_id},
                "text": text
            }
        }
        bg_tasks = BackgroundTasks()
        with patch.dict("os.environ", {"ENVIRONMENT": "development", "BOT_ENV": "development"}):
            await telegram_webhook(request, bg_tasks)
        # Execute background tasks manually for testing
        for task in bg_tasks.tasks:
            await task.func(*task.args, **task.kwargs)
        
    with patch("app.routers.webhook.DEVELOPER_CHAT_IDS", ["123"]):
        with patch("app.routers.webhook.get_repo_context") as mock_ctx:
            mock_repo = AsyncMock()
            mock_repo.has_active_admin_bypass.return_value = False
            mock_ctx.return_value.__aenter__.return_value = mock_repo
            await call_webhook("/devmock rain")
            mock_repo.set_mock_state.assert_not_called()
            
    with patch("app.routers.webhook.DEVELOPER_CHAT_IDS", [str(chat_id)]):
        with patch("app.routers.webhook.send_telegram_message") as mock_send:
            with patch("app.routers.webhook.get_repo_context") as mock_ctx:
                with patch("app.scheduler_tasks.check_rain_and_alert", new_callable=AsyncMock) as mock_check:
                    mock_repo = AsyncMock()
                    mock_ctx.return_value.__aenter__.return_value = mock_repo
                    mock_repo.get_user_locations.return_value = []
                    
                    await call_webhook("/devmock rain")
                    mock_repo.set_mock_state.assert_called_with(chat_id, "rain")
                    mock_send.assert_called()
                    mock_check.assert_called()

                    await call_webhook("/devmock clear")
                    mock_repo.set_mock_state.assert_called_with(chat_id, "clear")

                    await call_webhook("/devmock off")
                    mock_repo.set_mock_state.assert_called_with(chat_id, None)

@pytest.mark.asyncio
async def test_scheduler_mock_state_injection():
    loc = UserLocation(chat_id=123, latitude=10.0, longitude=20.0, last_alerted_at=None)
    
    with patch("app.scheduler_tasks.get_repo_context") as mock_ctx:
        mock_repo = AsyncMock()
        mock_repo.get_active_locations.return_value = [loc]
        mock_repo.get_mock_state.return_value = "rain"
        mock_ctx.return_value.__aenter__.return_value = mock_repo
        
        with patch("app.scheduler_tasks.WeatherManager") as mock_wm_cls:
            mock_svc = AsyncMock()
            mock_wm_cls.return_value = mock_svc
            mock_svc.predict_rain.return_value = {
                "intensity": "หนัก (Heavy)",
                "duration_minutes": 60,
                "predictions": [{"time": "2026-06-02T12:00:00Z", "rain": 15.0}],
                "max_rain": 15.0,
                "wind_speed_kmh": 20.0,
                "endpoint": "tomorrow"
            }
            
            with patch("app.scheduler_tasks.send_telegram_message") as mock_send:
                with patch("app.scheduler_tasks.fetch_tmd_radar_routine", new_callable=AsyncMock) as mock_fetch:
                    with patch("app.scheduler_tasks.MetricsService") as mock_metrics_cls:
                        mock_metrics_cls.return_value = AsyncMock()
                        await check_rain_and_alert()
                        # Should pass mock_state="rain" to predict_rain
                        mock_svc.predict_rain.assert_called_with(10.0, 20.0, mock_state="rain", location_name=None)
                        mock_send.assert_called()
