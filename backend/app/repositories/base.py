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

    @abstractmethod
    async def has_disaster_alert_been_sent(self, chat_id: int, event_id: str) -> bool:
        """Check if a disaster alert has already been processed and sent."""
        pass

    @abstractmethod
    async def mark_disaster_alert_sent(self, chat_id: int, event_id: str, event_type: str) -> None:
        """Mark a disaster alert as sent to prevent duplicate processing."""
        pass

    @abstractmethod
    async def get_all_api_reliability(self) -> dict[str, float]:
        """ดึงคะแนนความแม่นยำของทุก API คืนค่าเป็น dict {endpoint: accuracy_score}"""
        pass

    @abstractmethod
    async def record_api_query_success(self, endpoint: str) -> None:
        """เพิ่มจำนวน total_queries ให้กับ API ที่ทำผลงานทายว่าฝนตกสำเร็จ"""
        pass

    @abstractmethod
    async def get_latest_radar_cache(self, station_code: str) -> Optional[dict]:
        """ดึงข้อมูล Cache ล่าสุดของสถานีเรดาร์ (คืนค่าเป็น dict ที่มี frames (list of dict with url, timestamp), created_at)"""
        pass

    @abstractmethod
    async def set_latest_radar_cache(self, station_code: str, frames: list, last_gif_fallback_time: float = 0.0) -> None:
        """บันทึกข้อมูล Cache ล่าสุดของสถานีเรดาร์ลงฐานข้อมูลแบบ Array 4 เฟรม"""
        pass

    @abstractmethod
    async def get_system_settings(self) -> dict:
        """ดึงข้อมูล System Settings จากฐานข้อมูล"""
        pass

    @abstractmethod
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
        """บันทึก metrics ของ cron routine run หนึ่งครั้ง"""
        pass

    @abstractmethod
    async def get_cron_metrics(
        self,
        days: int = 7,
        routine_name: Optional[str] = None,
    ) -> list[dict]:
        """ดึงรายการ cron run logs ย้อนหลัง N วัน คืนค่าเป็น list of dict"""
        pass
