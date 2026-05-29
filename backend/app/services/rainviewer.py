import httpx
from .weather_base import BaseWeatherService

class RainViewerService(BaseWeatherService):
    API_URL = "https://api.rainviewer.com/public/weather-maps.json"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "FonMaYang-Weather-App/1.0"
        }
        self.timeout = httpx.Timeout(10.0)

    async def get_current_radar_metadata(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.get(self.API_URL)
            response.raise_for_status()
            data = response.json()
            
            # Use the latest past radar frame
            latest_frame = data.get("radar", {}).get("past", [{}])[-1]
            return {
                "timestamp": latest_frame.get("time"),
                "map_layer": f"{data.get('host')}{latest_frame.get('path')}/256/{{z}}/{{x}}/{{y}}/2/1_1.png"
            }

    async def predict_rain_by_location(self, lat: float, lng: float) -> dict:
        # RainViewer public API provides global weather maps, 
        # predicting at exact points might require further parsing of tiles.
        # Returning a placeholder structure for MVP.
        return {"predictions": []}
