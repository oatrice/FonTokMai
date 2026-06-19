"""
E2E Test: OCR Service Fallback Chain
ทดสอบว่า OCRService.get_frame_timestamp() ทำงานถูกต้องใน 3 สถานการณ์:
1. Normal Flow: OCR.space คืน text ที่มี timestamp → parse ถูกต้อง
2. OCR Parse เจอ text format แปลก → ใช้ fallback_ts
3. OCR.space ล้มเหลว → fallback_ts ถูกนำมาใช้แทน
"""
import pytest
import respx
import httpx
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ocr_service import OCRService


# ────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────

@pytest.fixture
def ocr_service(monkeypatch):
    monkeypatch.setenv("OCR_SPACE_API_KEY", "mock-key")
    monkeypatch.setenv("GEMINI_API_KEY", "")  # ปิด Gemini ไว้ก่อน
    return OCRService()


@pytest.fixture
def dummy_frame():
    """ภาพ dummy 100x100 พิกเซลสีเทา"""
    return np.zeros((100, 100, 3), dtype=np.uint8)


# ────────────────────────────────────────────────────────────
# 1. Unit Test: _extract_timestamp_from_text
# ────────────────────────────────────────────────────────────

def test_extract_timestamp_dd_mm_yyyy(monkeypatch):
    """OCR text format DD/MM/YYYY HH:MM ต้องแปลงเป็น Unix timestamp ได้"""
    monkeypatch.setenv("OCR_SPACE_API_KEY", "mock-key")
    svc = OCRService.__new__(OCRService)
    svc.gemini_client = None
    svc.ocr_space_key = "mock"

    ts = svc._extract_timestamp_from_text("Radar Image\n06/06/2026 09:30 UTC")
    assert ts is not None
    # 2026-06-06 09:30:00 UTC
    from datetime import datetime, timezone
    expected = int(datetime(2026, 6, 6, 9, 30, 0, tzinfo=timezone.utc).timestamp())
    assert ts == expected


def test_extract_timestamp_iso_format(monkeypatch):
    """OCR text format YYYY-MM-DD HH:MM:SS ต้องแปลงได้"""
    monkeypatch.setenv("OCR_SPACE_API_KEY", "mock-key")
    svc = OCRService.__new__(OCRService)
    svc.gemini_client = None
    svc.ocr_space_key = "mock"

    ts = svc._extract_timestamp_from_text("2026-06-19 15:45:00")
    assert ts is not None
    from datetime import datetime, timezone
    expected = int(datetime(2026, 6, 19, 15, 45, 0, tzinfo=timezone.utc).timestamp())
    assert ts == expected


def test_extract_timestamp_garbage_text_returns_none(monkeypatch):
    """Text ที่ไม่มี timestamp ต้อง return None ไม่ crash"""
    monkeypatch.setenv("OCR_SPACE_API_KEY", "mock-key")
    svc = OCRService.__new__(OCRService)
    svc.gemini_client = None
    svc.ocr_space_key = "mock"

    ts = svc._extract_timestamp_from_text("hello world, no date here!")
    assert ts is None


def test_extract_timestamp_empty_string_returns_none(monkeypatch):
    """Empty string ต้อง return None ไม่ crash"""
    monkeypatch.setenv("OCR_SPACE_API_KEY", "mock-key")
    svc = OCRService.__new__(OCRService)
    svc.gemini_client = None
    svc.ocr_space_key = "mock"

    ts = svc._extract_timestamp_from_text("")
    assert ts is None


