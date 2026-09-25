import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np


@dataclass
class RadarCacheEntry:
    """Represents a cached state of radar frames and optical flow for a station."""
    frames: List[np.ndarray]
    last_modified_dt: datetime
    cache_timestamp: float
    flow: Optional[np.ndarray]
    frame_source: str
    data_gap_minutes: float
    frame_timestamps: List[int]
    frame_urls: List[str]

    @property
    def age_seconds(self) -> float:
        """Returns how long this entry has been in the cache."""
        return time.time() - self.cache_timestamp


class RadarFrameCache:
    """
    Manages the global in-memory cache for TMD Radar frames and optical flow.
    Replaces the legacy _GLOBAL_TMD_CACHE dict and _GLOBAL_TMD_LOCKS.
    """
    def __init__(self):
        self._cache: Dict[str, RadarCacheEntry] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def get(self, station_code: str) -> Optional[RadarCacheEntry]:
        return self._cache.get(station_code)

    def set(
        self,
        station_code: str,
        frames: List[np.ndarray],
        last_modified_dt: datetime,
        flow: Optional[np.ndarray],
        frame_source: str,
        data_gap_minutes: float,
        frame_timestamps: List[int],
        frame_urls: List[str]
    ) -> RadarCacheEntry:
        entry = RadarCacheEntry(
            frames=frames,
            last_modified_dt=last_modified_dt,
            cache_timestamp=time.time(),
            flow=flow,
            frame_source=frame_source,
            data_gap_minutes=data_gap_minutes,
            frame_timestamps=frame_timestamps,
            frame_urls=frame_urls,
        )
        self._cache[station_code] = entry
        return entry

    def invalidate(self, station_code: str):
        self._cache.pop(station_code, None)

    def clear(self):
        self._cache.clear()
        
    def get_all_stations(self) -> List[str]:
        return list(self._cache.keys())

    def get_lock(self, station_code: str) -> asyncio.Lock:
        """Get or create an async lock for a specific station."""
        if station_code not in self._locks:
            self._locks[station_code] = asyncio.Lock()
        return self._locks[station_code]

# Global singleton instance
radar_cache = RadarFrameCache()
