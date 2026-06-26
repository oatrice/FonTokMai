import pytest
import numpy as np
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from unittest.mock import patch, AsyncMock, MagicMock
import cv2
import sys
from unittest.mock import MagicMock
sys.modules['google.cloud.vision'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = MagicMock()

from app.services.ocr_service import OCRService

@pytest.fixture
def ocr_service():
    # Mock Firestore dependency inside the constructor
    with patch('app.services.ocr_service.FirestoreLocationRepository') as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.get_radar_timestamp_cache = AsyncMock(return_value=None)
        mock_repo_instance.set_radar_timestamp_cache = AsyncMock()
        mock_repo_instance.check_and_increment_vision_quota = AsyncMock(return_value=True)
        service = OCRService()
        return service

def test_frame_to_png_bytes(ocr_service):
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    png_bytes = ocr_service._frame_to_png_bytes(img)
    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 0

def test_extract_timestamp_from_text(ocr_service):
    # Test DD/MM/YYYY HH:MM
    text1 = "some radar text 06/06/2026 09:30 some other text"
    ts1 = ocr_service._extract_timestamp_from_text(text1)
    
    expected_dt1 = datetime(2026, 6, 6, 9, 30, 0, tzinfo=timezone.utc)
    assert ts1 == int(expected_dt1.timestamp())
    
    # Test YYYY-MM-DD HH:MM:SS
    text2 = "TMD RADAR 2026-06-06 09:30:15"
    ts2 = ocr_service._extract_timestamp_from_text(text2)
    expected_dt2 = datetime(2026, 6, 6, 9, 30, 15, tzinfo=timezone.utc)
    assert ts2 == int(expected_dt2.timestamp())
    
    # Test Invalid
    assert ocr_service._extract_timestamp_from_text("no date here") is None

@pytest.mark.asyncio
async def test_get_frame_timestamp_ocr_space_success(ocr_service):
    with patch.object(ocr_service, '_call_ocr_space', new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = "06/06/2026 10:00"
        
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        ts = await ocr_service.get_frame_timestamp(frame)
        
        expected_dt = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)
        assert ts == int(expected_dt.timestamp())
        
        mock_ocr.assert_called_once()
        ocr_service.repo.set_radar_timestamp_cache.assert_called_once()

@pytest.mark.skip(reason="Hotfix #85: Bypassed Vision and Gemini fallback chain")
@pytest.mark.asyncio
async def test_get_frame_timestamp_gemini_fallback(ocr_service):
    with patch.object(ocr_service, '_call_cloud_vision', new_callable=AsyncMock) as mock_vision, \
         patch.object(ocr_service, '_call_gemini', new_callable=AsyncMock) as mock_gemini:
        
        # Vision fails
        mock_vision.return_value = "no text"
        # Gemini succeeds
        mock_gemini.return_value = "06/06/2026 11:00"
        
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        ts = await ocr_service.get_frame_timestamp(frame)
        
        expected_dt = datetime(2026, 6, 6, 11, 0, 0, tzinfo=timezone.utc)
        assert ts == int(expected_dt.timestamp())
        
        mock_vision.assert_called_once()
        mock_gemini.assert_called_once()
        ocr_service.repo.set_radar_timestamp_cache.assert_called_once()

@pytest.mark.skip(reason="Hotfix #85: Bypassed Vision and Gemini fallback chain")
@pytest.mark.asyncio
async def test_get_frame_timestamp_ocr_space_fallback(ocr_service):
    with patch.object(ocr_service, '_call_cloud_vision', new_callable=AsyncMock) as mock_vision, \
         patch.object(ocr_service, '_call_gemini', new_callable=AsyncMock) as mock_gemini, \
         patch.object(ocr_service, '_call_ocr_space', new_callable=AsyncMock) as mock_ocr_space:
        
        mock_vision.return_value = None
        mock_gemini.return_value = None
        mock_ocr_space.return_value = "06/06/2026 12:00"
        
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        ts = await ocr_service.get_frame_timestamp(frame)
        
        expected_dt = datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc)
        assert ts == int(expected_dt.timestamp())
        
        mock_vision.assert_called_once()
        mock_gemini.assert_called_once()
        mock_ocr_space.assert_called_once()
        ocr_service.repo.set_radar_timestamp_cache.assert_called_once()

@pytest.mark.asyncio
async def test_get_frame_timestamp_fallback_ts(ocr_service):
    with patch.object(ocr_service, '_call_ocr_space', new_callable=AsyncMock) as mock_ocr_space:
        
        mock_ocr_space.return_value = None
        
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        fallback = 1717671600
        ts = await ocr_service.get_frame_timestamp(frame, fallback_ts=fallback)
        assert ts == fallback
        ocr_service.repo.set_radar_timestamp_cache.assert_not_called()

@pytest.mark.skip(reason="Hotfix #85: Bypassed Vision quota check")
@pytest.mark.asyncio
async def test_get_frame_timestamp_cloud_vision_quota_exceeded(ocr_service):
    # Mock quota to return False (exceeded)
    ocr_service.repo.check_and_increment_vision_quota = AsyncMock(return_value=False)
    
    with patch.object(ocr_service, '_call_cloud_vision', new_callable=AsyncMock) as mock_vision, \
         patch.object(ocr_service, '_call_gemini', new_callable=AsyncMock) as mock_gemini:
        
        mock_gemini.return_value = "06/06/2026 13:00"
        
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        ts = await ocr_service.get_frame_timestamp(frame)
        
        expected_dt = datetime(2026, 6, 6, 13, 0, 0, tzinfo=timezone.utc)
        assert ts == int(expected_dt.timestamp())
        
        # Cloud vision should NOT be called
        mock_vision.assert_not_called()
        # Gemini should be called
        mock_gemini.assert_called_once()
        # Quota check should have been called
        ocr_service.repo.check_and_increment_vision_quota.assert_called_once()
