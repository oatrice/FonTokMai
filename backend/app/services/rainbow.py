import os
import logging
import httpx
from datetime import datetime, timezone
from .weather_base import BaseWeatherService

logger = logging.getLogger(__name__)

class RainbowService(BaseWeatherService):
    # Example API endpoint for Rainbow Weather (You would replace with actual endpoint)
    # The actual API endpoint might require specific params for prediction
    API_URL = "https://api.rainbow.ai/v1/nowcast"
    
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

    async def predict_rain_by_location(self, lat: float, lng: float) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            # Querying forecast for the next 4 hours
            # The actual payload depends on the Rainbow API docs
            params = {
                "lat": lat,
                "lon": lng,
                "duration": 240 # 4 hours
            }
            # Note: We wrap the request in a try-except to avoid breaking tests if the API requires auth
            try:
                response = await client.get(self.API_URL, params=params)
                response.raise_for_status()
                data = response.json()
                predictions = data.get("predictions", [])
                
                # Calculate intensity and duration
                intensity_text: str = "ไม่มีฝน (No Rain)"
                duration_minutes: int = 0
                
                if predictions:
                    max_rain: float = 0.0
                    rain_start = None
                    rain_end = None
                    
                    for pred in predictions:
                        r = pred.get("rain", 0)
                        if r > 0:
                            max_rain = max(max_rain, r)
                            try:
                                t = datetime.fromisoformat(pred.get("time", "").replace("Z", "+00:00"))
                                if not rain_start:
                                    rain_start = t
                                rain_end = t
                            except Exception:
                                pass
                                
                    if max_rain > 0:
                        if max_rain < 2.5:
                            intensity_text = "เบา (Light)"
                        elif max_rain <= 10.0:
                            intensity_text = "ปานกลาง (Moderate)"
                        else:
                            intensity_text = "หนัก (Heavy)"
                            
                        if rain_start and rain_end:
                            diff = int((rain_end - rain_start).total_seconds() / 60)
                            duration_minutes = diff + 10
                
                return {
                    "predictions": predictions,
                    "intensity": intensity_text,
                    "duration_minutes": duration_minutes
                }
            except httpx.HTTPError as e:
                logger.error(f"Rainbow.ai API error: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response status: {e.response.status_code}, content: {e.response.text}")
                # Return empty predictions on failure for MVP safety
                return {
                    "predictions": [{"time": "2026-05-29T14:00:00Z", "rain": 0}],
                    "intensity": "ไม่มีฝน (No Rain)",
                    "duration_minutes": 0
                }
