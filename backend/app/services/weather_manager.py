import logging
from typing import Optional
from .tomorrow import TomorrowService
from .rainbow import RainbowService

logger = logging.getLogger(__name__)

class WeatherManager:
    def __init__(self):
        self.tomorrow_svc = TomorrowService()
        self.rainbow_svc = RainbowService()

    async def predict_rain(
        self,
        lat: float,
        lng: float,
        mock_state: Optional[str] = None,
        force_endpoint: Optional[str] = None,
    ) -> dict:
        """
        ดึงข้อมูลพยากรณ์ฝนโดยผ่านระบบ Fallback อัตโนมัติ:
          Tomorrow.io → Rainbow Local → Rainbow Global

        พารามิเตอร์:
          force_endpoint: ถ้าระบุ ("global" หรือ "local") จะเรียก Rainbow endpoint นั้นโดยตรง
                          โดยไม่ผ่าน fallback chain (ใช้สำหรับ user สลับ endpoint เอง)
        """
        # --- โหมดบังคับ endpoint (ไม่ผ่าน fallback) ---
        if force_endpoint in ("global", "local"):
            try:
                result = await self.rainbow_svc.predict_rain_by_location(
                    lat, lng, endpoint_type=force_endpoint, mock_state=mock_state
                )
                endpoint_label = "rainbow-global" if force_endpoint == "global" else "rainbow-local"
                result["endpoint"] = endpoint_label
                logger.info(f"Successfully fetched weather from Rainbow ({force_endpoint}) [forced]")
                return result
            except Exception as e:
                logger.error(f"Rainbow ({force_endpoint}) failed (forced mode): {e}")
                return {
                    "predictions": [],
                    "intensity": "ไม่ทราบ",
                    "max_rain": 0.0,
                    "duration_minutes": 0,
                    "wind_speed_kmh": 0.0,
                    "endpoint": "error",
                }

        # --- โหมดปกติ: Tomorrow.io → Rainbow Local → Rainbow Global ---

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
                "endpoint": "error",
            }

    async def compare_all_apis(self, lat: float, lng: float, mock_state: Optional[str] = None) -> dict:
        """
        เรียก 3 API พร้อมกันเพื่อเปรียบเทียบผลลัพธ์
        """
        import asyncio
        
        async def safe_call(name, coro):
            try:
                res = await coro
                res["endpoint"] = name
                return name, res
            except Exception as e:
                logger.error(f"Error fetching from {name}: {e}")
                return name, {"error": str(e), "endpoint": name, "max_rain": 0.0}

        tasks = [
            safe_call("tomorrow", self.tomorrow_svc.predict_rain_by_location(lat, lng, mock_state=mock_state)),
            safe_call("rainbow-local", self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="local", mock_state=mock_state)),
            safe_call("rainbow-global", self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="global", mock_state=mock_state))
        ]
        
        results = await asyncio.gather(*tasks)
        return {k: v for k, v in results}
