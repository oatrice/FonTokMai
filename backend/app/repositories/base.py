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
    async def update_last_alerted(
        self,
        location: UserLocation,
        alerted_time: Optional[datetime],
        max_rain: Optional[float] = None,
    ) -> UserLocation:
        """อัปเดตเวลาแจ้งเตือนล่าสุด และความรุนแรงของฝนที่แจ้งไป (mm/hr)"""
        pass

    @abstractmethod
    async def delete_location(self, chat_id: int, name: str = "default") -> bool:
        pass

    @abstractmethod
    async def get_mock_state(self, chat_id: int) -> Optional[str]:
        """Get the developer mock state for a chat_id. Returns 'rain', 'clear', or None."""
        pass

    @abstractmethod
    async def set_mock_state(self, chat_id: int, state: Optional[str]) -> None:
        """Set the developer mock state for a chat_id. Set to None to disable mock."""
        pass

    @abstractmethod
    async def save_feedback(
        self,
        chat_id: int,
        lat: float,
        lng: float,
        feedback_type: str,
        prediction_context: Optional[str] = None
    ):
        """Save user feedback (e.g. false_alarm) for ML improvements."""
        pass
