import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import numpy as np
import io
from PIL import Image

from app.services.telegram import send_telegram_photo
from app.services.tmd_radar.processor import TMDRadarProcessor
from app.services.weather_manager import WeatherManager

@pytest.mark.asyncio
async def test_telegram_photo_compression():
    """Test that send_telegram_photo automatically compresses large images."""
    # Create a realistic smooth graphic image (1200x1200)
    arr = np.zeros((1200, 1200, 3), dtype=np.uint8)
    for i in range(1200):
        arr[i, :, 0] = i % 255
        arr[:, i, 1] = (i * 2) % 255
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=0)  # Uncompressed PNG (~4.3MB)
    large_bytes = buf.getvalue()
    
    assert len(large_bytes) > 400 * 1024  # Ensure initial size > 400KB

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        success = await send_telegram_photo(123456, large_bytes, "radar_latest.png")
        assert success is True
        assert mock_post.called

        # Extract sent file data from call arguments
        call_kwargs = mock_post.call_args[1]
        files = call_kwargs.get("files", {})
        photo_tuple = files.get("photo")
        assert photo_tuple is not None
        sent_filename, sent_bytes, content_type = photo_tuple

        # Check that filename was updated to .jpg and size is significantly reduced (< 400KB)
        assert sent_filename.endswith(".jpg")
        assert len(sent_bytes) < len(large_bytes)
        assert len(sent_bytes) < 400 * 1024

@pytest.mark.asyncio
async def test_radar_cache_fetch_retry_with_status_callback():
    """Test that fetch_latest_image_bytes retries on connection error and calls status_callback."""
    processor = TMDRadarProcessor("phs")

    retry_status_updates = []
    async def mock_status_callback(msg: str):
        retry_status_updates.append(msg)

    # Mock http client to fail 2 times then succeed on 3rd attempt
    mock_client = AsyncMock()
    fail_resp = MagicMock()
    fail_resp.status_code = 503

    success_resp = MagicMock()
    success_resp.status_code = 200
    success_resp.content = b"fake_radar_image_bytes"

    # Side effect: exception, exception, success
    import httpx
    mock_client.get.side_effect = [
        httpx.ConnectTimeout("Connection timed out"),
        httpx.ConnectTimeout("Connection timed out"),
        success_resp
    ]

    with patch("app.dependencies.get_http_client", return_value=mock_client):
        res = await processor.fetch_latest_image_bytes(status_callback=mock_status_callback, max_retries=3, retry_delay=0.01)
        assert res == b"fake_radar_image_bytes"
        assert mock_client.get.call_count == 3
        assert len(retry_status_updates) == 2
        assert "phs" in retry_status_updates[0]
        assert "2/3" in retry_status_updates[0]
