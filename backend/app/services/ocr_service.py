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
    import google.generativeai as genai
except ImportError:
    genai = None

from app.repositories.firestore import FirestoreLocationRepository

class OCRService:
    def __init__(self):
        self.repo = FirestoreLocationRepository()
        
        # Initialize Gemini API if key is present and package is installed
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        if self.gemini_key and genai is not None:
            genai.configure(api_key=self.gemini_key)
            
        self.ocr_space_key = os.environ.get("OCR_SPACE_API_KEY")

    def _hash_frame(self, frame: np.ndarray) -> str:
        """Create a fast MD5 hash of the numpy frame."""
        return hashlib.md5(frame.tobytes()).hexdigest()

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
            # We use synchronous client wrapped in a way or just synchronous block 
            # since Cloud Vision python client has async support in some versions,
            # but standard `vision.ImageAnnotatorClient()` might be sync.
            # Using ImageAnnotatorAsyncClient if available:
            client = vision.ImageAnnotatorAsyncClient()
            image = vision.Image(content=content)
            response = await client.text_detection(image=image)
            
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
        """Call Gemini 1.5 Flash to extract text."""
        if genai is None:
            print("Gemini API package not installed. Skipping.")
            return None
            
        if not self.gemini_key:
            print("Gemini API key not found.")
            return None
            
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Create a dictionary suitable for gemini inputs
            image_part = {
                "mime_type": "image/png",
                "data": content
            }
            prompt = "Extract all the text you can see in this radar image. Pay special attention to timestamps or dates."
            
            # Since genai sdk is mostly sync, we could run it in an executor or use generate_content_async
            # Newer SDK supports generate_content_async
            response = await model.generate_content_async([prompt, image_part])
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
            
            async with httpx.AsyncClient(timeout=30.0) as client:
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
                
                bkk_tz = ZoneInfo('Asia/Bangkok')
                dt_bkk = datetime(year, month, day, hour, minute, second, tzinfo=bkk_tz)
                return int(dt_bkk.astimezone(timezone.utc).timestamp())
            except Exception as e:
                print(f"OCR Parsing error: {e}")
        return None

    async def get_frame_timestamp(self, frame: np.ndarray, fallback_ts: Optional[int] = None) -> Optional[int]:
        """
        Check cache for the frame hash. If not found, run OCR fallback chain to extract timestamp.
        Returns the UTC timestamp integer.
        """
        frame_hash = self._hash_frame(frame)
        cached_ts = await self.repo.get_radar_timestamp_cache(frame_hash)
        if cached_ts is not None:
            return cached_ts

        png_bytes = self._frame_to_png_bytes(frame)
        ts = None
        
        # Fallback Chain 1: Google Cloud Vision
        print("Running OCR: Cloud Vision")
        text = await self._call_cloud_vision(png_bytes)
        ts = self._extract_timestamp_from_text(text)
        
        # Fallback Chain 2: Gemini
        if ts is None:
            print("Running OCR: Gemini")
            text = await self._call_gemini(png_bytes)
            ts = self._extract_timestamp_from_text(text)
            
        # Fallback Chain 3: OCR.space
        if ts is None:
            print("Running OCR: OCR.space")
            text = await self._call_ocr_space(png_bytes)
            ts = self._extract_timestamp_from_text(text)
        
        # If all failed, use fallback_ts
        if ts is None and fallback_ts is not None:
            print("OCR Failed. Using fallback_ts")
            ts = fallback_ts
            
        if ts is not None:
            # Cache the result
            await self.repo.set_radar_timestamp_cache(frame_hash, ts)
        
        return ts
