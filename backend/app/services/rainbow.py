import os
import logging
import httpx
from typing import Optional
from datetime import datetime, timezone
from .weather_base import BaseWeatherService

logger = logging.getLogger(__name__)

class RainbowService(BaseWeatherService):
    # Example API endpoint for Rainbow Weather (You would replace with actual endpoint)
    # The actual API endpoint might require specific params for prediction
    API_URL = "https://api.rainbow.ai/nowcast/v1/precip-global"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "FonMaYang-Weather-App/1.0",
            "Accept": "application/json"
        }
        api_key = os.getenv("RAINBOW_API_KEY")
        if api_key:
            self.headers["Ocp-Apim-Subscription-Key"] = api_key
            
        self.timeout = httpx.Timeout(10.0)

    async def get_current_radar_metadata(self) -> dict:
        # Rainbow primarily focuses on Nowcast predictions rather than raw map tiles in standard APIs,
        # but we implement this to satisfy the Base abstract class.
        return {
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "map_layer": None
        }

    async def predict_rain_by_location(self, lat: float, lng: float, endpoint_type: str = "global", mock_state: Optional[str] = None) -> dict:
        if mock_state == "rain":
            return {
                "predictions": [{"time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "rain": 15.0}],
                "intensity": "หนัก (Heavy)",
                "max_rain": 15.0,
                "duration_minutes": 60,
                "endpoint": endpoint_type
            }
        elif mock_state == "clear":
            return {
                "predictions": [{"time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "rain": 0.0}],
                "intensity": "ไม่มีฝน (No Rain)",
                "max_rain": 0.0,
                "duration_minutes": 0,
                "endpoint": endpoint_type
            }

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            try:
                # Determine base API URL
                base_url = "https://api.rainbow.ai/nowcast/v1/precip-global" if endpoint_type == "global" else "https://api.rainbow.ai/nowcast/v1/precip"
                
                # API expects longitude first, then latitude in the URL path
                url = f"{base_url}/{lng}/{lat}"
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                forecast = data.get("forecast", [])
                summary = data.get("summary", {})
                
                # Transform to our internal 'predictions' format
                predictions = []
                for item in forecast:
                    t_begin = item.get("timestampBegin", 0)
                    if t_begin > 0:
                        dt = datetime.fromtimestamp(t_begin, timezone.utc)
                        time_str = dt.isoformat().replace("+00:00", "Z")
                    else:
                        time_str = ""
                    
                    predictions.append({
                        "time": time_str,
                        "rain": item.get("precipRate", 0.0)
                    })
                
                # Calculate intensity and duration
                intensity_text: str = "ไม่มีฝน (No Rain)"
                duration_minutes: int = 0
                
                if forecast:
                    max_rain: float = 0.0
                    rain_start = None
                    rain_end = None
                    
                    for item in forecast:
                        r = item.get("precipRate", 0.0)
                        if r > 0:
                            max_rain = max(max_rain, r)
                            t_begin = item.get("timestampBegin")
                            t_end = item.get("timestampEnd")
                            if t_begin and t_end:
                                if not rain_start:
                                    rain_start = t_begin
                                rain_end = t_end
                                
                    if max_rain > 0:
                        api_intensity = summary.get("intensity", "").lower()
                        if api_intensity == "light":
                            intensity_text = "เบา (Light)"
                        elif api_intensity == "moderate":
                            intensity_text = "ปานกลาง (Moderate)"
                        elif api_intensity in ("heavy", "extreme"):
                            intensity_text = "หนัก (Heavy)"
                        else:
                            # Fallback calculation if summary is missing
                            if max_rain < 2.5:
                                intensity_text = "เบา (Light)"
                            elif max_rain <= 10.0:
                                intensity_text = "ปานกลาง (Moderate)"
                            else:
                                intensity_text = "หนัก (Heavy)"
                                
                        if rain_start and rain_end:
                            diff = int((rain_end - rain_start) / 60)
                            duration_minutes = diff
                
                return {
                    "predictions": predictions,
                    "intensity": intensity_text,
                    "max_rain": max_rain if forecast else 0.0,
                    "duration_minutes": duration_minutes,
                    "endpoint": endpoint_type
                }
            except httpx.HTTPError as e:
                logger.error(f"Rainbow.ai API error: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response status: {e.response.status_code}, content: {e.response.text}")
                # Return empty predictions on failure for MVP safety
                return {
                    "predictions": [{"time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "rain": 0}],
                    "intensity": "ไม่มีฝน (No Rain)",
                    "max_rain": 0.0,
                    "duration_minutes": 0,
                    "endpoint": endpoint_type
                }
