import pytest
import time
import asyncio
from datetime import datetime, timezone
import numpy as np

from app.services.tmd_radar.cache_manager import RadarFrameCache, RadarCacheEntry

def test_cache_set_and_get():
    cache = RadarFrameCache()
    frames = [np.zeros((10, 10))]
    now = datetime.now(timezone.utc)
    
    entry = cache.set(
        station_code="bkk120",
        frames=frames,
        last_modified_dt=now,
        flow=None,
        frame_source="static_cache",
        data_gap_minutes=15.0,
        frame_timestamps=[1234567890],
        frame_urls=["http://example.com/frame.png"]
    )
    
    assert isinstance(entry, RadarCacheEntry)
    
    cached_entry = cache.get("bkk120")
    assert cached_entry is not None
    assert cached_entry.frame_source == "static_cache"
    assert cached_entry.data_gap_minutes == 15.0
    assert cached_entry.age_seconds >= 0

def test_cache_invalidate_and_clear():
    cache = RadarFrameCache()
    
    cache.set("bkk120", [], datetime.now(), None, "src", 15.0, [], [])
    cache.set("kkn240", [], datetime.now(), None, "src", 15.0, [], [])
    
    assert len(cache.get_all_stations()) == 2
    
    cache.invalidate("bkk120")
    assert cache.get("bkk120") is None
    assert cache.get("kkn240") is not None
    
    cache.clear()
    assert len(cache.get_all_stations()) == 0

@pytest.mark.asyncio
async def test_cache_locks():
    cache = RadarFrameCache()
    lock1 = cache.get_lock("bkk120")
    lock2 = cache.get_lock("bkk120")
    lock3 = cache.get_lock("kkn240")
    
    assert lock1 is lock2
    assert lock1 is not lock3
