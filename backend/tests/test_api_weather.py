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

@patch.dict('os.environ', {'XWEATHER_ENABLED': 'true', 'XWEATHER_CLIENT_ID': 'test', 'XWEATHER_CLIENT_SECRET': 'test'})
def test_compare_weather_apis_e2e():
    """
    E2E Test สำหรับ Issue #49: Compare all APIs
    โดยใช้ mock_state="rain" เพื่อจำลองข้อมูลโดยไม่ต้องยิง API จริง
    """
    if not client:
        pytest.fail("FastAPI app is not implemented yet")

    response = client.get("/api/v1/weather/compare?lat=13.7&lng=100.5&mock_state=rain")
    
    assert response.status_code == 200
    data = response.json()
    
    # ตรวจสอบว่ามีข้อมูลจาก API ครบถ้วนตามที่คาดหวังหรือไม่
    assert "xweather" in data
    assert "tomorrow" in data
    assert "rainbow-local" in data
    assert "rainbow-global" in data
    assert "open-meteo" in data
    
    # ตรวจสอบข้อมูลจาก open-meteo (ตาม spec mock_state="rain")
    assert data["open-meteo"]["max_rain"] == 15.0
    assert data["open-meteo"]["intensity"] == "หนัก (Heavy)"
    assert data["open-meteo"]["endpoint"] == "open-meteo"

    # Xweather ควรมีการนำ distance_km ของ stormcell มาแปะเป็น storm_distance_km
    assert "storm_distance_km" in data["xweather"]
    assert data["xweather"]["storm_distance_km"] == 10.0

