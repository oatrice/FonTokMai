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
