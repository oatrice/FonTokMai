import logging
from typing import Optional
from .tomorrow import TomorrowService
from .rainbow import RainbowService
from .xweather import XweatherService
from .open_meteo import OpenMeteoService

logger = logging.getLogger(__name__)

class WeatherManager:
    def __init__(self):
        self.xweather_svc = XweatherService()
        self.tomorrow_svc = TomorrowService()
        self.rainbow_svc = RainbowService()
        self.open_meteo_svc = OpenMeteoService()

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

        # --- โหมดปกติ: Xweather → Tomorrow.io → Rainbow Local → Rainbow Global ---

        # 1. Primary: Xweather
        try:
            result = await self.xweather_svc.predict_rain_by_location(lat, lng, mock_state=mock_state)
            logger.info("Successfully fetched weather from Xweather")
            return result
        except Exception as e:
            logger.warning(f"Xweather failed: {e}. Falling back to Tomorrow.io.")

        # 2. Secondary: Tomorrow.io
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
                import re
                error_msg = str(e)
                error_msg = re.sub(r'client_id=[^&\s]+', 'client_id=***', error_msg)
                error_msg = re.sub(r'client_secret=[^&\s]+', 'client_secret=***', error_msg)
                logger.error(f"Error fetching from {name}: {error_msg}")
                return name, {"error": error_msg, "endpoint": name, "max_rain": 0.0}

        async def fetch_xweather_full():
            res_rain, res_alerts = await asyncio.gather(
                self.xweather_svc.predict_rain_by_location(lat, lng, mock_state=mock_state),
                self.get_advanced_alerts(lat, lng, mock_state=mock_state)
            )
            storm = res_alerts.get("stormcell")
            if storm and storm.get("distance_km") is not None:
                res_rain["storm_distance_km"] = storm["distance_km"]
            return res_rain

        tasks = [
            safe_call("xweather", fetch_xweather_full()),
            safe_call("tomorrow", self.tomorrow_svc.predict_rain_by_location(lat, lng, mock_state=mock_state)),
            safe_call("rainbow-local", self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="local", mock_state=mock_state)),
            safe_call("rainbow-global", self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="global", mock_state=mock_state)),
            safe_call("open-meteo", self.open_meteo_svc.predict_rain_by_location(lat, lng, mock_state=mock_state))
        ]
        
        results = await asyncio.gather(*tasks)
        
        final_results = {}
        for k, v in results:
            if "predictions" in v:
                v["predictions"] = v["predictions"][:15]
            final_results[k] = v
            
        return final_results

    async def get_advanced_alerts(self, lat: float, lng: float, mock_state: Optional[str] = None) -> dict:
        """
        ดึงข้อมูลเตือนภัยขั้นสูงจาก Xweather (Advisories, Lightning, Stormcells)
        ถ้า Xweather ปิดอยู่ หรือ API พัง จะพยายามดึงข้อมูลลมจาก Open-Meteo แทน (Contingency)
        """
        try:
            return await self.xweather_svc.get_advanced_alerts(lat, lng, mock_state=mock_state)
        except Exception as e:
            logger.warning(f"Failed to fetch advanced alerts from Xweather: {e}. Falling back to Open-Meteo for wind vectors.")
            try:
                wind_data = await self.open_meteo_svc.get_wind_vector(lat, lng, mock_state=mock_state)
                return {
                    "advisories": [], 
                    "lightning": None, 
                    "stormcell": {
                        "distance_km": None,
                        "direction": wind_data.get("direction_cardinal", ""),
                        "speed_kmh": wind_data.get("speed_kmh", 0),
                        "max_dbz": None
                    }
                }
            except Exception as e_meteo:
                logger.error(f"Open-Meteo Contingency failed: {e_meteo}")
                return {"advisories": [], "lightning": None, "stormcell": None}
