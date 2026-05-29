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
