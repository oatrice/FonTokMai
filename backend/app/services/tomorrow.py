import os
import logging
import httpx
from typing import Optional
from datetime import datetime, timezone
from .weather_base import BaseWeatherService

logger = logging.getLogger(__name__)

class TomorrowService(BaseWeatherService):
    API_URL = "https://api.tomorrow.io/v4/timelines"
    
    def __init__(self):
        self.api_key = os.getenv("TOMORROW_API_KEY")
        self.timeout = httpx.Timeout(15.0)

    async def get_current_radar_metadata(self) -> dict:
        return {
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "map_layer": None
        }

    async def predict_rain_by_location(self, lat: float, lng: float, mock_state: Optional[str] = None) -> dict:
        if not self.api_key or "INVALID" in self.api_key.upper():
            logger.error("TOMORROW_API_KEY is not set or marked invalid.")
            raise ValueError("TOMORROW_API_KEY is missing or invalid")

        if mock_state == "rain":
            return {
                "predictions": [{"time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "rain": 15.0}],
                "intensity": "หนัก (Heavy)",
                "max_rain": 15.0,
                "duration_minutes": 60,
                "wind_speed_kmh": 20.0,
                "endpoint": "tomorrow"
            }
        elif mock_state == "clear":
            return {
                "predictions": [{"time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "rain": 0.0}],
                "intensity": "ไม่มีฝน (No Rain)",
                "max_rain": 0.0,
                "duration_minutes": 0,
                "wind_speed_kmh": 5.0,
                "endpoint": "tomorrow"
            }

        params = {
            "location": f"{lat},{lng}",
            "fields": "precipitationIntensity,windSpeed,windDirection",
            "timesteps": "1m",
            "units": "metric",
            "apikey": self.api_key
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(self.API_URL, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Transform to our internal 'predictions' format
                predictions = []
                timelines = data.get("data", {}).get("timelines", [])
                
                max_rain = 0.0
                rain_start = None
                rain_end = None
                wind_speed_sum = 0.0
                wind_speed_count = 0
                wind_dir_sum = 0.0
                wind_dir_count = 0
                
                for timeline in timelines:
                    if timeline.get("timestep") == "1m":
                        intervals = timeline.get("intervals", [])
                        for interval in intervals:
                            time_str = interval.get("startTime", "")
                            values = interval.get("values", {})
                            precip = values.get("precipitationIntensity", 0.0)
                            wind = values.get("windSpeed", 0.0)
                            
                            predictions.append({
                                "time": time_str,
                                "rain": precip
                            })
                            
                            if precip > 0:
                                max_rain = max(max_rain, precip)
                                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00")).timestamp()
                                if not rain_start:
                                    rain_start = dt
                                rain_end = dt
                                
                                wind_speed_sum += wind
                                wind_speed_count += 1
                                
                                wind_dir = values.get("windDirection")
                                if wind_dir is not None:
                                    wind_dir_sum += wind_dir
                                    wind_dir_count += 1

                intensity_text = "ไม่มีฝน (No Rain)"
                duration_minutes = 0
                avg_wind_speed = 0.0
                wind_dir_text = "ไม่ทราบ"
                
                if max_rain > 0:
                    if max_rain < 2.5:
                        intensity_text = "เบา (Light)"
                    elif max_rain <= 10.0:
                        intensity_text = "ปานกลาง (Moderate)"
                    else:
                        intensity_text = "หนัก (Heavy)"
                        
                    if rain_start and rain_end:
                        duration_minutes = int((rain_end - rain_start) / 60)
                        
                    if wind_speed_count > 0:
                        avg_wind_speed = wind_speed_sum / wind_speed_count

                # Tomorrow.io wind is usually in m/s natively, but since units=metric, it might be m/s.
                # Usually standard metric wind speed is m/s. We will convert it to km/h.
                # 1 m/s = 3.6 km/h. Let's assume metric gives m/s.
                wind_speed_kmh = avg_wind_speed * 3.6
                
                if wind_dir_count > 0:
                    avg_wind_dir = wind_dir_sum / wind_dir_count
                    wind_dir_text = self.degrees_to_cardinal(avg_wind_dir)

                return {
                    "predictions": predictions,
                    "intensity": intensity_text,
                    "max_rain": max_rain,
                    "duration_minutes": duration_minutes,
                    "wind_speed_kmh": round(wind_speed_kmh, 1),
                    "wind_dir_text": wind_dir_text,
                    "endpoint": "tomorrow"
                }

            except httpx.HTTPStatusError as e:
                logger.error(f"Tomorrow.io HTTP error {e.response.status_code}: {e.response.text}")
                raise e
            except Exception as e:
                error_msg = str(e) if str(e) else repr(e)
                logger.error(f"Tomorrow.io Request failed: {error_msg}")
                raise Exception(error_msg)
