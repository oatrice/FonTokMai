from fastapi import APIRouter, Query, HTTPException
from app.schemas.weather import PredictionResponse
from app.services.rainbow import RainbowService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["weather"]
)

@router.get("/predict", response_model=PredictionResponse)
async def predict_weather(
    lat: float = Query(..., description="Latitude of the location"),
    lng: float = Query(..., description="Longitude of the location")
):
    """
    Get short-term rain predictions (15-30 minutes) for a specific location.
    """
    try:
        rainbow_service = RainbowService()
        result = await rainbow_service.predict_rain_by_location(lat, lng)
        return result
    except Exception as e:
        logger.error(f"Error getting rain prediction: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching predictions")

@router.get("/compare")
async def compare_weather_apis(
    lat: float = Query(..., description="Latitude of the location"),
    lng: float = Query(..., description="Longitude of the location"),
    mock_state: str = Query(None, description="Mock state e.g. rain, clear, error")
):
    """
    Compare rain predictions from all available APIs. (Issue #49)
    """
    from app.services.weather_manager import WeatherManager
    try:
        weather_manager = WeatherManager()
        result = await weather_manager.compare_all_apis(lat, lng, mock_state=mock_state)
        return result
    except Exception as e:
        logger.error(f"Error comparing APIs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while comparing APIs")
