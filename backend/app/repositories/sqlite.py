from typing import Optional, List, Union
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import UserLocation
from app.repositories.base import LocationRepository

class SQLiteLocationRepository(LocationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_location(self, chat_id: Union[str, int], name: str = "default") -> Optional[UserLocation]:
        from sqlalchemy import or_, func
        chat_id_str = str(chat_id)
        name_lower = (name or "default").lower()
        conditions = [UserLocation.chat_id == chat_id_str]
        if name_lower == "default":
            conditions.append(or_(func.lower(UserLocation.name) == "default", UserLocation.name.is_(None)))
        else:
            conditions.append(func.lower(UserLocation.name) == name_lower)
            
        result = await self.session.execute(
            select(UserLocation).where(*conditions)
        )
        return result.scalars().first()

    async def get_user_locations(self, chat_id: Union[str, int]) -> List[UserLocation]:
        chat_id_str = str(chat_id)
        result = await self.session.execute(
            select(UserLocation).where(UserLocation.chat_id == chat_id_str)
        )
        return list(result.scalars().all())

    async def save_location(
        self,
        chat_id: Union[str, int],
        lat: float,
        lng: float,
        retention_type: str,
        name: str = "default",
        platform: str = "telegram"
    ) -> UserLocation:
        chat_id_str = str(chat_id)
        loc = await self.get_location(chat_id_str, name)
        
        expires_at = None
        if retention_type == "TWO_MONTHS":
            expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=60)
            
        if loc:
            loc.latitude = lat
            loc.longitude = lng
            loc.retention_type = retention_type
            loc.expires_at = expires_at
            loc.platform = platform
        else:
            loc = UserLocation(
                chat_id=chat_id_str,
                name=name,
                latitude=lat,
                longitude=lng,
                retention_type=retention_type,
                expires_at=expires_at,
                platform=platform
            )
            self.session.add(loc)
            
        await self.session.commit()
        await self.session.refresh(loc)
        return loc

    async def get_active_locations(self) -> List[UserLocation]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = await self.session.execute(
            select(UserLocation).where(
                (UserLocation.expires_at == None) | (UserLocation.expires_at > now)
            )
        )
        return list(result.scalars().all())

    async def update_last_alerted(
        self,
        location: UserLocation,
        alerted_time: Optional[datetime],
        max_rain: Optional[float] = None,
    ) -> UserLocation:
        location.last_alerted_at = alerted_time.replace(tzinfo=None) if alerted_time else None
        if max_rain is not None:
            location.last_alert_max_rain = max_rain
        await self.session.commit()
        return location

    async def delete_location(self, chat_id: Union[str, int], name: str = "default") -> bool:
        chat_id_str = str(chat_id)
        loc = await self.get_location(chat_id_str, name)
        if loc:
            await self.session.delete(loc)
            await self.session.commit()
            return True
        return False

    async def get_mock_state(self, chat_id: Union[str, int]) -> Optional[str]:
        from app.models import DeveloperMock
        chat_id_str = str(chat_id)
        result = await self.session.execute(
            select(DeveloperMock).where(DeveloperMock.chat_id == chat_id_str)
        )
        mock = result.scalars().first()
        return mock.state if mock else None

    async def set_mock_state(self, chat_id: Union[str, int], state: Optional[str]) -> None:
        from app.models import DeveloperMock
        chat_id_str = str(chat_id)
        result = await self.session.execute(
            select(DeveloperMock).where(DeveloperMock.chat_id == chat_id_str)
        )
        mock = result.scalars().first()
        
        if state is None:
            if mock:
                await self.session.delete(mock)
        else:
            if mock:
                mock.state = state
            else:
                mock = DeveloperMock(chat_id=chat_id_str, state=state)
                self.session.add(mock)
                
        await self.session.commit()

    async def get_global_dev_config(self) -> Optional[dict]:
        import json
        from app.models import SystemConfig
        result = await self.session.execute(
            select(SystemConfig).where(SystemConfig.key == "dev_config")
        )
        config_record = result.scalars().first()
        if config_record:
            try:
                return json.loads(config_record.value_json)
            except:
                pass
        return None

    async def set_global_dev_config(self, config: dict) -> None:
        import json
        from app.models import SystemConfig
        result = await self.session.execute(
            select(SystemConfig).where(SystemConfig.key == "dev_config")
        )
        config_record = result.scalars().first()
        value = json.dumps(config)
        if config_record:
            config_record.value_json = value
        else:
            config_record = SystemConfig(key="dev_config", value_json=value)
            self.session.add(config_record)
        await self.session.commit()

    async def save_feedback(
        self,
        chat_id: Union[str, int],
        lat: float,
        lng: float,
        feedback_type: str,
        prediction_context: Optional[str] = None
    ):
        from app.models import UserFeedback, ApiReliability
        chat_id_str = str(chat_id)
        feedback = UserFeedback(
            chat_id=chat_id_str,
            latitude=lat,
            longitude=lng,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            feedback_type=feedback_type,
            prediction_context=prediction_context
        )
        self.session.add(feedback)
        
        if feedback_type == "false_alarm" and prediction_context:
            endpoint = None
            if "Source: Tomorrow.io" in prediction_context: endpoint = "tomorrow"
            elif "Source: Rainbow Local" in prediction_context: endpoint = "rainbow-local"
            elif "Source: Rainbow Global" in prediction_context: endpoint = "rainbow-global"
            elif "Source: Xweather" in prediction_context: endpoint = "xweather"
            elif "Source: Open-Meteo" in prediction_context: endpoint = "open-meteo"
            
            if endpoint:
                result = await self.session.execute(select(ApiReliability).where(ApiReliability.endpoint == endpoint))
                rel = result.scalars().first()
                if not rel:
                    defaults = {"tmd-radar": 1.1, "xweather": 1.0, "tomorrow": 0.95, "rainbow-local": 0.9, "rainbow-global": 0.85, "open-meteo": 0.8}
                    rel = ApiReliability(
                        endpoint=endpoint, 
                        total_queries=0, 
                        false_alarms=0, 
                        accuracy_score=defaults.get(endpoint, 1.0)
                    )
                    self.session.add(rel)
                    
                rel.false_alarms += 1
                if rel.total_queries > 0:
                    rel.accuracy_score = 1.0 - (rel.false_alarms / rel.total_queries)
                    if rel.accuracy_score < 0:
                        rel.accuracy_score = 0.0

        await self.session.commit()
        await self.session.refresh(feedback)
        return feedback

    async def has_disaster_alert_been_sent(self, chat_id: Union[str, int], event_id: str) -> bool:
        from app.models import DisasterAlertHistory
        chat_id_str = str(chat_id)
        result = await self.session.execute(
            select(DisasterAlertHistory).where(
                (DisasterAlertHistory.chat_id == chat_id_str) & 
                (DisasterAlertHistory.event_id == event_id)
            )
        )
        return result.scalars().first() is not None

    async def mark_disaster_alert_sent(self, chat_id: Union[str, int], event_id: str, event_type: str) -> None:
        from app.models import DisasterAlertHistory
        chat_id_str = str(chat_id)
        history = DisasterAlertHistory(
            chat_id=chat_id_str,
            event_id=event_id,
            event_type=event_type,
            alerted_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        self.session.add(history)
        await self.session.commit()

    async def get_all_api_reliability(self) -> dict[str, float]:
        from app.models import ApiReliability
        result = await self.session.execute(select(ApiReliability))
        reliabilities = result.scalars().all()
        
        scores = {}
        for r in reliabilities:
            scores[r.endpoint] = r.accuracy_score
            
        defaults = {
            "tmd-radar": 1.1,
            "xweather": 1.0,
            "tomorrow": 0.95,
            "rainbow-local": 0.9,
            "rainbow-global": 0.85,
            "open-meteo": 0.8
        }
        for ep, default_score in defaults.items():
            if ep not in scores:
                scores[ep] = default_score
                
        return scores

    async def record_api_query_success(self, endpoint: str) -> None:
        from app.models import ApiReliability
        result = await self.session.execute(select(ApiReliability).where(ApiReliability.endpoint == endpoint))
        rel = result.scalars().first()
        
        if not rel:
            defaults = {"tmd-radar": 1.1, "xweather": 1.0, "tomorrow": 0.95, "rainbow-local": 0.9, "rainbow-global": 0.85, "open-meteo": 0.8}
            rel = ApiReliability(
                endpoint=endpoint, 
                total_queries=0, 
                false_alarms=0, 
                accuracy_score=defaults.get(endpoint, 1.0)
            )
            self.session.add(rel)
            
        rel.total_queries += 1
        if rel.total_queries > 0:
            rel.accuracy_score = 1.0 - (rel.false_alarms / rel.total_queries)
            if rel.accuracy_score < 0:
                rel.accuracy_score = 0.0
                
        await self.session.commit()

    async def get_latest_radar_cache(self, station_code: str) -> Optional[dict]:
        from app.models import RadarLatestCache
        result = await self.session.execute(select(RadarLatestCache).where(RadarLatestCache.station_code == station_code))
        cache = result.scalars().first()
        if cache:
            import json
            return {
                "station_code": cache.station_code,
                "frames": json.loads(cache.frames_json) if cache.frames_json else [],
                "created_at": cache.created_at,
                "last_gif_fallback_time": cache.last_gif_fallback_time
            }
        return None

    async def set_latest_radar_cache(self, station_code: str, frames: list, last_gif_fallback_time: float = 0.0) -> None:
        from app.models import RadarLatestCache
        import json
        result = await self.session.execute(select(RadarLatestCache).where(RadarLatestCache.station_code == station_code))
        cache = result.scalars().first()
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        if cache:
            cache.frames_json = json.dumps(frames)
            cache.created_at = now
            cache.last_gif_fallback_time = last_gif_fallback_time
        else:
            new_cache = RadarLatestCache(
                station_code=station_code,
                frames_json=json.dumps(frames),
                created_at=now,
                last_gif_fallback_time=last_gif_fallback_time
            )
            self.session.add(new_cache)
            
        await self.session.commit()

    async def get_system_settings(self) -> dict:
        # SQLite implementation for local dev can just return defaults
        # or implement a simple JSON file read if needed. 
        # For simplicity, default to True for local testing.
        return getattr(self, "_mock_system_settings", {"enable_gif_fallback": True})

    async def set_system_settings(self, settings: dict):
        self._mock_system_settings = settings

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
        import json
        from app.models import CronRunLog
        
        log_entry = CronRunLog(
            routine_name=routine_name,
            run_at=run_at.replace(tzinfo=None) if run_at else datetime.now(timezone.utc).replace(tzinfo=None),
            duration_s=duration_s,
            alerts_sent=alerts_sent,
            locations_checked=locations_checked,
            errors=errors,
            extra_data=json.dumps(extra_data) if extra_data else None
        )
        self.session.add(log_entry)
        await self.session.commit()

    async def get_cron_metrics(
        self,
        days: int = 7,
        routine_name: Optional[str] = None,
    ) -> list[dict]:
        from app.models import CronRunLog
        import json
        
        cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        
        conditions = [CronRunLog.run_at >= cutoff_date]
        if routine_name:
            conditions.append(CronRunLog.routine_name == routine_name)
            
        result = await self.session.execute(
            select(CronRunLog).where(*conditions).order_by(CronRunLog.run_at.desc())
        )
        logs = result.scalars().all()
        
        metrics = []
        for log in logs:
            extra = None
            if log.extra_data:
                try:
                    extra = json.loads(log.extra_data)
                except Exception:
                    pass
                    
            metrics.append({
                "routine_name": log.routine_name,
                "run_at": log.run_at.replace(tzinfo=timezone.utc),
                "duration_s": log.duration_s,
                "alerts_sent": log.alerts_sent,
                "locations_checked": log.locations_checked,
                "errors": log.errors,
                "extra_data": extra
            })
            
        return metrics

    async def save_admin_bypass(self, chat_id: Union[str, int], expires_in_minutes: int = 60) -> None:
        from app.models import AdminBypass
        chat_id_str = str(chat_id)
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=expires_in_minutes)
        result = await self.session.execute(
            select(AdminBypass).where(AdminBypass.chat_id == chat_id_str)
        )
        record = result.scalars().first()
        if record:
            record.expires_at = expires_at
        else:
            record = AdminBypass(chat_id=chat_id_str, expires_at=expires_at)
            self.session.add(record)
        await self.session.commit()

    async def delete_admin_bypass(self, chat_id: Union[str, int]) -> None:
        from app.models import AdminBypass
        chat_id_str = str(chat_id)
        result = await self.session.execute(
            select(AdminBypass).where(AdminBypass.chat_id == chat_id_str)
        )
        record = result.scalars().first()
        if record:
            await self.session.delete(record)
            await self.session.commit()

    async def has_active_admin_bypass(self, chat_id: Union[str, int]) -> bool:
        from app.models import AdminBypass
        chat_id_str = str(chat_id)
        result = await self.session.execute(
            select(AdminBypass).where(AdminBypass.chat_id == chat_id_str)
        )
        record = result.scalars().first()
        if not record:
            return False
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if record.expires_at > now:
            return True
        return False

    async def update_tracking_mode(
        self,
        chat_id: Union[str, int],
        tracking_mode: str,
        locked_target_id: Optional[str] = None,
        locked_target_cx: Optional[int] = None,
        locked_target_cy: Optional[int] = None,
        name: str = "default"
    ) -> None:
        chat_id_str = str(chat_id)
        loc = await self.get_location(chat_id_str, name)
        if not loc and name != "default":
            loc = await self.get_location(chat_id_str, "default")
        if loc:
            loc.tracking_mode = tracking_mode
            loc.locked_target_id = locked_target_id
            loc.locked_target_cx = locked_target_cx
            loc.locked_target_cy = locked_target_cy
            await self.session.commit()
