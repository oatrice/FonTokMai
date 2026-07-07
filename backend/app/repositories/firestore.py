from typing import Optional, List, Union
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

    async def get_location(self, chat_id: Union[str, int], name: str = "default") -> Optional[UserLocation]:
        chat_id_str = str(chat_id)
        doc_ref = self.collection.document(f"{chat_id_str}_{name}")
        doc = await doc_ref.get()
        if not doc.exists and name == "default":
            # Check legacy document ID format
            doc_ref = self.collection.document(chat_id_str)
            doc = await doc_ref.get()
            
        if doc.exists:
            data = doc.to_dict()
            return self._dict_to_model(data)
        return None

    async def get_user_locations(self, chat_id: Union[str, int]) -> List[UserLocation]:
        chat_id_str = str(chat_id)
        locations = []
        async for doc in self.collection.where("chat_id", "==", chat_id_str).stream():
            data = doc.to_dict()
            locations.append(self._dict_to_model(data))
            
        if not locations:
            try:
                chat_id_int = int(chat_id)
                async for doc in self.collection.where("chat_id", "==", chat_id_int).stream():
                    data = doc.to_dict()
                    locations.append(self._dict_to_model(data))
            except ValueError:
                pass
                
        return locations

    async def save_location(
        self,
        chat_id: Union[str, int],
        lat: float,
        lng: float,
        retention_type: str,
        name: str = "default",
        platform: str = "telegram"
    ) -> UserLocation:
        expires_at = None
        if retention_type == "TWO_MONTHS":
            # Just keep it as UTC timestamp or python datetime
            # We'll calculate it from current time + 60 days
            from datetime import timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(days=60)
            
        chat_id_str = str(chat_id)
        data = {
            "chat_id": chat_id_str,
            "name": name,
            "latitude": lat,
            "longitude": lng,
            "retention_type": retention_type,
            "expires_at": expires_at,
            "platform": platform
        }
        
        doc_ref = self.collection.document(f"{chat_id_str}_{name}")
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


    async def delete_location(self, chat_id: Union[str, int], name: str = "default") -> bool:
        chat_id_str = str(chat_id)
        doc_ref = self.collection.document(f"{chat_id_str}_{name}")
        doc = await doc_ref.get()
        if not doc.exists and name == "default":
            # Check legacy document ID format
            doc_ref = self.collection.document(chat_id_str)
            
        await doc_ref.delete()
        return True

    def _dict_to_model(self, data: dict) -> UserLocation:
        from datetime import timezone
        for field in ["expires_at", "last_alerted_at"]:
            val = data.get(field)
            if val and getattr(val, "tzinfo", None):
                data[field] = val.astimezone(timezone.utc).replace(tzinfo=None)
        return UserLocation(**data)

    async def get_mock_state(self, chat_id: Union[str, int]) -> Optional[str]:
        chat_id_str = str(chat_id)
        doc_ref = self.db.collection('dev_mocks').document(chat_id_str)
        doc = await doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return data.get("state")
        return None

    async def set_mock_state(self, chat_id: Union[str, int], state: Optional[str]) -> None:
        chat_id_str = str(chat_id)
        doc_ref = self.db.collection('dev_mocks').document(chat_id_str)
        if state is None:
            await doc_ref.delete()
        else:
            await doc_ref.set({"state": state})

    async def get_global_dev_config(self) -> Optional[dict]:
        doc_ref = self.db.collection('system_config').document('dev_config')
        doc = await doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None

    async def set_global_dev_config(self, config: dict) -> None:
        doc_ref = self.db.collection('system_config').document('dev_config')
        await doc_ref.set(config)

    async def save_feedback(
        self,
        chat_id: Union[str, int],
        lat: float,
        lng: float,
        feedback_type: str,
        prediction_context: Optional[str] = None
    ):
        timestamp = datetime.now(timezone.utc)
        chat_id_str = str(chat_id)
        
        data = {
            "chat_id": chat_id_str,
            "latitude": lat,
            "longitude": lng,
            "timestamp": timestamp,
            "feedback_type": feedback_type,
            "prediction_context": prediction_context
        }
        
        # In Firestore, it's easier to just use an auto-generated ID for feedback
        doc_ref = self.db.collection('user_feedbacks').document()
        await doc_ref.set(data)
        
        if feedback_type == "false_alarm" and prediction_context:
            endpoint = None
            if "Source: Tomorrow.io" in prediction_context: endpoint = "tomorrow"
            elif "Source: Rainbow Local" in prediction_context: endpoint = "rainbow-local"
            elif "Source: Rainbow Global" in prediction_context: endpoint = "rainbow-global"
            elif "Source: Xweather" in prediction_context: endpoint = "xweather"
            elif "Source: Open-Meteo" in prediction_context: endpoint = "open-meteo"
            
            if endpoint:
                rel_ref = self.db.collection('api_reliability').document(endpoint)
                rel_doc = await rel_ref.get()
                if not rel_doc.exists:
                    defaults = {"tmd-radar": 1.1, "xweather": 1.0, "tomorrow": 0.95, "rainbow-local": 0.9, "rainbow-global": 0.85, "open-meteo": 0.8}
                    rel_data = {
                        "total_queries": 0,
                        "false_alarms": 1,
                        "accuracy_score": 0.0
                    }
                    await rel_ref.set(rel_data)
                else:
                    rel_data = rel_doc.to_dict()
                    total = rel_data.get("total_queries", 0)
                    alarms = rel_data.get("false_alarms", 0) + 1
                    acc = 1.0 - (alarms / total) if total > 0 else 0.0
                    if acc < 0: acc = 0.0
                    await rel_ref.update({
                        "false_alarms": alarms,
                        "accuracy_score": acc
                    })
        
        # Don't construct SQLAlchemy model here, just return dict
        data["id"] = doc_ref.id
        return data

    async def has_disaster_alert_been_sent(self, chat_id: Union[str, int], event_id: str) -> bool:
        chat_id_str = str(chat_id)
        doc_ref = self.db.collection('disaster_alerts_history').document(f"{chat_id_str}_{event_id}")
        doc = await doc_ref.get()
        return doc.exists

    async def mark_disaster_alert_sent(self, chat_id: Union[str, int], event_id: str, event_type: str) -> None:
        chat_id_str = str(chat_id)
        doc_ref = self.db.collection('disaster_alerts_history').document(f"{chat_id_str}_{event_id}")
        await doc_ref.set({
            "chat_id": chat_id_str,
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc)
        })

    async def get_all_api_reliability(self) -> dict[str, float]:
        reliabilities = {}
        async for doc in self.db.collection('api_reliability').stream():
            data = doc.to_dict()
            reliabilities[doc.id] = data.get("accuracy_score", 0.0)
            
        defaults = {
            "tmd-radar": 1.1,
            "xweather": 1.0,
            "tomorrow": 0.95,
            "rainbow-local": 0.9,
            "rainbow-global": 0.85,
            "open-meteo": 0.8
        }
        for ep, default_score in defaults.items():
            if ep not in reliabilities:
                reliabilities[ep] = default_score
                
        return reliabilities

    async def record_api_query_success(self, endpoint: str) -> None:
        doc_ref = self.db.collection('api_reliability').document(endpoint)
        doc = await doc_ref.get()
        
        if not doc.exists:
            defaults = {"tmd-radar": 1.1, "xweather": 1.0, "tomorrow": 0.95, "rainbow-local": 0.9, "rainbow-global": 0.85, "open-meteo": 0.8}
            data = {
                "total_queries": 1,
                "false_alarms": 0,
                "accuracy_score": defaults.get(endpoint, 1.0)
            }
            await doc_ref.set(data)
            return
            
        data = doc.to_dict()
        total = data.get("total_queries", 0) + 1
        alarms = data.get("false_alarms", 0)
        acc = 1.0 - (alarms / total)
        if acc < 0: acc = 0.0
        
        await doc_ref.update({
            "total_queries": total,
            "accuracy_score": acc
        })

    async def get_radar_timestamp_cache(self, frame_hash: str) -> Optional[int]:
        doc_ref = self.db.collection('radar_frame_cache').document(frame_hash)
        doc = await doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return data.get("timestamp")
        return None

    async def set_radar_timestamp_cache(self, frame_hash: str, timestamp: int) -> None:
        doc_ref = self.db.collection('radar_frame_cache').document(frame_hash)
        await doc_ref.set({
            "timestamp": timestamp,
            "created_at": datetime.now(timezone.utc)
        })

    async def check_and_increment_vision_quota(self, limit: int = 1000) -> bool:
        """Check if monthly Cloud Vision quota is exceeded. If not, increment and return True."""
        # Get current month in YYYY-MM format using Pacific Time (Google Cloud Billing cycle)
        from zoneinfo import ZoneInfo
        month_key = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m")
        doc_ref = self.db.collection('api_quotas').document(f'vision_{month_key}')
        
        doc = await doc_ref.get()
        if not doc.exists:
            # First request of the month
            await doc_ref.set({'count': 1})
            return True
            
        data = doc.to_dict()
        count = data.get('count', 0)
        
        if count >= limit:
            return False
            
        # Increment quota
        from google.cloud import firestore
        await doc_ref.update({'count': firestore.Increment(1)})
        return True

    async def get_latest_radar_cache(self, station_code: str) -> Optional[dict]:
        doc_ref = self.db.collection('radar_latest_cache').document(station_code)
        doc = await doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None

    async def set_latest_radar_cache(self, station_code: str, frames: list, last_gif_fallback_time: float = 0.0) -> None:
        from google.cloud import firestore
        doc_ref = self.db.collection('radar_latest_cache').document(station_code)
        data = {
            "frames": frames,
            "created_at": firestore.SERVER_TIMESTAMP,
            "last_gif_fallback_time": last_gif_fallback_time
        }
        await doc_ref.set(data, merge=True)

    async def get_system_settings(self) -> dict:
        doc_ref = self.db.collection('system_settings').document('tmd_radar')
        doc = await doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return {}

    async def set_system_settings(self, settings: dict):
        doc_ref = self.db.collection('system_settings').document('tmd_radar')
        await doc_ref.set(settings, merge=True)

    async def record_cron_run(
        self,
        routine_name: str,
        run_at,
        duration_s: float,
        alerts_sent: int = 0,
        locations_checked: int = 0,
        errors: int = 0,
        extra_data: Optional[dict] = None,
    ) -> None:
        doc_ref = self.db.collection('cron_metrics').document()
        await doc_ref.set({
            "routine_name": routine_name,
            "run_at": run_at if run_at else datetime.now(timezone.utc),
            "duration_s": duration_s,
            "alerts_sent": alerts_sent,
            "locations_checked": locations_checked,
            "errors": errors,
            "extra_data": extra_data
        })

    async def get_cron_metrics(
        self,
        days: int = 7,
        routine_name: Optional[str] = None,
    ) -> list[dict]:
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = self.db.collection('cron_metrics').where("run_at", ">=", cutoff_date)
        if routine_name:
            query = query.where("routine_name", "==", routine_name)
            
        # Note: Firestore might require an index for order_by with multiple fields/where clauses.
        # To avoid index errors during deployment, we'll sort in python since volume isn't huge.
        docs = []
        async for doc in query.stream():
            docs.append(doc.to_dict())
            
        docs.sort(key=lambda x: x.get("run_at", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        
        metrics = []
        for d in docs:
            run_dt = d.get("run_at")
            if run_dt and getattr(run_dt, "tzinfo", None) is None:
                run_dt = run_dt.replace(tzinfo=timezone.utc)
                
            metrics.append({
                "routine_name": d.get("routine_name"),
                "run_at": run_dt,
                "duration_s": d.get("duration_s", 0.0),
                "alerts_sent": d.get("alerts_sent", 0),
                "locations_checked": d.get("locations_checked", 0),
                "errors": d.get("errors", 0),
                "extra_data": d.get("extra_data")
            })
            
        return metrics

    async def save_admin_bypass(self, chat_id: Union[str, int], expires_in_minutes: int = 60) -> None:
        from datetime import timedelta
        chat_id_str = str(chat_id)
        doc_ref = self.db.collection('admin_bypass').document(chat_id_str)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
        await doc_ref.set({
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc)
        })

    async def delete_admin_bypass(self, chat_id: Union[str, int]) -> None:
        chat_id_str = str(chat_id)
        doc_ref = self.db.collection('admin_bypass').document(chat_id_str)
        await doc_ref.delete()

    async def has_active_admin_bypass(self, chat_id: Union[str, int]) -> bool:
        chat_id_str = str(chat_id)
        doc_ref = self.db.collection('admin_bypass').document(chat_id_str)
        doc = await doc_ref.get()
        if not doc.exists:
            return False
            
        data = doc.to_dict()
        expires_at = data.get("expires_at")
        
        if not expires_at:
            return False
            
        # Handle Firestore DatetimeWithNanoseconds
        if getattr(expires_at, "tzinfo", None) is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        return expires_at > datetime.now(timezone.utc)
