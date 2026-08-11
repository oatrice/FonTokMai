# backend/tests/test_chainat_loop.py

import pytest
import httpx
from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
from app.services.tmd_radar_config import STATIONS

def test_chainat_loop_url_configured_correctly():
    """Verify Chainat (chn) loop_gif_url is configured as chnloop.gif in catalog and config."""
    preset = next((p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "chn"), None)
    assert preset is not None
    assert preset["loop_gif_url"] == "https://weather.tmd.go.th/chn/chnloop.gif"

    assert "chn" in STATIONS
    assert STATIONS["chn"].loop_gif_url == "https://weather.tmd.go.th/chn/chnloop.gif"

@pytest.mark.asyncio
async def test_chainat_loop_gif_live_fetch():
    """Integration test: live fetch https://weather.tmd.go.th/chn/chnloop.gif and verify valid GIF bytes."""
    url = "https://weather.tmd.go.th/chn/chnloop.gif"
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(url)
        assert res.status_code == 200, f"Expected HTTP 200 for {url}, got {res.status_code}"
        assert len(res.content) > 10_000, f"Expected GIF size > 10KB, got {len(res.content)} bytes"
        assert res.content[:3] == b"GIF", "Downloaded content is not a valid GIF file"
