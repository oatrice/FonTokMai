import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone

# We must mock firebase_admin and firestore_async before importing FirestoreLocationRepository
# because it initializes in __init__. We can patch it at the module level.
with patch("app.repositories.firestore.firebase_admin"):
    with patch("app.repositories.firestore.credentials"):
        with patch("app.repositories.firestore.firestore_async") as mock_fs:
            from app.repositories.firestore import FirestoreLocationRepository
            from app.models import UserLocation

@pytest_asyncio.fixture(scope="function")
async def firestore_repo():
    with patch("app.repositories.firestore.firebase_admin") as mock_firebase:
        with patch("app.repositories.firestore.credentials") as mock_cred:
            with patch("app.repositories.firestore.firestore_async") as mock_fs:
                mock_db = MagicMock()
                mock_collection = MagicMock()
                mock_db.collection.return_value = mock_collection
                mock_fs.client.return_value = mock_db
                
                repo = FirestoreLocationRepository()
                repo.mock_db = mock_db
                repo.mock_collection = mock_collection
                yield repo

@pytest.mark.asyncio
async def test_get_location_found(firestore_repo):
    chat_id = 12345
    mock_doc_ref = MagicMock()
    firestore_repo.mock_collection.document.return_value = mock_doc_ref
    
    mock_doc = MagicMock()
    mock_doc.exists = True
    
    # Store datetime natively in mock
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    mock_doc.to_dict.return_value = {
        "chat_id": chat_id,
        "name": "Home",
        "latitude": 10.0,
        "longitude": 20.0,
        "retention_type": "TWO_MONTHS",
        "expires_at": now
    }
    
    mock_doc_ref.get = AsyncMock(return_value=mock_doc)
    
    loc = await firestore_repo.get_location(chat_id, "Home")
    assert loc is not None
    assert str(loc.chat_id) == str(chat_id)
    assert loc.name == "Home"
    assert loc.latitude == 10.0
    assert loc.expires_at == now

@pytest.mark.asyncio
async def test_get_location_not_found(firestore_repo):
    chat_id = 12345
    mock_doc_ref = MagicMock()
    firestore_repo.mock_collection.document.return_value = mock_doc_ref
    
    mock_doc = MagicMock()
    mock_doc.exists = False
    mock_doc_ref.get = AsyncMock(return_value=mock_doc)
    
    loc = await firestore_repo.get_location(chat_id, "Home")
    assert loc is None

@pytest.mark.asyncio
async def test_save_location_two_months(firestore_repo):
    chat_id = 9999
    lat = 13.75
    lng = 100.5
    
    mock_doc_ref = MagicMock()
    firestore_repo.mock_collection.document.return_value = mock_doc_ref
    mock_doc_ref.set = AsyncMock()
    
    loc = await firestore_repo.save_location(chat_id, lat, lng, "TWO_MONTHS", "Work")
    
    assert str(loc.chat_id) == str(chat_id)
    assert loc.name == "Work"
    assert loc.latitude == lat
    assert loc.retention_type == "TWO_MONTHS"
    assert loc.expires_at is not None
    
    diff = loc.expires_at - datetime.now(timezone.utc).replace(tzinfo=None)
    assert 59 <= diff.days <= 60
    
    # Verify set was called
    mock_doc_ref.set.assert_called_once()
    set_args = mock_doc_ref.set.call_args[0][0]
    assert str(set_args["chat_id"]) == str(chat_id)
    assert set_args["retention_type"] == "TWO_MONTHS"
    assert "expires_at" in set_args

@pytest.mark.asyncio
async def test_save_location_forever(firestore_repo):
    chat_id = 8888
    
    mock_doc_ref = MagicMock()
    firestore_repo.mock_collection.document.return_value = mock_doc_ref
    mock_doc_ref.set = AsyncMock()
    
    loc = await firestore_repo.save_location(chat_id, 10.0, 20.0, "FOREVER", "Home")
    
    assert loc.expires_at is None
    
    mock_doc_ref.set.assert_called_once()
    set_args = mock_doc_ref.set.call_args[0][0]
    assert set_args["expires_at"] is None

@pytest.mark.asyncio
async def test_get_active_locations(firestore_repo):
    mock_query = MagicMock()
    firestore_repo.mock_collection.where.return_value = mock_query
    
    # We will query all documents or query active ones
    # Firestore doesn't easily do OR queries for expires_at == null OR expires_at > now
    # So we might query all and filter in Python, or use a specific index/query strategy.
    # We will test the repository's logic.
    mock_doc1 = MagicMock()
    mock_doc1.to_dict.return_value = {"chat_id": "1", "latitude": 10.0, "longitude": 20.0, "retention_type": "FOREVER", "expires_at": None}
    
    mock_doc2 = MagicMock()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    future = now + timedelta(days=10)
    mock_doc2.to_dict.return_value = {"chat_id": "2", "latitude": 10.0, "longitude": 20.0, "retention_type": "TWO_MONTHS", "expires_at": future}
    
    mock_doc3 = MagicMock() # Expired
    past = now - timedelta(days=10)
    mock_doc3.to_dict.return_value = {"chat_id": "3", "latitude": 10.0, "longitude": 20.0, "retention_type": "TWO_MONTHS", "expires_at": past}
    
    # Mock stream to return docs
    async def mock_stream():
        for doc in [mock_doc1, mock_doc2, mock_doc3]:
            yield doc
    
    firestore_repo.mock_collection.stream = mock_stream
    
    locs = await firestore_repo.get_active_locations()
    assert len(locs) == 2
    chat_ids = [l.chat_id for l in locs]
    assert "1" in chat_ids
    assert "2" in chat_ids
    assert "3" not in chat_ids

