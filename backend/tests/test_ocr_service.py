import pytest
import numpy as np
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from unittest.mock import patch, AsyncMock
import cv2

from app.services.ocr_service import OCRService

@pytest.fixture
def ocr_service():
    # Mock Firestore dependency inside the constructor
    with patch('app.services.ocr_service.FirestoreLocationRepository') as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.get_radar_timestamp_cache = AsyncMock(return_value=None)
        mock_repo_instance.set_radar_timestamp_cache = AsyncMock()
        service = OCRService()
        return service

def test_preprocess_image(ocr_service):
    # Create a dummy image 500x500 RGB
    img = np.zeros((500, 500, 3), dtype=np.uint8)
    
    processed = ocr_service._preprocess_image(img)
    # Ensure it cropped bottom 50px (since 500*0.1 = 50)
    assert processed.shape == (50, 500)
    # Ensure it's single channel (grayscale/thresh)
    assert len(processed.shape) == 2

def test_extract_timestamp_from_text(ocr_service):
    # Test DD/MM/YYYY HH:MM
    text1 = "some radar text 06/06/2026 09:30 some other text"
    ts1 = ocr_service._extract_timestamp_from_text(text1)
    
    bkk_tz = ZoneInfo('Asia/Bangkok')
    expected_dt1 = datetime(2026, 6, 6, 9, 30, 0, tzinfo=bkk_tz)
    assert ts1 == int(expected_dt1.astimezone(timezone.utc).timestamp())
    
    # Test YYYY-MM-DD HH:MM:SS
    text2 = "TMD RADAR 2026-06-06 09:30:15"
    ts2 = ocr_service._extract_timestamp_from_text(text2)
    expected_dt2 = datetime(2026, 6, 6, 9, 30, 15, tzinfo=bkk_tz)
    assert ts2 == int(expected_dt2.astimezone(timezone.utc).timestamp())
    
    # Test Invalid
    assert ocr_service._extract_timestamp_from_text("no date here") is None

@pytest.mark.asyncio
@patch('app.services.ocr_service.pytesseract.image_to_string')
async def test_get_frame_timestamp_cache_miss(mock_tesseract, ocr_service):
    mock_tesseract.return_value = "06/06/2026 10:00"
    
    frame = np.zeros((500, 500, 3), dtype=np.uint8)
    ts = await ocr_service.get_frame_timestamp(frame)
    
    bkk_tz = ZoneInfo('Asia/Bangkok')
    expected_dt = datetime(2026, 6, 6, 10, 0, 0, tzinfo=bkk_tz)
    assert ts == int(expected_dt.astimezone(timezone.utc).timestamp())
    
    # Verify tesseract was called
    mock_tesseract.assert_called_once()
    # Verify cache was set
    ocr_service.repo.set_radar_timestamp_cache.assert_called_once()

@pytest.mark.asyncio
async def test_get_frame_timestamp_cache_hit(ocr_service):
    # Mock that cache returns a timestamp
    expected_ts = 1234567890
    ocr_service.repo.get_radar_timestamp_cache.return_value = expected_ts
    
    frame = np.zeros((500, 500, 3), dtype=np.uint8)
    ts = await ocr_service.get_frame_timestamp(frame)
    
    assert ts == expected_ts
    # Verify tesseract was NOT called
    with patch('app.services.ocr_service.pytesseract.image_to_string') as mock_tesseract:
        mock_tesseract.assert_not_called()
