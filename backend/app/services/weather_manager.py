import logging
from typing import Optional
from .tomorrow import TomorrowService
from .rainbow import RainbowService
from .xweather import XweatherService
from .open_meteo import OpenMeteoService
from .tmd_radar_processor import TMDRadarProcessor

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

        # --- โหมดปกติ: Auto-select based on accuracy score ---
        from app.dependencies import get_repo_context
        async with get_repo_context() as repo:
            reliabilities = await repo.get_all_api_reliability()
            
        sorted_endpoints = sorted(reliabilities.keys(), key=lambda k: reliabilities[k], reverse=True)
        
        service_map = {
            "xweather": lambda: self.xweather_svc.predict_rain_by_location(lat, lng, mock_state=mock_state),
            "tomorrow": lambda: self.tomorrow_svc.predict_rain_by_location(lat, lng, mock_state=mock_state),
            "rainbow-local": lambda: self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="local", mock_state=mock_state),
            "rainbow-global": lambda: self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="global", mock_state=mock_state),
            "open-meteo": lambda: self.open_meteo_svc.predict_rain_by_location(lat, lng, mock_state=mock_state),
            "tmd-radar": lambda: self._get_tmd_prediction(lat, lng)
        }
        
        for ep in sorted_endpoints:
            if ep not in service_map:
                continue
                
            try:
                result = await service_map[ep]()
                logger.info(f"Successfully fetched weather from {ep} (accuracy: {reliabilities[ep]:.2f})")
                if "endpoint" not in result:
                    result["endpoint"] = ep
                    
                # หากดึงสำเร็จและมีการทายว่าฝนจะตก ให้บวก total_queries
                if result.get("max_rain", 0.0) > 0:
                    async with get_repo_context() as update_repo:
                        await update_repo.record_api_query_success(ep)
                        
                return result
            except Exception as e:
                logger.warning(f"{ep} failed: {e}. Falling back to next...")
                
        logger.error("All weather APIs failed in auto-select.")
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
        from app.dependencies import get_repo_context
        
        async with get_repo_context() as repo:
            reliabilities = await repo.get_all_api_reliability()
        
        async def safe_call(name, coro):
            try:
                res = await coro
                res["endpoint"] = name
                res["accuracy_score"] = reliabilities.get(name, 0.0)
                return name, res
            except Exception as e:
                import re
                error_msg = str(e)
                error_msg = re.sub(r'client_id=[^&\s]+', 'client_id=***', error_msg)
                error_msg = re.sub(r'client_secret=[^&\s]+', 'client_secret=***', error_msg)
                logger.error(f"Error fetching from {name}: {error_msg}")
                return name, {"error": error_msg, "endpoint": name, "max_rain": 0.0, "accuracy_score": reliabilities.get(name, 0.0)}

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
            if not self.xweather_svc.enabled or self.xweather_svc._is_circuit_open():
                raise Exception("Xweather is disabled or circuit is open")
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

    async def _get_tmd_prediction(self, lat: float, lng: float) -> dict:
        """
        Wrapper for TMD Radar predictions.
        In the future, this will check cached images, calculate optical flow trajectory, 
        and return the expected rain max_rain and ETA.
        """
        # MVP: Attempt to locate the station and see if it's in bounds
        for station_code in ["kkn120", "kkn240", "skn240"]:
            try:
                processor = TMDRadarProcessor(station_code)
                px, py = processor.latlng_to_pixel(lat, lng)
                if px is not None and py is not None:
                    # In a real scenario, we'd read the cached Optical Flow array and return ETA.
                    # Returning a stub for the integration task.
                    return {
                        "predictions": [],
                        "intensity": "ไม่ทราบ",
                        "max_rain": 0.0,
                        "duration_minutes": 0,
                        "wind_speed_kmh": 0.0,
                        "endpoint": "tmd-radar"
                    }
            except Exception:
                pass
        raise Exception("Location out of bounds for active TMD Radars.")
