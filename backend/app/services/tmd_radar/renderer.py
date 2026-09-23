from typing import Protocol, List, Dict, Any, Optional
from datetime import datetime
import numpy as np

class RadarRenderer(Protocol):
    def generate_radar_tracking_image(
        self,
        curr_frame: np.ndarray,
        user_px: int,
        user_py: int,
        approaching_clouds: list,
        tmd_time_utc: datetime,
        all_clusters: list,
        predictions: list,
        is_tracking_mode: bool,
        show_trajectory: bool,
        show_labels: bool,
        time_offset_min: float,
        locked_target_id: Optional[str] = None,
        locked_target_cx: Optional[int] = None,
        locked_target_cy: Optional[int] = None,
        cluster_dist_approaching: float = 10,
        cluster_dist_ambient: float = 6,
        historical_vectors: list = None
    ) -> Optional[bytes]: ...

    def generate_timeline_image(
        self,
        predictions: list,
        location_name: Optional[str] = None
    ) -> Optional[bytes]: ...

    def generate_multiframe_analysis_image(
        self,
        frames: List[np.ndarray],
        flow: np.ndarray,
        user_px: int,
        user_py: int,
        clusters: list,
        processor: Any,
        tmd_time_utc: datetime,
        gap_min: float,
        frame_timestamps: list
    ) -> Optional[bytes]: ...
