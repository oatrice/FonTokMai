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

    def latlng_to_pixel(self, lat: float, lng: float, is_loop: bool = True) -> Tuple[Optional[int], Optional[int]]:
        """Converts geographical coordinates to image pixel coordinates based on bounding box."""
        bbox = self.config.bbox
        if lat > bbox.lat_max or lat < bbox.lat_min or lng < bbox.lng_min or lng > bbox.lng_max:
            return None, None
            
        # Select crop parameters based on image type
        crop_x = self.config.loop_crop_x if is_loop else self.config.static_crop_x
        crop_y = self.config.loop_crop_y if is_loop else self.config.static_crop_y
        crop_width = self.config.loop_crop_width if is_loop else self.config.static_crop_width
        crop_height = self.config.loop_crop_height if is_loop else self.config.static_crop_height
        
        # Check if we have affine calibration points
        if self.config.calibration_points and len(self.config.calibration_points) >= 3:
            # Full affine transformation (implemented in future PRs if needed)
            pass
            
        # Fallback to standard linear interpolation using bounding box
        x_pct = (lng - bbox.lng_min) / (bbox.lng_max - bbox.lng_min)
        y_pct = (bbox.lat_max - lat) / (bbox.lat_max - bbox.lat_min)
        
        # Crop offsets
        x = int(x_pct * crop_width) + crop_x
        y = int(y_pct * crop_height) + crop_y
        
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

    def extrapolate_rain_at_pixel(self, img: np.ndarray, flow: np.ndarray, px: int, py: int, steps: int) -> float:
        """
        Uses Semi-Lagrangian backward tracking to find the dBZ value that will arrive at (px, py) in 'steps' time intervals.
        Each step corresponds to the time difference between the frames used to compute the optical flow (e.g. 15 mins).
        Positive steps mean predicting into the future.
        """
        if steps == 0:
            return self.get_dbz_at_pixel(img, px, py)
            
        # Get the flow vector at the target pixel
        vx, vy = self.get_flow_vector_at(flow, px, py)
        
        # Calculate source pixel (backward tracking)
        # Assuming linear constant velocity over the steps
        src_x = int(round(px - (vx * steps)))
        src_y = int(round(py - (vy * steps)))
        
        # Clamp to image boundaries
        src_x = max(0, min(img.shape[1] - 1, src_x))
        src_y = max(0, min(img.shape[0] - 1, src_y))
        
        # Get the dbz from the source pixel in the current image
        dbz = self.get_dbz_at_pixel(img, src_x, src_y)
        
        return float(dbz)

    def get_wind_speed_kmh(self, flow: np.ndarray, px: int, py: int) -> float:
        """
        Converts the optical flow vector (px/15min) into wind speed (km/h) 
        based on the geographic bounding box size.
        """
        import math
        vx, vy = self.get_flow_vector_at(flow, px, py)
        pixel_speed_15m = math.sqrt(vx**2 + vy**2)
        
        # Calculate km per pixel (approx 1 degree = 111 km)
        lon_diff = self.config.bbox.lng_max - self.config.bbox.lng_min
        width_km = lon_diff * 111.0
        km_per_pixel = width_km / max(1, self.config.crop_width)
        
        km_per_15m = pixel_speed_15m * km_per_pixel
        km_per_h = km_per_15m * 4.0
        
        return float(km_per_h)

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
        """Fetches the Loop.gif and extracts all frames as numpy arrays using PIL for proper GIF coalescing."""
        import httpx
        from PIL import Image, ImageSequence
        import io
        
        url = getattr(self.config, 'loop_gif_url', self.config.static_image_url.replace('_latest.gif', 'Loop.gif').replace('_latest.jpg', 'Loop.gif'))
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    img = Image.open(io.BytesIO(response.content))
                    frames = []
                    # PIL handles GIF frame disposal properly (coalescing delta frames)
                    for frame in ImageSequence.Iterator(img):
                        frames.append(np.array(frame.copy().convert("RGB")))
                    return frames
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

