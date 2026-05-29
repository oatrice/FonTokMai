import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# We will import app from main, but currently it doesn't exist
try:
    from app.main import app
    client = TestClient(app)
except ImportError:
    client = None

def test_predict_weather_success():
    if not client:
        pytest.fail("FastAPI app is not implemented yet")

    mock_prediction = {
        "predictions": [
            {"time": "2026-05-29T10:00:00Z", "rain": 0.0},
            {"time": "2026-05-29T10:10:00Z", "rain": 1.2}
        ]
    }
    
    with patch("app.routers.weather.RainbowService.predict_rain_by_location", new_callable=AsyncMock) as mock_predict:
        mock_predict.return_value = mock_prediction
        
        response = client.get("/api/v1/weather/predict?lat=17.1664&lng=104.1486")
        
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert len(data["predictions"]) == 2
        assert data["predictions"][1]["rain"] == 1.2
        mock_predict.assert_called_once_with(17.1664, 104.1486)

def test_predict_weather_missing_params():
    if not client:
        pytest.fail("FastAPI app is not implemented yet")

    response = client.get("/api/v1/weather/predict?lat=17.1664")
    assert response.status_code == 422