@pytest.mark.asyncio
async def test_update_last_alerted(firestore_repo):
    chat_id = 1111
    loc = UserLocation(chat_id=chat_id, latitude=10.0, longitude=20.0, retention_type="FOREVER")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    mock_doc_ref = MagicMock()
    firestore_repo.mock_collection.document.return_value = mock_doc_ref
    mock_doc_ref.update = AsyncMock()
    
    updated_loc = await firestore_repo.update_last_alerted(loc, now)
    assert updated_loc.last_alerted_at == now
    
    mock_doc_ref.update.assert_called_once_with({"last_alerted_at": now})

@pytest.mark.asyncio
async def test_delete_location(firestore_repo):
    chat_id = 2222
    mock_doc_ref = MagicMock()
    firestore_repo.mock_collection.document.return_value = mock_doc_ref
    
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc_ref.get = AsyncMock(return_value=mock_doc)
    mock_doc_ref.delete = AsyncMock()
    
    res = await firestore_repo.delete_location(chat_id, "Home")
    assert res is True
    mock_doc_ref.delete.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_locations(firestore_repo):
    chat_id = 5555
    mock_query = MagicMock()
    firestore_repo.mock_collection.where.return_value = mock_query
    
    mock_doc1 = MagicMock()
    mock_doc1.to_dict.return_value = {"chat_id": chat_id, "name": "Home", "latitude": 10.0, "longitude": 20.0}
    
    mock_doc2 = MagicMock()
    mock_doc2.to_dict.return_value = {"chat_id": chat_id, "name": "Work", "latitude": 30.0, "longitude": 40.0}
    
    async def mock_stream():
        yield mock_doc1
        yield mock_doc2
        
    mock_query.stream = mock_stream
    
    locs = await firestore_repo.get_user_locations(chat_id)
    assert len(locs) == 2
    assert locs[0].name == "Home"
    assert locs[1].name == "Work"
    firestore_repo.mock_collection.where.assert_called_once_with("chat_id", "==", str(chat_id))

@pytest.mark.asyncio
async def test_save_feedback_firestore(firestore_repo):
    chat_id = 7777
    lat = 13.0
    lng = 100.0
    
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "feed_1"
    firestore_repo.db.collection.return_value.document.return_value = mock_doc_ref
    
    mock_rel_doc = MagicMock()
    mock_rel_doc.exists = True
    mock_rel_doc.to_dict.return_value = {"total_queries": 2, "false_alarms": 0, "accuracy_score": 1.0}
    mock_doc_ref.get = AsyncMock(return_value=mock_rel_doc)
    mock_doc_ref.set = AsyncMock()
    mock_doc_ref.update = AsyncMock()
    
    # We need to correctly route db.collection("api_reliability").document("tomorrow").get()
    async def mock_get():
        return mock_rel_doc
    mock_doc_ref.get = mock_get
    
    res = await firestore_repo.save_feedback(chat_id, lat, lng, "false_alarm", "Source: Tomorrow.io, max_rain: 1.5")
    assert res["id"] == "feed_1"
    assert res["feedback_type"] == "false_alarm"
    
    mock_doc_ref.update.assert_called_once()
    update_args = mock_doc_ref.update.call_args[0][0]
    assert update_args["false_alarms"] == 1
    assert update_args["accuracy_score"] == 0.5  # 1 - (1/2)

@pytest.mark.asyncio
async def test_record_api_query_success_firestore(firestore_repo):
    mock_doc_ref = MagicMock()
    firestore_repo.db.collection.return_value.document.return_value = mock_doc_ref
    
    mock_rel_doc = MagicMock()
    mock_rel_doc.exists = False
    
    async def mock_get():
        return mock_rel_doc
    mock_doc_ref.get = mock_get
    mock_doc_ref.set = AsyncMock()
    
    await firestore_repo.record_api_query_success("open-meteo")
    
    mock_doc_ref.set.assert_called_once()
    set_args = mock_doc_ref.set.call_args[0][0]
    assert set_args["total_queries"] == 1
    assert set_args["false_alarms"] == 0
    assert set_args["accuracy_score"] == 0.8  # Default for open-meteo

@pytest.mark.asyncio
async def test_check_and_increment_vision_quota_allowed(firestore_repo):
    mock_doc_ref = MagicMock()
    firestore_repo.db.collection.return_value.document.return_value = mock_doc_ref
    
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"count": 999}
    
    async def mock_get(): return mock_doc
    mock_doc_ref.get = mock_get
    mock_doc_ref.update = AsyncMock()
    
    result = await firestore_repo.check_and_increment_vision_quota(1000)
    assert result is True
    mock_doc_ref.update.assert_called_once()

@pytest.mark.asyncio
async def test_check_and_increment_vision_quota_exceeded(firestore_repo):
    mock_doc_ref = MagicMock()
    firestore_repo.db.collection.return_value.document.return_value = mock_doc_ref
    
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"count": 1000}
    
    async def mock_get(): return mock_doc
    mock_doc_ref.get = mock_get
    mock_doc_ref.update = AsyncMock()
    
    result = await firestore_repo.check_and_increment_vision_quota(1000)
    assert result is False
    mock_doc_ref.update.assert_not_called()
