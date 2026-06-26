import cv2
import numpy as np
import re
import hashlib
import os
import io
import json
import base64
import httpx
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional

try:
    from google.cloud import vision
except ImportError:
    vision = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

from app.repositories.firestore import FirestoreLocationRepository

class OCRService:
    def __init__(self):
        self.repo = FirestoreLocationRepository()
        
        # Initialize Gemini API if key is present and package is installed
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.gemini_client = None
        if self.gemini_key and genai is not None:
            self.gemini_client = genai.Client(api_key=self.gemini_key)
            
        self.ocr_space_key = os.environ.get("OCR_SPACE_API_KEY")

    def _hash_frame(self, frame: np.ndarray) -> str:
        """Create a fast MD5 hash of the numpy frame."""
        return hashlib.md5(frame.tobytes() + b"v2").hexdigest()

    def _frame_to_png_bytes(self, frame: np.ndarray) -> bytes:
        """Convert a numpy frame to PNG bytes."""
        # Convert RGB to BGR for cv2 encoding (TMD frames are usually RGB in memory)
        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        success, encoded_image = cv2.imencode('.png', bgr_frame)
        if not success:
            raise ValueError("Could not encode image to PNG")
        return encoded_image.tobytes()

    async def _call_cloud_vision(self, content: bytes) -> Optional[str]:
        """Call Google Cloud Vision API to extract text."""
        if vision is None:
            print("Cloud Vision API package not installed. Skipping.")
            return None
            
        try:
            import asyncio
            client = vision.ImageAnnotatorClient()
            image = vision.Image(content=content)
            response = await asyncio.to_thread(client.text_detection, image=image)
            
            if response.error.message:
                print(f"Cloud Vision API Error: {response.error.message}")
                return None
                
            texts = response.text_annotations
            if texts:
                return texts[0].description
            return None
        except Exception as e:
            print(f"Cloud Vision Exception: {e}")
            return None

    async def _call_gemini(self, content: bytes) -> Optional[str]:
        """Call Gemini 2.5 Flash to extract text."""
        if genai is None:
            print("Gemini API package not installed. Skipping.")
            return None
            
        if not self.gemini_client:
            print("Gemini API key not found or client not initialized.")
            return None
            
        try:
            prompt = "Extract all the text you can see in this radar image exactly as it appears. Do not format as markdown. Keep the date and time together on the same line."
            
            response = await self.gemini_client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    prompt,
                    types.Part.from_bytes(data=content, mime_type="image/png")
                ]
            )
            return response.text
        except Exception as e:
            print(f"Gemini Exception: {e}")
            return None

    async def _call_ocr_space(self, content: bytes) -> Optional[str]:
        """Call OCR.space API."""
        if not self.ocr_space_key:
            print("OCR.space API key not found.")
            return None
            
        try:
            url = "https://api.ocr.space/parse/image"
            payload = {
                'apikey': self.ocr_space_key,
                'language': 'eng',
                'OCREngine': '2' # Engine 2 is better for special characters
            }
            files = {
                'file': ('radar.png', content, 'image/png')
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, data=payload, files=files)
                result = response.json()
                
            if result.get("IsErroredOnProcessing"):
                print(f"OCR.space Error: {result.get('ErrorMessage')}")
                return None
                
            parsed_results = result.get("ParsedResults", [])
            if parsed_results:
                return parsed_results[0].get("ParsedText")
            return None
        except Exception as e:
            print(f"OCR.space Exception: {e}")
            return None

    async def _call_pytesseract(self, frame: np.ndarray) -> Optional[str]:
        """Call local Tesseract OCR engine."""
        if pytesseract is None:
            print("pytesseract is not installed. Skipping local OCR.")
            return None
            
        import shutil
        tesseract_cmd = shutil.which("tesseract")
        if not tesseract_cmd:
            if os.path.exists("/opt/homebrew/bin/tesseract"):
                tesseract_cmd = "/opt/homebrew/bin/tesseract"
            elif os.path.exists("/usr/local/bin/tesseract"):
                tesseract_cmd = "/usr/local/bin/tesseract"
                
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        else:
            print("Tesseract binary not found in PATH or standard locations.")
            return None
            
        try:
            import asyncio
            # frame is numpy array, pytesseract can handle it directly
            text = await asyncio.to_thread(pytesseract.image_to_string, frame)
            return text
        except Exception as e:
            print(f"pytesseract Exception: {e}")
            return None

    def _extract_timestamp_from_text(self, text: str) -> Optional[int]:
        """
        Parse text like "06 Jun 2026 09:30" or "2026-06-06 09:30:00"
        TMD radar typically has formats like "06/06/2026 09:30"
        """
        if not text:
            return None
            
        match = re.search(r'(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}(?::\d{2})?)', text)
        if match:
            date_str = match.group(1)
            time_str = match.group(2)
            try:
                if '/' in date_str:
                    day, month, year = map(int, date_str.split('/'))
                else:
                    year, month, day = map(int, date_str.split('-'))
                
                time_parts = list(map(int, time_str.split(':')))
                hour = time_parts[0]
                minute = time_parts[1]
                second = time_parts[2] if len(time_parts) > 2 else 0
                
                # TMD radar images typically write the time in UTC (e.g. 06/06/2026 15:30Z)
                # Even if the 'Z' is missed by OCR, we should treat it as UTC.
                dt_utc = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
                return int(dt_utc.timestamp())
            except Exception as e:
                print(f"OCR Parsing error: {e}")
        return None

    async def get_frame_timestamp(
        self,
        frame: np.ndarray,
        fallback_ts: Optional[int] = None,
        *,
        skip_hash_cache: bool = False,
    ) -> Optional[int]:
        """
        Check cache for the frame hash. If not found, run OCR fallback chain to extract timestamp.
        Returns the UTC timestamp integer.

        skip_hash_cache: when True, always run live OCR (used for image overlays so a stale
        hash-cache entry — e.g. a poll-time wall-clock fallback — cannot override the real
        TMD timestamp printed on the frame).
        """
        frame_hash = self._hash_frame(frame)
        if not skip_hash_cache:
            cached_ts = await self.repo.get_radar_timestamp_cache(frame_hash)
            if cached_ts is not None:
                return cached_ts

        png_bytes = self._frame_to_png_bytes(frame)
        ts = None
        
        # Hotfix (Issue #85): Bypass Cloud Vision and Gemini due to quotas/latency
        # Check quota for Cloud Vision
        # vision_allowed = await self.repo.check_and_increment_vision_quota(1000)
        
        # Fallback Chain 1: Google Cloud Vision (Bypassed)
        # if vision_allowed:
        #     print("Running OCR: Cloud Vision")
        #     text = await self._call_cloud_vision(png_bytes)
        #     ts = self._extract_timestamp_from_text(text)
        # else:
        #     print("Cloud Vision quota exceeded. Skipping to Gemini.")
        
        # Fallback Chain 2: Gemini (Bypassed)
        # if ts is None:
        #     print("Running OCR: Gemini")
        #     text = await self._call_gemini(png_bytes)
        #     ts = self._extract_timestamp_from_text(text)
            
        # Try Local Tesseract First
        if ts is None:
            print("Running OCR: Local Tesseract")
            text = await self._call_pytesseract(frame)
            ts = self._extract_timestamp_from_text(text)
            
        # Primary Engine: OCR.space (Issue #85)
        if ts is None:
            print("Running OCR: OCR.space (Hotfix Bypass)")
            text = await self._call_ocr_space(png_bytes)
            ts = self._extract_timestamp_from_text(text)
        
        # If all failed, use fallback_ts
        if ts is None and fallback_ts is not None:
            print("OCR Failed. Using fallback_ts")
            ts = fallback_ts
            
        if ts is not None:
            # Only cache successful OCR parses — never persist poll-time fallback values.
            if fallback_ts is None or ts != fallback_ts:
                await self.repo.set_radar_timestamp_cache(frame_hash, ts)

        return ts
