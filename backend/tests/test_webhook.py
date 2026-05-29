import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)

def test_telegram_webhook_with_location():
    mock_prediction = {
        "predictions": [
            {"time": "2026-05-29T10:00:00Z", "rain": 0.0},
            {"time": "2026-05-29T10:20:00Z", "rain": 2.5}
        ]
    }
    
    # Mock RainbowService
    with patch("app.routers.webhook.RainbowService.predict_rain_by_location", new_callable=AsyncMock) as mock_predict:
        mock_predict.return_value = mock_prediction
        
        # Mock httpx.AsyncClient.post to telegram API
        with patch("app.routers.webhook.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            
            payload = {
                "update_id": 12345,
                "message": {
                    "message_id": 1,
                    "chat": {"id": 9999},
                    "location": {
                        "latitude": 17.1664,
                        "longitude": 104.1486
                    }
                }
            }
            
            response = client.post("/api/v1/webhook/telegram", json=payload)
            
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            
            mock_predict.assert_called_once_with(17.1664, 104.1486)
            
            # Check if telegram message was sent
            assert mock_post.called
            call_args = mock_post.call_args
            assert "api.telegram.org" in call_args[0][0]
            assert call_args[1]["json"]["chat_id"] == 9999
            assert "20 นาที" in call_args[1]["json"]["text"]

def test_telegram_webhook_without_location():
    with patch("app.routers.webhook.RainbowService.predict_rain_by_location", new_callable=AsyncMock) as mock_predict:
        payload = {
            "update_id": 12345,
            "message": {
                "message_id": 2,
                "chat": {"id": 9999},
                "text": "Hello"
            }
        }
        
        response = client.post("/api/v1/webhook/telegram", json=payload)
        
        # Should return 200 to acknowledge telegram, but do nothing
        assert response.status_code == 200
        assert response.json() == {"status": "ignored"}
        
        mock_predict.assert_not_called()
