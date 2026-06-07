import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from .weather_base import BaseWeatherService

logger = logging.getLogger(__name__)

class OpenMeteoService(BaseWeatherService):
    API_URL = "https://api.open-meteo.com/v1/forecast"
    
    def __init__(self, default_model: str = "auto"):
        self.default_model = default_model
        self.timeout = httpx.Timeout(10.0)

    async def get_current_radar_metadata(self) -> dict:
        # Open-Meteo doesn't provide radar metadata in the same way, we return dummy/empty
        return {
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "map_layer": None
        }

    async def predict_rain_by_location(self, lat: float, lng: float, mock_state: Optional[str] = None, model: Optional[str] = None) -> dict:
        """
        ดึงข้อมูลพยากรณ์ฝนล่วงหน้า (minutely_15) และลม (hourly)
        """
        if mock_state == "rain":
            return {
                "predictions": [{"time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "rain": 15.0}],
                "intensity": "หนัก (Heavy)",
                "max_rain": 15.0,
                "duration_minutes": 60,
                "wind_speed_kmh": 20.0,
                "endpoint": "open_meteo"
            }
        elif mock_state == "clear":
            return {
                "predictions": [{"time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "rain": 0.0}],
                "intensity": "ไม่มีฝน (No Rain)",
                "max_rain": 0.0,
                "duration_minutes": 0,
                "wind_speed_kmh": 5.0,
                "endpoint": "open_meteo"
            }
        elif mock_state == "error":
            raise Exception("Mock Network Error: Unable to reach Open-Meteo API")

        active_model = model or self.default_model

        params = {
            "latitude": lat,
            "longitude": lng,
            "minutely_15": "precipitation",
            "hourly": "wind_speed_10m,wind_direction_10m",
            "timezone": "UTC"
        }
        if active_model != "auto":
            params["models"] = active_model

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(self.API_URL, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Parse minutely precipitation (15-min intervals)
                predictions = []
                max_rain = 0.0
                rain_start = None
                rain_end = None
                
                minutely = data.get("minutely_15", {})
                times = minutely.get("time", [])
                precips = minutely.get("precipitation", [])
                
                now_utc = datetime.now(timezone.utc)
                now_ts = now_utc.timestamp()
                
                start_idx = 0
                for i, t_str in enumerate(times):
                    t_str_iso = t_str + "Z" if not t_str.endswith("Z") else t_str
                    try:
                        dt = datetime.fromisoformat(t_str_iso.replace("Z", "+00:00"))
                        if dt.timestamp() >= now_ts - 15 * 60:  # Include current 15-min window
                            start_idx = i
                            break
                    except ValueError:
                        pass
                
                limit = min(len(times), len(precips), start_idx + 12)
                for i in range(start_idx, limit):
                    # Replace string '2026-06-05T12:00' with valid ISO '2026-06-05T12:00Z'
                    time_str = times[i]
                    if not time_str.endswith("Z"):
                        time_str += "Z"
                        
                    p_val = precips[i] if precips[i] is not None else 0.0
                    
                    predictions.append({
                        "time": time_str,
                        "rain": p_val
                    })
                    
                    if p_val > 0:
                        max_rain = max(max_rain, p_val)
                        try:
                            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00")).timestamp()
                            if not rain_start:
                                rain_start = dt
                            rain_end = dt
                        except ValueError:
                            pass
                            
                # Get current wind from hourly
                hourly = data.get("hourly", {})
                h_winds = hourly.get("wind_speed_10m", [])
                current_wind_speed = h_winds[0] if h_winds else 0.0
                
                intensity_text = "ไม่มีฝน (No Rain)"
                duration_minutes = 0
                
                if max_rain > 0:
                    if max_rain < 2.5:
                        intensity_text = "เบา (Light)"
                    elif max_rain <= 10.0:
                        intensity_text = "ปานกลาง (Moderate)"
                    else:
                        intensity_text = "หนัก (Heavy)"
                        
                    if rain_start and rain_end:
                        duration_minutes = int((rain_end - rain_start) / 60)
                        if duration_minutes == 0:
                            duration_minutes = 15 # Minimum 15 mins block
                
                return {
                    "predictions": predictions,
                    "intensity": intensity_text,
                    "max_rain": max_rain,
                    "duration_minutes": duration_minutes,
                    "wind_speed_kmh": current_wind_speed,
                    "endpoint": "open_meteo"
                }

            except Exception as e:
                error_msg = str(e) if str(e) else repr(e)
                logger.error(f"Open-Meteo Request failed: {error_msg}")
                raise Exception(f"Open-Meteo Error: {error_msg}")

    async def get_wind_vector(self, lat: float, lng: float, mock_state: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """
        ดึงข้อมูลลมปัจจุบัน (speed, direction) ไว้เป็น Contingency หาก Xweather พัง
        """
        if mock_state == "rain":
            return {"speed_kmh": 40.0, "direction_deg": 90, "direction_cardinal": "E", "source": "open_meteo"}
        elif mock_state == "clear":
            return {"speed_kmh": 10.0, "direction_deg": 180, "direction_cardinal": "S", "source": "open_meteo"}
        elif mock_state == "error":
            raise Exception("Mock Network Error")

        active_model = model or self.default_model

        params = {
            "latitude": lat,
            "longitude": lng,
            "current": "wind_speed_10m,wind_direction_10m",
            "timezone": "UTC"
        }
        if active_model != "auto":
            params["models"] = active_model

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(self.API_URL, params=params)
                response.raise_for_status()
                data = response.json()
                
                current = data.get("current", {})
                speed = current.get("wind_speed_10m", 0.0)
                direction = current.get("wind_direction_10m", 0)
                
                return {
                    "speed_kmh": speed,
                    "direction_deg": direction,
                    "direction_cardinal": self.degrees_to_cardinal(direction),
                    "source": "open_meteo"
                }
            except Exception as e:
                error_msg = str(e) if str(e) else repr(e)
                logger.error(f"Open-Meteo Wind Vector Request failed: {error_msg}")
                raise Exception(f"Open-Meteo Error: {error_msg}")
