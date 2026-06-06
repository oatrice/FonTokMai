import cv2
import numpy as np
from typing import List, Tuple, Optional
from app.services.tmd_radar_config import STATIONS, DBZ_COLOR_MAPPING, IGNORED_COLORS

class TMDRadarProcessor:
    def __init__(self, station_code: str):
        self.station_code = station_code
        if station_code not in STATIONS:
            raise ValueError(f"Unknown station code: {station_code}")
        self.config = STATIONS[station_code]
        import os
        self.storage_dir = os.path.join(os.getcwd(), "backend", "tmp")

    def latlng_to_pixel(self, lat: float, lng: float) -> Tuple[Optional[int], Optional[int]]:
        """Converts geographical coordinates to image pixel coordinates based on bounding box."""
        bbox = self.config.bbox
        
        if not (bbox.lat_min <= lat <= bbox.lat_max and bbox.lng_min <= lng <= bbox.lng_max):
            return None, None
            
        # Check if we have calibration points (currently assuming 2 points for affine scale/translate)
        if hasattr(self.config, 'calibration_points') and self.config.calibration_points and len(self.config.calibration_points) >= 2:
            pts = list(self.config.calibration_points.items())
            (lat1, lng1), (px1, py1) = pts[0]
            (lat2, lng2), (px2, py2) = pts[1]
            
            # Calculate interpolated X
            x = px1 + (lng - lng1) * (px2 - px1) / (lng2 - lng1) if lng1 != lng2 else px1
            
            # Calculate interpolated Y (assuming lat decreases as Y increases)
            y = py1 + (lat1 - lat) * (py2 - py1) / (lat1 - lat2) if lat1 != lat2 else py1
            
            return int(x), int(y)

        # Fallback to standard linear interpolation using bounding box
        x_pct = (lng - bbox.lng_min) / (bbox.lng_max - bbox.lng_min)
        y_pct = (bbox.lat_max - lat) / (bbox.lat_max - bbox.lat_min)
        
        # Crop offsets
        x = int(x_pct * self.config.crop_width) + self.config.crop_x
        y = int(y_pct * self.config.crop_height) + self.config.crop_y
        
        return x, y

    def get_dbz_at_pixel(self, img: np.ndarray, x: int, y: int) -> float:
        """Reads the color at (x,y) and returns the corresponding dBZ value."""
        if x < 0 or x >= img.shape[1] or y < 0 or y >= img.shape[0]:
            return 0.0
            
        # OpenCV defaults to BGR
        pixel = img[y, x]
        if len(pixel) >= 3:
            b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])
        else:
            return 0.0
            
        color_tuple = (r, g, b)
        
        # Check ignored (perfect black)
        if color_tuple in IGNORED_COLORS:
            return 0.0
            
        # Find nearest color (due to GIF compression artifacts, colors are not exact)
        min_dist = float('inf')
        best_dbz = 0.0
        
        import math
        for known_color, dbz in DBZ_COLOR_MAPPING.items():
            dist = math.sqrt((r - known_color[0])**2 + (g - known_color[1])**2 + (b - known_color[2])**2)
            if dist < min_dist:
                min_dist = dist
                best_dbz = dbz
                
        # If the closest color is within a reasonable Euclidean distance (e.g., 90)
        if min_dist < 90:
            return best_dbz
            
        return 0.0

    def calculate_optical_flow(self, frames: List[np.ndarray]) -> np.ndarray:
        """
        Calculates dense optical flow using Farneback algorithm between the last two frames.
        frames: List of image arrays in RGB or Grayscale.
        Returns: Flow vector array of shape (H, W, 2)
        """
        if len(frames) < 2:
            raise ValueError("At least 2 frames required for optical flow")
            
        prev_img = frames[-2]
        curr_img = frames[-1]
        
        # Convert to Grayscale if they are color
        if len(prev_img.shape) == 3:
            prev_gray = cv2.cvtColor(prev_img, cv2.COLOR_RGB2GRAY)
        else:
            prev_gray = prev_img
            
        if len(curr_img.shape) == 3:
            curr_gray = cv2.cvtColor(curr_img, cv2.COLOR_RGB2GRAY)
        else:
            curr_gray = curr_img
            
        # Calculate dense optical flow by Farneback method
        # flow[y, x, 0] = dx
        # flow[y, x, 1] = dy
        flow = cv2.calcOpticalFlowFarneback(
            prev=prev_gray,
            next=curr_gray,
            flow=None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )
        return flow
        
    def get_flow_vector_at(self, flow: np.ndarray, x: int, y: int) -> Tuple[float, float]:
        """Returns the (dx, dy) velocity vector from optical flow array at given pixel."""
        if x < 0 or x >= flow.shape[1] or y < 0 or y >= flow.shape[0]:
            return 0.0, 0.0
            
        vx = float(flow[y, x, 0])
        vy = float(flow[y, x, 1])
        return vx, vy

    def calculate_growth_decay(self, prev_img: np.ndarray, curr_img: np.ndarray, x: int, y: int, radius: int = 10) -> float:
        """
        Calculates the growth or decay percentage of a rain cell around (x, y).
        Positive = Growth (Formation / Intensification)
        Negative = Decay (Dissipation / Weakening)
        
        It compares the sum of dBZ values in the region between the two frames.
        """
        prev_sum = 0.0
        curr_sum = 0.0
        count = 0
        
        # Look at a bounding box around (x,y)
        x_start = max(0, x - radius)
        x_end = min(curr_img.shape[1], x + radius)
        y_start = max(0, y - radius)
        y_end = min(curr_img.shape[0], y + radius)
        
        for iy in range(y_start, y_end):
            for ix in range(x_start, x_end):
                dbz_prev = self.get_dbz_at_pixel(prev_img, ix, iy)
                dbz_curr = self.get_dbz_at_pixel(curr_img, ix, iy)
                prev_sum += dbz_prev
                curr_sum += dbz_curr
                count += 1
                
        if count == 0:
            return 0.0
            
        if prev_sum == 0 and curr_sum == 0:
            return 0.0
        elif prev_sum == 0 and curr_sum > 0:
            return 100.0 # Formed from nothing
        elif prev_sum > 0 and curr_sum == 0:
            return -100.0 # Dissipated completely
            
        percent_change = ((curr_sum - prev_sum) / prev_sum) * 100.0
        return percent_change

    async def fetch_latest_image_bytes(self) -> Optional[bytes]:
        """Fetches the latest static radar image (Polling method)."""
        import httpx
        url = self.config.static_image_url
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.content
        except Exception:
            pass
        return None

    async def fetch_loop_gif_and_extract_frames(self) -> List[np.ndarray]:
        """Fetches the Loop.gif and extracts all frames as numpy arrays."""
        import httpx
        import imageio.v3 as iio
        
        url = getattr(self.config, 'loop_gif_url', self.config.static_image_url.replace('_latest.gif', 'Loop.gif').replace('_latest.jpg', 'Loop.gif'))
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    frames = iio.imread(response.content, index=None)
                    # iio.imread returns an array of shape (N, H, W, C), convert to list
                    return list(frames)
        except Exception as e:
            print(f"Error fetching loop gif: {e}")
        return []

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
        import time
        import os
        from google.cloud import storage
        
        timestamp = int(time.time())
        filename = f"radar/{self.station_code}/{self.station_code}_{timestamp}.gif"
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.appspot.com")
        
        # Use sync GCS upload (in a real high-throughput app we might use asyncio wrapper or threadpool)
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        blob.upload_from_string(image_bytes, content_type="image/gif")
        
        return filename
        
    async def cleanup_old_frames(self, max_age_hours: int = 3) -> int:
        """Deletes files in GCS that are older than max_age_hours."""
        import time
        import os
        from google.cloud import storage
        
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        cutoff_time = now - max_age_seconds
        
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.appspot.com")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        prefix = f"radar/{self.station_code}/"
        
        blobs = bucket.list_blobs(prefix=prefix)
        deleted_count = 0
        
        for blob in blobs:
            # We parse the timestamp from the filename "radar/kkn120/kkn120_1234567890.gif"
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

