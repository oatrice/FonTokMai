import cv2
import numpy as np
import pytesseract
import re
import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional

from app.repositories.firestore import FirestoreLocationRepository

class OCRService:
    def __init__(self):
        self.repo = FirestoreLocationRepository()

    def _hash_frame(self, frame: np.ndarray) -> str:
        """Create a fast MD5 hash of the numpy frame."""
        return hashlib.md5(frame.tobytes()).hexdigest()

    def _preprocess_image(self, frame: np.ndarray) -> np.ndarray:
        """
        Crop the bottom part of the image where the timestamp is usually located.
        Convert to grayscale and apply thresholding for better OCR.
        """
        h, w = frame.shape[:2]
        # Crop the bottom 10% or bottom 50 pixels (approximate for radar timestamp)
        crop_h = max(int(h * 0.1), 50)
        cropped = frame[h - crop_h:h, 0:w]
        
        # Convert to grayscale
        gray = cv2.cvtColor(cropped, cv2.COLOR_RGB2GRAY)
        
        # Threshold (assuming white text on dark background or vice-versa)
        # Otsu's thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def _extract_timestamp_from_text(self, text: str) -> Optional[int]:
        """
        Parse text like "06 Jun 2026 09:30" or "2026-06-06 09:30:00"
        TMD radar typically has formats like "06/06/2026 09:30"
        """
        # Look for DD/MM/YYYY HH:MM or YYYY-MM-DD HH:MM
        # This is a naive regex that captures basic date and time
        match = re.search(r'(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}(?::\d{2})?)', text)
        if match:
            date_str = match.group(1)
            time_str = match.group(2)
            try:
                if '/' in date_str:
                    # DD/MM/YYYY
                    day, month, year = map(int, date_str.split('/'))
                else:
                    # YYYY-MM-DD
                    year, month, day = map(int, date_str.split('-'))
                
                time_parts = list(map(int, time_str.split(':')))
                hour = time_parts[0]
                minute = time_parts[1]
                second = time_parts[2] if len(time_parts) > 2 else 0
                
                bkk_tz = ZoneInfo('Asia/Bangkok')
                dt_bkk = datetime(year, month, day, hour, minute, second, tzinfo=bkk_tz)
                return int(dt_bkk.astimezone(timezone.utc).timestamp())
            except Exception as e:
                print(f"OCR Parsing error: {e}")
        return None

    async def get_frame_timestamp(self, frame: np.ndarray, fallback_ts: Optional[int] = None) -> Optional[int]:
        """
        Check cache for the frame hash. If not found, run OCR to extract timestamp.
        Returns the UTC timestamp integer.
        """
        frame_hash = self._hash_frame(frame)
        cached_ts = await self.repo.get_radar_timestamp_cache(frame_hash)
        if cached_ts is not None:
            return cached_ts

        # Run OCR
        processed = self._preprocess_image(frame)
        
        # psm 7 = Treat the image as a single text line.
        # psm 6 = Assume a single uniform block of text.
        text = pytesseract.image_to_string(processed, config='--psm 6').strip()
        
        ts = self._extract_timestamp_from_text(text)
        
        if ts is None and fallback_ts is not None:
            ts = fallback_ts
            
        if ts is not None:
            # Cache the result
            await self.repo.set_radar_timestamp_cache(frame_hash, ts)
        
        return ts
