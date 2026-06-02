from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from app.models import UserLocation

class LocationRepository(ABC):
    @abstractmethod
    async def get_location(self, chat_id: int, name: str = "default") -> Optional[UserLocation]:
        pass

    @abstractmethod
    async def get_user_locations(self, chat_id: int) -> list[UserLocation]:
        pass

    @abstractmethod
    async def save_location(self, chat_id: int, lat: float, lng: float, retention_type: str, name: str = "default") -> UserLocation:
        pass

    @abstractmethod
    async def get_active_locations(self) -> list[UserLocation]:
        pass

    @abstractmethod
    async def update_last_alerted(self, location: UserLocation, alerted_time: datetime) -> UserLocation:
        pass

    @abstractmethod
    async def delete_location(self, chat_id: int, name: str = "default") -> bool:
        pass
