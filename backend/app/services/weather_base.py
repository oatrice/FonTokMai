from abc import ABC, abstractmethod
from datetime import datetime, timezone

class BaseWeatherService(ABC):
    @abstractmethod
    async def get_current_radar_metadata(self) -> dict:
        """Fetch the latest radar metadata."""
        pass

    @abstractmethod
    async def predict_rain_by_location(self, lat: float, lng: float) -> dict:
        """Predict rain at a specific location."""
        pass

    def check_data_delay(self, data_timestamp: int, max_delay_minutes: int = 30) -> bool:
        """
        Check if the data is delayed beyond the maximum allowed delay.
        Returns True if delayed (outdated), False otherwise.
        """
        current_time = int(datetime.now(timezone.utc).timestamp())
        delta_seconds = current_time - data_timestamp
        return delta_seconds > (max_delay_minutes * 60)

    @staticmethod
    def degrees_to_cardinal(d):
        """Convert wind direction in degrees to cardinal text (N, NE, E, etc.)."""
        if d is None:
            return "ไม่ทราบ"
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        ix = int((d + 11.25)/22.5)
        return dirs[ix % 16]