# ────────────────────────────────────────────────────────────
# 2. E2E Flow: OCR.space สำเร็จ → ต้องได้ timestamp
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ocr_space_success_returns_timestamp(ocr_service, dummy_frame):
    """
    Mock OCR.space ให้ return text ที่มี timestamp
    ต้องได้ Unix timestamp ออกมา ไม่ใช่ None
    """
    mock_ocr_response = {
        "IsErroredOnProcessing": False,
        "ParsedResults": [
            {"ParsedText": "TMD Radar\n19/06/2026 15:30 UTC\nSome info"}
        ]
    }

    # Mock Firestore repo ที่ OCRService ใช้
    mock_repo = AsyncMock()
    mock_repo.get_radar_timestamp_cache.return_value = None
    mock_repo.set_radar_timestamp_cache.return_value = None
    ocr_service.repo = mock_repo

    with patch.object(ocr_service, "_call_ocr_space", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = "TMD Radar\n19/06/2026 15:30 UTC"

        ts = await ocr_service.get_frame_timestamp(dummy_frame, fallback_ts=9999)

    assert ts is not None
    assert ts != 9999  # ต้องได้ค่าจาก OCR ไม่ใช่ fallback

    from datetime import datetime, timezone
    expected = int(datetime(2026, 6, 19, 15, 30, 0, tzinfo=timezone.utc).timestamp())
    assert ts == expected


# ────────────────────────────────────────────────────────────
# 3. E2E Fallback: OCR.space ล้มเหลว → ใช้ fallback_ts
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ocr_space_fail_uses_fallback_ts(ocr_service, dummy_frame):
    """
    ถ้า OCR.space ล้มเหลว (return None)
    ต้องใช้ fallback_ts แทน ไม่ใช่ return None เฉยๆ
    """
    mock_repo = AsyncMock()
    mock_repo.get_radar_timestamp_cache.return_value = None
    mock_repo.set_radar_timestamp_cache.return_value = None
    ocr_service.repo = mock_repo

    with patch.object(ocr_service, "_call_ocr_space", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = None  # OCR.space ล้มเหลว

        fallback = 1718793600  # dummy timestamp
        ts = await ocr_service.get_frame_timestamp(dummy_frame, fallback_ts=fallback)

    assert ts == fallback


# ────────────────────────────────────────────────────────────
# 4. E2E: OCR.space คืน garbage text → ใช้ fallback_ts
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ocr_garbage_text_uses_fallback_ts(ocr_service, dummy_frame):
    """
    ถ้า OCR.space return text แต่ไม่มี timestamp format ที่ recognize ได้
    ต้องใช้ fallback_ts ไม่ crash
    """
    mock_repo = AsyncMock()
    mock_repo.get_radar_timestamp_cache.return_value = None
    mock_repo.set_radar_timestamp_cache.return_value = None
    ocr_service.repo = mock_repo

    with patch.object(ocr_service, "_call_ocr_space", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = "ภาษาไทย blah blah no date"

        fallback = 1718793600
        ts = await ocr_service.get_frame_timestamp(dummy_frame, fallback_ts=fallback)

    assert ts == fallback


# ────────────────────────────────────────────────────────────
# 5. E2E: Cache hit → ใช้ค่าจาก cache ทันที ไม่เรียก OCR
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_hit_skips_ocr(ocr_service, dummy_frame):
    """
    ถ้ามี cache อยู่แล้ว ต้อง return จาก cache ทันที
    และไม่เรียก OCR.space เลย (เพื่อประหยัด quota)
    """
    cached_ts = 1718793600
    mock_repo = AsyncMock()
    mock_repo.get_radar_timestamp_cache.return_value = cached_ts
    ocr_service.repo = mock_repo

    with patch.object(ocr_service, "_call_ocr_space", new_callable=AsyncMock) as mock_ocr:
        ts = await ocr_service.get_frame_timestamp(dummy_frame)

    assert ts == cached_ts
    mock_ocr.assert_not_called()  # ต้องไม่เรียก OCR เลย


# ────────────────────────────────────────────────────────────
# 6. All-fail: OCR + fallback_ts=None → คืน None ไม่ crash
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_fail_no_fallback_returns_none(ocr_service, dummy_frame):
    """
    ถ้าทั้ง OCR และ fallback_ts เป็น None
    ต้องคืน None ไม่ raise Exception
    """
    mock_repo = AsyncMock()
    mock_repo.get_radar_timestamp_cache.return_value = None
    mock_repo.set_radar_timestamp_cache.return_value = None
    ocr_service.repo = mock_repo

    with patch.object(ocr_service, "_call_ocr_space", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = None

        ts = await ocr_service.get_frame_timestamp(dummy_frame, fallback_ts=None)

    assert ts is None
