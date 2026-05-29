from pydantic import BaseModel, Field
from typing import List

class PredictionItem(BaseModel):
    time: str = Field(..., description="Timestamp of the prediction")
    rain: float = Field(..., description="Rain intensity")

class PredictionResponse(BaseModel):
    predictions: List[PredictionItem] = Field(..., description="List of rain predictions for the next 15-30 minutes")
