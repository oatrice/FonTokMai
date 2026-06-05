from typing import Optional, List
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore_async

from app.models import UserLocation
from app.repositories.base import LocationRepository

class FirestoreLocationRepository(LocationRepository):
    def __init__(self):
        if not firebase_admin._apps:
            # Requires GOOGLE_APPLICATION_CREDENTIALS in ENV or running on GCP
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
        self.db = firestore_async.client()
        self.collection = self.db.collection('user_locations')

    async def get_location(self, chat_id: int, name: str = "default") -> Optional[UserLocation]:
        doc_ref = self.collection.document(f"{chat_id}_{name}")
        doc = await doc_ref.get()
        if not doc.exists and name == "default":
            # Check legacy document ID format
            doc_ref = self.collection.document(str(chat_id))
            doc = await doc_ref.get()
            
        if doc.exists:
            data = doc.to_dict()
            return self._dict_to_model(data)
        return None

    async def get_user_locations(self, chat_id: int) -> List[UserLocation]:
        locations = []
        async for doc in self.collection.where("chat_id", "==", chat_id).stream():
            data = doc.to_dict()
            locations.append(self._dict_to_model(data))
        return locations

    async def save_location(self, chat_id: int, lat: float, lng: float, retention_type: str, name: str = "default") -> UserLocation:
        expires_at = None
        if retention_type == "TWO_MONTHS":
            # Just keep it as UTC timestamp or python datetime
            # We'll calculate it from current time + 60 days
            from datetime import timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(days=60)
            
        data = {
            "chat_id": chat_id,
            "name": name,
            "latitude": lat,
            "longitude": lng,
            "retention_type": retention_type,
            "expires_at": expires_at
        }
        
        doc_ref = self.collection.document(f"{chat_id}_{name}")
        await doc_ref.set(data)
        
        return self._dict_to_model(data)

    async def get_active_locations(self) -> List[UserLocation]:
        # Firestore cannot do an OR query efficiently for "expires_at == null OR expires_at > now".
        # We can fetch all and filter in python, or use a complex index.
        # Since the bot might not have millions of locations, fetching all and filtering in-memory is acceptable.
        locations = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        async for doc in self.collection.stream():
            data = doc.to_dict()
            loc = self._dict_to_model(data)
            if loc.expires_at is None or loc.expires_at > now:
                locations.append(loc)
                
        return locations

    async def update_last_alerted(
        self,
        location: UserLocation,
        alerted_time: Optional[datetime],
        max_rain: Optional[float] = None,
    ) -> UserLocation:
        alerted_time_native = alerted_time.replace(tzinfo=None) if alerted_time else None
        update_data: dict = {"last_alerted_at": alerted_time_native}
        if max_rain is not None:
            update_data["last_alert_max_rain"] = max_rain
        doc_ref = self.collection.document(f"{location.chat_id}_{location.name}")
        await doc_ref.update(update_data)
        location.last_alerted_at = alerted_time_native
        if max_rain is not None:
            location.last_alert_max_rain = max_rain
        return location


    async def delete_location(self, chat_id: int, name: str = "default") -> bool:
        doc_ref = self.collection.document(f"{chat_id}_{name}")
        doc = await doc_ref.get()
        if not doc.exists and name == "default":
            # Check legacy document ID format
            doc_ref = self.collection.document(str(chat_id))
            
        await doc_ref.delete()
        return True

    def _dict_to_model(self, data: dict) -> UserLocation:
        from datetime import timezone
        for field in ["expires_at", "last_alerted_at"]:
            val = data.get(field)
            if val and getattr(val, "tzinfo", None):
                data[field] = val.astimezone(timezone.utc).replace(tzinfo=None)
        return UserLocation(**data)

    async def get_mock_state(self, chat_id: int) -> Optional[str]:
        doc_ref = self.db.collection('dev_mocks').document(str(chat_id))
        doc = await doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return data.get("state")
        return None

    async def set_mock_state(self, chat_id: int, state: Optional[str]) -> None:
        doc_ref = self.db.collection('dev_mocks').document(str(chat_id))
        if state is None:
            await doc_ref.delete()
        else:
            await doc_ref.set({"state": state})

    async def save_feedback(
        self,
        chat_id: int,
        lat: float,
        lng: float,
        feedback_type: str,
        prediction_context: Optional[str] = None
    ):
        timestamp = datetime.now(timezone.utc)
        
        data = {
            "chat_id": chat_id,
            "latitude": lat,
            "longitude": lng,
            "timestamp": timestamp,
            "feedback_type": feedback_type,
            "prediction_context": prediction_context
        }
        
        # In Firestore, it's easier to just use an auto-generated ID for feedback
        doc_ref = self.db.collection('user_feedbacks').document()
        await doc_ref.set(data)
        
        # Don't construct SQLAlchemy model here, just return dict
        data["id"] = doc_ref.id
        return data

    async def has_disaster_alert_been_sent(self, chat_id: int, event_id: str) -> bool:
        doc_ref = self.db.collection('disaster_alerts_history').document(f"{chat_id}_{event_id}")
        doc = await doc_ref.get()
        return doc.exists

    async def mark_disaster_alert_sent(self, chat_id: int, event_id: str, event_type: str) -> None:
        doc_ref = self.db.collection('disaster_alerts_history').document(f"{chat_id}_{event_id}")
        await doc_ref.set({
            "chat_id": chat_id,
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc)
        })
