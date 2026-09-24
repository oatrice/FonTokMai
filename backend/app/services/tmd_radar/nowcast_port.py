from app.services.tmd_radar.entities import RadarPredictionEntity
from typing import Protocol, Dict, Any, Optional

class NowcastPort(Protocol):
    async def predict(self, lat: float, lng: float, force_station: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Executes a nowcast prediction for the given coordinates.
        Returns a dictionary containing predictions, intensity, max_rain, etc.
        """
        ...
