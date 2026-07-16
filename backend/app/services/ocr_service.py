import logging
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
from typing import Optional, List

logger = logging.getLogger(__name__)

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
        """Hash only the bottom timestamp crop for cache keying.

        Hashing the full frame caused false CACHE MISSes when cloud pixels
        shifted slightly between polls even though the TMD timestamp text
        (bottom 60 px) was identical — wastefully re-running OCR.

        Using the crop means: same timestamp text → same hash → CACHE HIT,
        regardless of cloud movement.  If timestamp_crop() geometry ever
        changes, bump the suffix so old hashes are automatically invalidated.
        """
        crop = self.timestamp_crop(frame)  # 800×60×3 ≈ 144 KB (vs 1.92 MB full)
        return hashlib.md5(crop.tobytes() + b"v3crop").hexdigest()


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
            from app.dependencies import get_http_client
            client = get_http_client()
            response = await client.post(url, data=payload, files=files, timeout=10.0)
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
            # Use PSM 6 (Assume a single uniform block of text) to drastically improve accuracy on cropped timestamp strips.
            text = await asyncio.to_thread(pytesseract.image_to_string, frame, config="--psm 6")
            return text
        except Exception as e:
            print(f"pytesseract Exception: {e}")
            return None

    def _extract_timestamp_from_text(self, text: str, *, _debug_hash: str = "") -> Optional[int]:
        """
        Parse text like "06 Jun 2026 09:30" or "2026-06-06 09:30:00"
        TMD radar typically has formats like "06/06/2026 09:30" or "2026-06-06 09:30:00"
        """
        if not text:
            return None

        # Clean text first: sometimes OCR mis-detects colons as spaces or other symbols,
        # e.g., "13 0004" instead of "13:00:04" or similar.
        # Let's try standard regex search first
        match = re.search(r'(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}(?::\d{2})?)', text)
        
        # If not found, look for space-separated time blocks after a date string: "YYYY-MM-DD HH MM SS"
        if not match:
            # Match date followed by 2 or 3 groups of digits (e.g. HH MM or HH MM SS)
            match_loose = re.search(r'(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\s+(\d{2})\s+(\d{2})(?:\s+(\d{2}))?', text)
            if match_loose:
                date_str = match_loose.group(1)
                h = match_loose.group(2)
                m = match_loose.group(3)
                s = match_loose.group(4) if match_loose.group(4) else "00"
                # Standardize time string format for parsing below
                time_str = f"{h}:{m}:{s}"
                match = match_loose
            else:
                return None
        else:
            date_str = match.group(1)
            time_str = match.group(2)

        if match:
            # Log the matched snippet and surrounding context so we can see
            # exactly what the OCR engine read and from which part of the text.
            ctx_start = max(0, match.start() - 30)
            ctx_end   = min(len(text), match.end() + 30)
            context   = repr(text[ctx_start:ctx_end])
            if _debug_hash:
                logger.debug(
                    f"[OCR] hash={_debug_hash}  regex_match={repr(match.group(0))}  "
                    f"pos={match.start()}  context={context}"
                )
            try:
                if '/' in date_str:
                    day, month, year = map(int, date_str.split('/'))
                else:
                    year, month, day = map(int, date_str.split('-'))

                # We clean up common OCR year errors: e.g. "2086" -> "2026"
                if year > 2050:
                    # If the year is way in the future (like 2086), it's likely an OCR error for 2026
                    year = 2026

                time_parts = list(map(int, time_str.split(':')))
                hour   = time_parts[0]
                minute = time_parts[1]
                second = time_parts[2] if len(time_parts) > 2 else 0

                # ⚠️  TIMEZONE ASSUMPTION: code treats the parsed time as UTC.
                # If TMD actually prints local BKK time on the image, stored
                # timestamps will be +7 h too large.  The DEBUG log below shows
                # both representations so a mis-assumption is immediately visible.
                dt_utc = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
                ts     = int(dt_utc.timestamp())
                if _debug_hash:
                    BKK = ZoneInfo("Asia/Bangkok")
                    bkk_str = datetime.fromtimestamp(ts, BKK).strftime("%Y-%m-%d %H:%M:%S")
                    logger.debug(
                        f"[OCR] hash={_debug_hash}  "
                        f"parsed_as_utc={date_str} {time_str}  "
                        f"stored_ts={ts}  "
                        f"→ if_UTC={date_str} {time_str} UTC  "
                        f"→ as_BKK={bkk_str} BKK"
                    )
                return ts
            except Exception as e:
                print(f"OCR Parsing error: {e}")
        return None

    def timestamp_crop(self, frame: np.ndarray) -> np.ndarray:
        """Bottom band where TMD prints the UTC date/time on radar images.

        TMD radar frames carry a bottom text strip such as:
            '1142KHO 2026-06-26 22:15:59 PPI Filtered Intensity...'
        Cropping the bottom 60 px makes this text large and high-contrast
        for OCR engines, replacing the old (incorrect) top-right crop.
        """
        h, w = frame.shape[:2]
        y1 = max(0, h - 60)   # bottom 60 px contains TMD timestamp text
        return frame[y1:h, 0:w].copy()

    async def _run_live_ocr(self, frame: np.ndarray) -> Optional[int]:
        """Run OCR engines on a frame/crop and return a parsed UTC timestamp, or None."""
        png_bytes = self._frame_to_png_bytes(frame)
        ts = None

        text = await self._call_pytesseract(frame)
        ts = self._extract_timestamp_from_text(text)

        if ts is None:
            text = await self._call_ocr_space(png_bytes)
            ts = self._extract_timestamp_from_text(text)

        return ts

    async def extract_parsed_timestamp(
        self,
        frame: np.ndarray,
        *,
        skip_hash_cache: bool = False,
        use_crop: bool = True,
    ) -> Optional[int]:
        """
        Return a UTC timestamp only when OCR successfully reads TMD date/time text.
        Never returns poll-time or wall-clock fallbacks.
        """
        frame_hash = self._hash_frame(frame)
        if not skip_hash_cache:
            cached_ts = await self.repo.get_radar_timestamp_cache(frame_hash)
            if cached_ts is not None:
                return cached_ts

        ts = await self._run_live_ocr(frame)
        if ts is None and use_crop:
            ts = await self._run_live_ocr(self.timestamp_crop(frame))

        if ts is not None:
            await self.repo.set_radar_timestamp_cache(frame_hash, ts)

        return ts

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
        BKK = ZoneInfo("Asia/Bangkok")
        frame_hash = self._hash_frame(frame)
        short_hash = frame_hash[:8]

        if not skip_hash_cache:
            cached_ts = await self.repo.get_radar_timestamp_cache(frame_hash)
            if cached_ts is not None:
                cached_dt = datetime.fromtimestamp(cached_ts, BKK).strftime("%H:%M:%S")
                logger.info(f"[OCR] hash={short_hash}  CACHE HIT  ts={cached_ts}  ({cached_dt} BKK)")
                return cached_ts

        logger.info(f"[OCR] hash={short_hash}  CACHE MISS  — running live OCR")

        # Try full frame first
        ts = None
        raw_text = None

        text_full = await self._call_pytesseract(frame)
        if text_full:
            ts = self._extract_timestamp_from_text(text_full, _debug_hash=short_hash)
            if ts:
                logger.info(
                    f"[OCR] hash={short_hash}  engine=tesseract(full)  "
                    f"parsed_utc={datetime.fromtimestamp(ts, timezone.utc).strftime('%H:%M:%S')} UTC  "
                    f"({datetime.fromtimestamp(ts, BKK).strftime('%H:%M:%S')} BKK)"
                )

        if ts is None:
            text_ocr = await self._call_ocr_space(self._frame_to_png_bytes(frame))
            if text_ocr:
                ts = self._extract_timestamp_from_text(text_ocr, _debug_hash=short_hash)
                if ts:
                    logger.info(
                        f"[OCR] hash={short_hash}  engine=ocr.space(full)  "
                        f"parsed_utc={datetime.fromtimestamp(ts, timezone.utc).strftime('%H:%M:%S')} UTC  "
                        f"({datetime.fromtimestamp(ts, BKK).strftime('%H:%M:%S')} BKK)"
                    )

        # Try crop if still None
        if ts is None:
            crop = self.timestamp_crop(frame)
            text_crop = await self._call_pytesseract(crop)
            if text_crop:
                ts = self._extract_timestamp_from_text(text_crop, _debug_hash=short_hash)
                if ts:
                    logger.info(
                        f"[OCR] hash={short_hash}  engine=tesseract(crop)  "
                        f"parsed_utc={datetime.fromtimestamp(ts, timezone.utc).strftime('%H:%M:%S')} UTC  "
                        f"({datetime.fromtimestamp(ts, BKK).strftime('%H:%M:%S')} BKK)"
                    )

        if ts is None:
            text_crop_ocr = await self._call_ocr_space(self._frame_to_png_bytes(self.timestamp_crop(frame)))
            if text_crop_ocr:
                ts = self._extract_timestamp_from_text(text_crop_ocr, _debug_hash=short_hash)
                if ts:
                    logger.info(
                        f"[OCR] hash={short_hash}  engine=ocr.space(crop)  "
                        f"parsed_utc={datetime.fromtimestamp(ts, timezone.utc).strftime('%H:%M:%S')} UTC  "
                        f"({datetime.fromtimestamp(ts, BKK).strftime('%H:%M:%S')} BKK)"
                    )

        # Fallback
        if ts is None and fallback_ts is not None:
            fallback_dt = datetime.fromtimestamp(fallback_ts, BKK).strftime("%H:%M:%S")
            logger.warning(f"[OCR] hash={short_hash}  ALL ENGINES FAILED  — using fallback_ts={fallback_ts} ({fallback_dt} BKK)")
            ts = fallback_ts

        if ts is not None:
            # Only cache successful OCR parses — never persist poll-time fallback values.
            if fallback_ts is None or ts != fallback_ts:
                await self.repo.set_radar_timestamp_cache(frame_hash, ts)

        return ts
