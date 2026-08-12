import os
import asyncio
import time
import logging
import math
import io
import re
import cv2
import httpx
import numpy as np
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from zoneinfo import ZoneInfo
from typing import List, Tuple, Optional
from app.dependencies import get_repo_context
from app.services.ocr_service import OCRService
from app.services.tmd_radar_config import STATIONS, DBZ_COLOR_MAPPING, IGNORED_COLORS

logger = logging.getLogger(__name__)


def _load_thai_font(size: int) -> "ImageFont.FreeTypeFont":
    """Return the best available font that supports Thai characters.

    Priority order (Thai-capable → Latin fallbacks → PIL default):
      macOS  : Tahoma, Arial Unicode MS
      Linux  : Noto Sans Thai, Garuda, LiberationSans, DejaVu Sans
    """
    candidates = [
        # macOS Thai fonts
        "/System/Library/Fonts/Supplemental/Thonburi.ttc",
        "/System/Library/Fonts/ThonburiUI.ttc",
        "/System/Library/Fonts/Supplemental/Ayuthaya.ttf",
        "/System/Library/Fonts/Supplemental/Sathu.ttf",
        "/System/Library/Fonts/Supplemental/Tahoma.ttf",
        "/Library/Fonts/Tahoma.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        # Linux / Docker Thai fonts (install fonts-thai-tlwg or fonts-noto-core)
        "/usr/share/fonts/truetype/tlwg/Garuda.ttf",
        "/usr/share/fonts/truetype/tlwg/Loma.ttf",
        "/usr/share/fonts/truetype/thai-tlwg/Garuda.ttf",
        "/usr/share/fonts/truetype/thai-tlwg/Loma.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        # Generic Latin fallbacks
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


class TMDCacheMixin:

    async def fetch_station_timestamp_utc(self) -> Optional[datetime]:
        """Fetch the authoritative latest-frame timestamp from the TMD station PHP page."""
        import time
        prefix = self.station_code[:3]
        php_url = f"https://weather.tmd.go.th/{prefix}.php?t={int(time.time())}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(php_url)
                if resp.status_code == 200:
                    return self.parse_html_timestamp(resp.text)
        except Exception as e:
            logger.warning(f"[{self.station_code}] HTML timestamp fetch failed: {e}")
        return None

    async def fetch_latest_image_bytes(
        self,
        status_callback: Optional[Any] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[bytes]:
        """Fetches the latest static radar image (Polling method) with retries."""
        import time
        from app.dependencies import get_http_client
        client = get_http_client()
        url = f"{self.config.static_image_url}?t={int(time.time())}"

        for attempt in range(1, max_retries + 1):
            try:
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    return response.content
                else:
                    logger.warning(f"[{self.station_code}] Failed to fetch static image (attempt {attempt}/{max_retries}): HTTP {response.status_code}")
            except Exception as e:
                logger.warning(f"[{self.station_code}] Exception in fetch_latest_image_bytes (attempt {attempt}/{max_retries}): {e}")
                if status_callback and attempt < max_retries:
                    try:
                        st_name = getattr(self.config, 'name', self.station_code)
                        msg = f"⚠️ ไม่สามารถเชื่อมต่อเรดาร์ {st_name} [{self.station_code}] ได้ (พยายามใหม่รอบ {attempt + 1}/{max_retries})..."
                        res = status_callback(msg)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as _cb_err:
                        logger.warning(f"Status callback error: {_cb_err}")

            if attempt < max_retries:
                await asyncio.sleep(retry_delay)

        return None

    async def fetch_loop_gif_and_extract_frames(
        self,
        status_callback: Optional[Any] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Tuple[List[np.ndarray], Optional['datetime'], Optional[bytes]]:
        """Fetches the Loop.gif and extracts frames, the Last-Modified datetime, and raw GIF bytes."""
        import time
        loop_bytes = None
        dt = None

        url = self.config.loop_gif_url
        if not url:
            logger.warning(
                 f"[{self.station_code}] No loop_gif_url configured "
                 f"(station has no loop GIF from TMD). Returning empty frames."
            )
            return [], None, None

        loop_url = f"{url}?t={int(time.time())}"
        from app.dependencies import get_http_client
        client = get_http_client()

        for attempt in range(1, max_retries + 1):
            try:
                response = await client.get(loop_url, timeout=30.0)
                if response.status_code == 200:
                    loop_bytes = response.content
                    last_modified = response.headers.get("last-modified")
                    
                    try:
                        php_url = f"https://weather.tmd.go.th/{self.station_code[:3]}.php?t={int(time.time())}"
                        php_resp = await client.get(php_url, timeout=30.0)
                        if php_resp.status_code == 200:
                            dt = self.parse_html_timestamp(php_resp.text)
                    except Exception as e:
                        logger.warning(f"Error fetching exact timestamp from HTML: {e}")

                    if dt is None and last_modified:
                        try:
                            dt = datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                        except Exception as e:
                            logger.warning(f"Error parsing date: {e}")
                    break
                else:
                    logger.warning(
                        f"[{self.station_code}] Loop GIF URL returned HTTP {response.status_code} (attempt {attempt}/{max_retries})"
                    )
            except Exception as e:
                logger.warning(f"[{self.station_code}] Error fetching loop gif (attempt {attempt}/{max_retries}): {e}")
                if status_callback and attempt < max_retries:
                    try:
                        st_name = getattr(self.config, 'name', self.station_code)
                        msg = f"⚠️ ไม่สามารถดึงภาพ Loop เรดาร์ {st_name} [{self.station_code}] ได้ (พยายามใหม่รอบ {attempt + 1}/{max_retries})..."
                        res = status_callback(msg)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as _cb_err:
                        logger.warning(f"Status callback error: {_cb_err}")

            if attempt < max_retries and not loop_bytes:
                await asyncio.sleep(retry_delay)

                
        if loop_bytes:
            # Validate magic bytes: TMD server sometimes returns non-GIF content
            # (HTML error pages, empty bodies) which causes Pillow/OpenCV to crash.
            if not (loop_bytes[:6] in (b"GIF87a", b"GIF89a")):
                logger.warning(
                    f"[{self.station_code}] Loop GIF bytes are not a valid GIF image "
                    f"(magic={loop_bytes[:6]!r}, size={len(loop_bytes)}). Skipping frame extraction."
                )
                return [], None, None

            try:
                img = Image.open(io.BytesIO(loop_bytes))
                frames = []
                for frame in ImageSequence.Iterator(img):
                    frames.append(np.array(frame.copy().convert("RGB")))

                if frames:
                    target_h, target_w = frames[0].shape[:2]
                    normalized_frames = []
                    for frame in frames:
                        if frame.shape[:2] != (target_h, target_w):
                            frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
                        normalized_frames.append(frame)
                    frames = normalized_frames
                    
                # Optimize memory: keep only the last 12 frames (approx 3 hours of radar data)
                # to prevent OOM spikes during downstream high-res GIF generation.
                if len(frames) > 12:
                    frames = frames[-12:]
                    
                try:
                    ocr_svc = OCRService()
                    if len(frames) > 0:
                        fallback_ts = int(dt.timestamp()) if dt else int(time.time())
                        ts = await ocr_svc.get_frame_timestamp(frames[-1], fallback_ts=fallback_ts)
                        if ts is not None:
                            dt = datetime.fromtimestamp(ts, timezone.utc)
                except Exception as e:
                    logger.warning(f"[{self.station_code}] Error in OCR timestamp extraction: {e}")

                return frames, dt, loop_bytes
            except Exception as e:
                logger.error(f"[{self.station_code}] Error processing loop gif: {e}")
        return [], None, None

    async def fetch_loop_history_bytes(self) -> List[bytes]:
        """
        Fetches the history of images from the loop page.
        This is a stub. Real implementation requires scraping the loop.php HTML.
        For MVP, we just try to fetch the latest static image as history.
        """
        # TODO: Implement actual HTML scraping of self.config.loop_page_url
        # For now, return an empty list to fallback to polling
        return []

    async def save_polled_frame(self, image_bytes: bytes) -> str:
        """Saves a polled image byte sequence to Google Cloud Storage with a timestamp."""
        
        timestamp = int(time.time())
        filename = f"radar/{self.station_code}/{self.station_code}_{timestamp}.gif"
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.firebasestorage.app")
        
        # Use sync GCS upload with asyncio.to_thread
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        import asyncio
        await asyncio.to_thread(blob.upload_from_string, image_bytes, content_type="image/gif")
        
        return filename
        
    async def cleanup_old_frames(self, max_age_hours: int = 3) -> int:
        """Deletes files in GCS that are older than max_age_hours."""
        import asyncio
        
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        cutoff_time = now - max_age_seconds
        
        def _delete_sync():
            bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.firebasestorage.app")
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            prefix = f"radar/{self.station_code}/"
            
            blobs = bucket.list_blobs(prefix=prefix)
            deleted_count = 0
            
            for blob in blobs:
                try:
                    base_name = blob.name.split("/")[-1]
                    ts_str = base_name.replace(f"{self.station_code}_", "").replace(".gif", "")
                    blob_ts = int(ts_str)
                    if blob_ts < cutoff_time:
                        blob.delete()
                        deleted_count += 1
                except Exception:
                    pass
            return deleted_count
            
        return await asyncio.to_thread(_delete_sync)

    async def update_radar_cache(self, force: bool = False, status_callback: Optional[Any] = None) -> dict:
        """
        Fetch from TMD and update cache if new image is available or if cache is stale.
        This encapsulates the fetching, OCR, cache validation, loop GIF fallback, and database persistence.
        """
        import os
        import time
        import cv2
        import numpy as np
        from datetime import datetime, timezone
        from app.dependencies import get_repo_context
        from app.services.ocr_service import OCRService

        station = self.station_code
        result = {"station": station, "updated": False, "error": None}
        now_ts = int(datetime.now(timezone.utc).timestamp())

        # 1. Check cache first (for smart polling skip)
        async with get_repo_context() as repo:
            cache = await repo.get_latest_radar_cache(station)
            
        frames = cache.get("frames", []) if cache else []
        latest_ts = frames[0]["timestamp"] if frames else 0
        last_gif_fallback_time = cache.get("last_gif_fallback_time", 0.0) if cache else 0.0

        # Sanity-check: if latest_ts is in the future (e.g. corrupted wall-clock fallback),
        # reset to 0 so a fresh valid OCR timestamp can replace it.
        if latest_ts > now_ts + 300:
            logger.warning(
                f"[{station}] ⚠️ Firestore latest_ts={latest_ts} is in the future "
                f"(now={now_ts}, delta={latest_ts - now_ts}s) — resetting to 0 to unblock cache"
            )
            latest_ts = 0

        # Skip fetch if cache is fresh, has full 6 frames, and force is False
        if not force and len(frames) >= 6 and (now_ts - latest_ts) < 1200:
            logger.debug(f"[{station}] Cache is fresh (latest_ts={latest_ts}, age={now_ts - latest_ts}s). Skipping update.")
            result["reason"] = "fresh"
            return result

        # 2. Fetch static image bytes
        static_bytes = await self.fetch_latest_image_bytes(status_callback=status_callback)
        
        ocr_svc = OCRService()
        ts = None
        frame = None
        np_arr = None

        if static_bytes:
            np_arr = np.frombuffer(static_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            logger.info(f"[{station}] ✅ Static fetch OK — {len(static_bytes):,} bytes, shape={frame.shape[:2]}")
            ts = await ocr_svc.get_frame_timestamp(frame, fallback_ts=now_ts)
            ocr_ok = ts is not None and ts != now_ts
            if not ocr_ok:
                logger.warning(f"[{station}] ⚠️ OCR failed on static image — frame will NOT be saved directly, forcing GIF fallback check")
                ts = None
        else:
            logger.warning(f"[{station}] ❌ Static fetch FAILED — will attempt GIF fallback if enabled")

        needs_fallback = False
        fallback_reason = ""

        # Check fallback settings
        async with get_repo_context() as repo:
            sys_settings = await repo.get_system_settings()
        enable_fallback_db = sys_settings.get("enable_gif_fallback", True)
        enable_fallback_env = os.environ.get("ENABLE_TMD_GIF_FALLBACK", "true").lower() == "true"
        enable_fallback = enable_fallback_db and enable_fallback_env

        if enable_fallback:
            if frames:
                gap_to_now = (now_ts - latest_ts) / 60.0
                is_static_outdated = False
                if ts:
                    static_age_minutes = (now_ts - ts) / 60.0
                    if static_age_minutes > 120.0:
                        is_static_outdated = True
                        
                if gap_to_now > 60.0 and (now_ts - last_gif_fallback_time) > 1800.0:
                    needs_fallback = True
                    fallback_reason = f"Static dead for {gap_to_now:.1f}m"
                elif is_static_outdated and (now_ts - last_gif_fallback_time) > 1800.0:
                    needs_fallback = True
                    fallback_reason = f"Static image is outdated by {static_age_minutes:.1f}m"
                elif ts and (ts - latest_ts) > 1800.0:
                    needs_fallback = True
                    fallback_reason = f"Large time gap detected ({int((ts - latest_ts)/60)}m) between {latest_ts} and {ts}"
        if enable_fallback and not static_bytes and not frames:
            needs_fallback = True
            fallback_reason = "Static fetch failed and cache empty"
        elif enable_fallback and static_bytes and not ts:
            if (now_ts - last_gif_fallback_time) > 300.0:
                needs_fallback = True
                fallback_reason = "Static fetch OCR failed"

        if enable_fallback and not needs_fallback and len(frames) < 6:
            if force or (now_ts - last_gif_fallback_time) > 1800.0:
                needs_fallback = True
                fallback_reason = f"Cache has <6 frames ({len(frames)})"

        # If not force, not outdated/dead and unchanged, return early
        if not force and not needs_fallback and ((ts and ts <= latest_ts) or not static_bytes):
            logger.debug(f"[{station}] Image unchanged or unavailable (ts {ts}). Skipping.")
            result["reason"] = "unchanged"
            return result

        new_url = None
        if ts and ts > latest_ts:
            logger.info(f"[{station}] 🆕 New frame detected (ts={ts} > latest={latest_ts}) — saving to GCS")
            
            # ── Option B: Normalize and Crop ────────────────────────────────
            # Scale to standard 800px max dimension so Admin crop coords map 1:1
            max_dim = 800
            h, w = frame.shape[:2]
            if h > max_dim or w > max_dim:
                scale = max_dim / float(max(h, w))
                new_w = int(w * scale)
                new_h = int(h * scale)
                frame_to_save = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            else:
                frame_to_save = frame
                
            scy = self.config.static_crop_y
            scx = self.config.static_crop_x
            sch = self.config.static_crop_height
            scw = self.config.static_crop_width
            
            if (scy + sch <= frame_to_save.shape[0]) and (scx + scw <= frame_to_save.shape[1]):
                frame_to_save = frame_to_save[scy:scy + sch, scx:scx + scw]
                
            is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(frame_to_save, cv2.COLOR_RGB2BGR))
            if is_success:
                new_url = await self.save_polled_frame(buffer.tobytes())
            else:
                new_url = await self.save_polled_frame(static_bytes)
            # ────────────────────────────────────────────────────────────────
            
            frames.insert(0, {"url": new_url, "timestamp": ts})
            frames = sorted(frames, key=lambda f: f["timestamp"])
            frames.reverse() # newest first

        if needs_fallback:
            logger.warning(f"[{station}] GIF fallback triggered: {fallback_reason}")
            last_gif_fallback_time = now_ts
            fallback_frames_data, fallback_dt, loop_bytes = await self.fetch_loop_gif_and_extract_frames()
            if fallback_frames_data and len(fallback_frames_data) >= 2:
                logger.info(f"[{station}] 🌀 GIF fallback: fetched {len(fallback_frames_data)} frames")
                recent_fallback = fallback_frames_data[-6:]
                recent_fallback.reverse()

                new_frames_list = []
                base_ts = ts if ts else now_ts
                # Crop parameters for loop frames
                lcy = self.config.loop_crop_y
                lcx = self.config.loop_crop_x
                lch = self.config.loop_crop_height
                lcw = self.config.loop_crop_width
                for i, f_img in enumerate(recent_fallback):
                    f_ts = await ocr_svc.get_frame_timestamp(f_img, fallback_ts=base_ts - i * 900)
                    # ── Crop to loop_crop region before saving ──────────────────
                    # Raw GIF frames are full-image (e.g. 1920×1600). Saving them
                    # uncropped causes GPS pin coordinates (computed from 728×728
                    # crop config) to be wildly misaligned when frames are loaded
                    # back from Firestore. Crop first so stored frames match config.
                    # ── Option B: Normalize to 800px max before crop ──────────
                    max_dim = 800
                    h, w = f_img.shape[:2]
                    if h > max_dim or w > max_dim:
                        scale = max_dim / float(max(h, w))
                        new_w = int(w * scale)
                        new_h = int(h * scale)
                        f_norm = cv2.resize(f_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    else:
                        f_norm = f_img

                    if (lcy + lch <= f_norm.shape[0]) and (lcx + lcw <= f_norm.shape[1]):
                        f_save = f_norm[lcy:lcy + lch, lcx:lcx + lcw]
                        logger.debug(
                            f"[{station}] GIF fallback crop: raw={f_img.shape[:2]} "
                            f"→ cropped={f_save.shape[:2]} (y={lcy}:{lcy+lch}, x={lcx}:{lcx+lcw})"
                        )
                    else:
                        # Crop region exceeds frame bounds — save full frame as fallback
                        logger.warning(
                            f"[{station}] GIF frame too small to crop: {f_norm.shape[:2]} "
                            f"< crop ({lch},{lcw}). Saving full frame."
                        )
                        f_save = f_norm
                    is_success, buffer = cv2.imencode(".png", cv2.cvtColor(f_save, cv2.COLOR_RGB2BGR))
                    if is_success:
                        f_url = await self.save_polled_frame(buffer.tobytes())
                        new_frames_list.append({"url": f_url, "timestamp": f_ts})

                if new_frames_list:
                    gif_newest_ts = new_frames_list[0]["timestamp"]
                    current_newest_ts = frames[0]["timestamp"] if frames else 0
                    is_bootstrap = fallback_reason.startswith("Cache has <") or fallback_reason == "Cache is empty"

                    if is_bootstrap:
                        if ts and ts > gif_newest_ts:
                            new_frames_list.insert(0, {"url": new_url, "timestamp": ts})
                        frames = new_frames_list
                    elif gif_newest_ts > current_newest_ts + 300:
                        logger.info(f"[{station}] GIF data is newer. Adopting GIF frames.")
                        if ts and ts > gif_newest_ts:
                            new_frames_list.insert(0, {"url": new_url, "timestamp": ts})
                        frames = new_frames_list
                    else:
                        logger.warning(f"[{station}] GIF data is NOT newer. Discarding GIF.")

        frames = frames[:6]
        
        async with get_repo_context() as repo:
            await repo.set_latest_radar_cache(
                station_code=station,
                frames=frames,
                last_gif_fallback_time=last_gif_fallback_time
            )
        logger.info(f"Updated cache for {station} with {len(frames)} frames, latest ts {ts}")

        # Cleanup old frames
        deleted = await self.cleanup_old_frames(max_age_hours=3)
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old frames for {station}")

        result["updated"] = True
        return result


    async def decode_static_frame(self) -> Optional[np.ndarray]:
        """Download and decode the latest static radar image as an RGB numpy frame."""
        static_bytes = await self.fetch_latest_image_bytes()
        if not static_bytes:
            return None
        arr = np.frombuffer(static_bytes, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    @staticmethod
    def parse_html_timestamp(html: str) -> Optional[datetime]:
        """Parse TMD station PHP embed version string, e.g. v=250626_1030 → UTC datetime."""
        match = re.search(r'v=(\d{6})_(\d{4})', html)
        if not match:
            return None
        date_str = match.group(1)
        time_str = match.group(2)
        year = int('20' + date_str[0:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        hour = int(time_str[0:2])
        minute = int(time_str[2:4])
        bkk_tz = ZoneInfo('Asia/Bangkok')
        dt_bkk = datetime(year, month, day, hour, minute, tzinfo=bkk_tz)
        return dt_bkk.astimezone(timezone.utc)
