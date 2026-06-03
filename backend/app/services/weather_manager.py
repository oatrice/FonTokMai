import logging
from typing import Optional
from .tomorrow import TomorrowService
from .rainbow import RainbowService

logger = logging.getLogger(__name__)

class WeatherManager:
    def __init__(self):
        self.tomorrow_svc = TomorrowService()
        self.rainbow_svc = RainbowService()

    async def predict_rain(self, lat: float, lng: float, mock_state: Optional[str] = None) -> dict:
        """
        Tries Tomorrow.io first. If it fails, falls back to Rainbow Local, then Rainbow Global.
        """
        # 1. Primary: Tomorrow.io
        try:
            result = await self.tomorrow_svc.predict_rain_by_location(lat, lng, mock_state=mock_state)
            logger.info("Successfully fetched weather from Tomorrow.io")
            return result
        except Exception as e:
            logger.warning(f"Tomorrow.io failed: {e}. Falling back to Rainbow (Local).")

        # 2. Secondary: Rainbow Local
        try:
            result = await self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="local", mock_state=mock_state)
            logger.info("Successfully fetched weather from Rainbow (Local)")
            result["endpoint"] = "rainbow-local"
            return result
        except Exception as e:
            logger.warning(f"Rainbow Local failed: {e}. Falling back to Rainbow (Global).")

        # 3. Fallback: Rainbow Global
        try:
            result = await self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="global", mock_state=mock_state)
            logger.info("Successfully fetched weather from Rainbow (Global)")
            result["endpoint"] = "rainbow-global"
            return result
        except Exception as e:
            logger.error(f"All weather APIs failed. Last error: {e}")
            return {
                "predictions": [],
                "intensity": "ไม่ทราบ",
                "max_rain": 0.0,
                "duration_minutes": 0,
                "wind_speed_kmh": 0.0,
                "endpoint": "error"
            }
