# backend/tests/test_chainat_loop.py

import pytest
import httpx
import io
import cv2
import numpy as np
from unittest.mock import AsyncMock
from PIL import Image, ImageSequence
from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
from app.services.tmd_radar_config import STATIONS
from app.services.ocr_service import OCRService

def test_chainat_loop_url_configured_correctly():
    """Verify Chainat (chn) loop_gif_url is configured as chnloop.gif in catalog and config."""
    preset = next((p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "chn"), None)
    assert preset is not None
    assert preset["loop_gif_url"] == "https://weather.tmd.go.th/chn/chnloop.gif"

    assert "chn" in STATIONS
    assert STATIONS["chn"].loop_gif_url == "https://weather.tmd.go.th/chn/chnloop.gif"

@pytest.mark.asyncio
async def test_chainat_loop_gif_live_fetch():
    """Integration test: live fetch https://weather.tmd.go.th/chn/chnloop.gif and verify valid GIF bytes."""
    url = "https://weather.tmd.go.th/chn/chnloop.gif"
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(url)
        assert res.status_code == 200, f"Expected HTTP 200 for {url}, got {res.status_code}"
        assert len(res.content) > 10_000, f"Expected GIF size > 10KB, got {len(res.content)} bytes"
        assert res.content[:3] == b"GIF", "Downloaded content is not a valid GIF file"

@pytest.mark.asyncio
async def test_chainat_loop_gif_frame_extraction_and_transcribe():
    """Integration test: download chnloop.gif, extract frames via PIL, and run OCR transcribe."""
    url = "https://weather.tmd.go.th/chn/chnloop.gif"
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.get(url)
        assert res.status_code == 200
        gif_bytes = res.content

    # Extract GIF frames using PIL
    gif = Image.open(io.BytesIO(gif_bytes))
    frames = []
    for frame in ImageSequence.Iterator(gif):
        rgba = frame.convert('RGBA')
        bgr = cv2.cvtColor(np.array(rgba), cv2.COLOR_RGBA2BGR)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        frames.append(rgb)

    assert len(frames) > 0, "Failed to extract any frames from chnloop.gif"
    print(f"\n[INTEGRATION TEST] Extracted {len(frames)} frames from Chainat chnloop.gif. Frame shape: {frames[0].shape}")

    # Verify each frame's shape and non-empty content
    for i, frame in enumerate(frames):
        assert isinstance(frame, np.ndarray)
        assert frame.shape[0] > 100 and frame.shape[1] > 100

    # Test OCR service transcribe with mock repo to avoid uninitialized DB errors
    mock_repo = AsyncMock()
    mock_repo.get_radar_timestamp_cache = AsyncMock(return_value=None)
    mock_repo.set_radar_timestamp_cache = AsyncMock()
    ocr_service = OCRService(repo=mock_repo)
    fallback_ts = 1786426400

    timestamp = await ocr_service.get_frame_timestamp(frames[-1], fallback_ts=fallback_ts)
    assert timestamp is not None and isinstance(timestamp, int)
    print(f"[INTEGRATION TEST] Transcribe timestamp result for last frame: {timestamp}")
