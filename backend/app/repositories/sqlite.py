from typing import Optional, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import UserLocation
from app.repositories.base import LocationRepository

class SQLiteLocationRepository(LocationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_location(self, chat_id: int, name: str = "default") -> Optional[UserLocation]:
        from sqlalchemy import or_
        conditions = [UserLocation.chat_id == chat_id]
        if name == "default":
            conditions.append(or_(UserLocation.name == name, UserLocation.name.is_(None)))
        else:
            conditions.append(UserLocation.name == name)
            
        result = await self.session.execute(
            select(UserLocation).where(*conditions)
        )
        return result.scalars().first()

    async def get_user_locations(self, chat_id: int) -> List[UserLocation]:
        result = await self.session.execute(
            select(UserLocation).where(UserLocation.chat_id == chat_id)
        )
        return list(result.scalars().all())

    async def save_location(self, chat_id: int, lat: float, lng: float, retention_type: str, name: str = "default") -> UserLocation:
        loc = await self.get_location(chat_id, name)
        
        expires_at = None
        if retention_type == "TWO_MONTHS":
            expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=60)
            
        if loc:
            loc.latitude = lat
            loc.longitude = lng
            loc.retention_type = retention_type
            loc.expires_at = expires_at
        else:
            loc = UserLocation(
                chat_id=chat_id,
                name=name,
                latitude=lat,
                longitude=lng,
                retention_type=retention_type,
                expires_at=expires_at
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

    async def delete_location(self, chat_id: int, name: str = "default") -> bool:
        loc = await self.get_location(chat_id, name)
        if loc:
            await self.session.delete(loc)
            await self.session.commit()
            return True
        return False

    async def get_mock_state(self, chat_id: int) -> Optional[str]:
        from app.models import DeveloperMock
        result = await self.session.execute(
            select(DeveloperMock).where(DeveloperMock.chat_id == chat_id)
        )
        mock = result.scalars().first()
        return mock.state if mock else None

    async def set_mock_state(self, chat_id: int, state: Optional[str]) -> None:
        from app.models import DeveloperMock
        result = await self.session.execute(
            select(DeveloperMock).where(DeveloperMock.chat_id == chat_id)
        )
        mock = result.scalars().first()
        
        if state is None:
            if mock:
                await self.session.delete(mock)
        else:
            if mock:
                mock.state = state
            else:
                mock = DeveloperMock(chat_id=chat_id, state=state)
                self.session.add(mock)
                
        await self.session.commit()

    async def save_feedback(
        self,
        chat_id: int,
        lat: float,
        lng: float,
        feedback_type: str,
        prediction_context: Optional[str] = None
    ):
        from app.models import UserFeedback, ApiReliability
        feedback = UserFeedback(
            chat_id=chat_id,
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

    async def has_disaster_alert_been_sent(self, chat_id: int, event_id: str) -> bool:
        from app.models import DisasterAlertHistory
        result = await self.session.execute(
            select(DisasterAlertHistory).where(
                (DisasterAlertHistory.chat_id == chat_id) & 
                (DisasterAlertHistory.event_id == event_id)
            )
        )
        return result.scalars().first() is not None

    async def mark_disaster_alert_sent(self, chat_id: int, event_id: str, event_type: str) -> None:
        from app.models import DisasterAlertHistory
        history = DisasterAlertHistory(
            chat_id=chat_id,
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
            return {
                "station_code": cache.station_code,
                "static_url": cache.static_url,
                "loop_url": cache.loop_url,
                "timestamp": cache.timestamp,
                "created_at": cache.created_at
            }
        return None

    async def set_latest_radar_cache(self, station_code: str, url_t: str, url_t_minus_1: Optional[str], timestamp: int) -> None:
        from app.models import RadarLatestCache
        result = await self.session.execute(select(RadarLatestCache).where(RadarLatestCache.station_code == station_code))
        cache = result.scalars().first()
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        if cache:
            cache.static_url = url_t
            cache.loop_url = url_t_minus_1
            cache.timestamp = timestamp
            cache.created_at = now
        else:
            cache = RadarLatestCache(
                station_code=station_code,
                static_url=static_url,
                loop_url=loop_url,
                timestamp=timestamp,
                created_at=now
            )
            self.session.add(cache)
            
        await self.session.commit()

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
