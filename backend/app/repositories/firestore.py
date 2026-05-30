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

    async def get_location(self, chat_id: int) -> Optional[UserLocation]:
        doc_ref = self.collection.document(str(chat_id))
        doc = await doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return self._dict_to_model(data)
        return None

    async def save_location(self, chat_id: int, lat: float, lng: float, retention_type: str) -> UserLocation:
        # Same expiry logic as sqlite, but stored in Firestore
        expires_at = None
        if retention_type == "TWO_MONTHS":
            # Just keep it as UTC timestamp or python datetime
            # We'll calculate it from current time + 60 days
            pass # TODO: expiry logic
            
        return UserLocation(chat_id=chat_id, latitude=lat, longitude=lng, retention_type=retention_type)

    async def get_active_locations(self) -> List[UserLocation]:
        return []

    async def update_last_alerted(self, location: UserLocation, alerted_time: datetime) -> UserLocation:
        return location

    async def delete_location(self, chat_id: int) -> bool:
        return True

    def _dict_to_model(self, data: dict) -> UserLocation:
        return UserLocation(**data)
