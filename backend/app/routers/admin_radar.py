# backend/app/routers/admin_radar.py

import cv2
import numpy as np
import httpx
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.database import AsyncSessionLocal
from app.repositories.radar import RadarStationRepository
from app.services.tmd_radar.auto_calibration import AutoCalibrationService
from app.services.tmd_radar_registry import radar_registry

router = APIRouter(tags=["Admin Radar"])

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session

class RadarPreviewRequest(BaseModel):
    code: str = Field(..., example="svp240")
    name: str = Field(..., example="Bangkok Suvarnabhumi (240km)")
    image_url: str = Field(..., example="https://weather.tmd.go.th/svp/svp240_latest.jpg")
    loop_page_url: Optional[str] = Field(default="")
    loop_gif_url: Optional[str] = Field(default="")
    lat: float = Field(..., example=13.6860)
    lng: float = Field(..., example=100.7486)
    radius_km: float = Field(default=240.0)
    # Optional manual override crop coordinates for fine-tuning
    crop_x: Optional[int] = None
    crop_y: Optional[int] = None
    crop_width: Optional[int] = None
    crop_height: Optional[int] = None

class RadarStationSaveRequest(BaseModel):
    code: str
    name: str
    static_image_url: str
    loop_page_url: Optional[str] = ""
    loop_gif_url: Optional[str] = ""
    center_lat: float
    center_lng: float
    radius_km: float = 240.0
    lat_max: float
    lng_min: float
    lat_min: float
    lng_max: float
    static_crop_x: int = 0
    static_crop_y: int = 0
    static_crop_width: int = 800
    static_crop_height: int = 800
    loop_crop_x: int = 0
    loop_crop_y: int = 0
    loop_crop_width: int = 680
    loop_crop_height: int = 680
    projection_type: str = "azimuthal"
    is_active: bool = True

@router.post("/preview")
async def preview_radar_calibration(req: RadarPreviewRequest):
    """
    Downloads radar image, detects/fine-tunes circle & crops, and returns Base64 preview image with bounding overlay.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(req.image_url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[preview] Download error for {req.image_url}: {e}")
        raise HTTPException(status_code=400, detail=f"Error downloading radar image: {str(e)}")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Radar image URL returned HTTP {resp.status_code}. URL: {req.image_url}"
        )

    image_data = resp.content
    if not image_data or len(image_data) < 100:
        raise HTTPException(status_code=400, detail=f"Downloaded image is empty or too small ({len(image_data)} bytes). URL may not be a direct image link.")

    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        # Check if response is HTML (common if URL redirects to page, not image)
        sample = image_data[:200].decode('utf-8', errors='replace')
        logger.error(f"[preview] Image decode failed. Content sample: {sample[:80]}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to decode image. The URL may return HTML instead of a JPEG/PNG. First bytes: {sample[:80]!r}"
        )

    service = AutoCalibrationService()
    circle = service.detect_radar_circle(img)

    if req.crop_x is not None and req.crop_y is not None and req.crop_width is not None and req.crop_height is not None:
        crop_info = {
            "static_crop_x": req.crop_x,
            "static_crop_y": req.crop_y,
            "static_crop_width": req.crop_width,
            "static_crop_height": req.crop_height,
            "loop_crop_x": req.crop_x,
            "loop_crop_y": req.crop_y,
            "loop_crop_width": req.crop_width,
            "loop_crop_height": req.crop_height
        }
    elif circle:
        crop_info = service.calculate_crops(img.shape, circle)
    else:
        crop_info = {
            "static_crop_x": 0, "static_crop_y": 0,
            "static_crop_width": img.shape[1], "static_crop_height": img.shape[0],
            "loop_crop_x": 0, "loop_crop_y": 0,
            "loop_crop_width": img.shape[1], "loop_crop_height": img.shape[0]
        }

    preview_img = service.draw_crop_preview(
        img,
        crop_info["static_crop_x"],
        crop_info["static_crop_y"],
        crop_info["static_crop_width"],
        crop_info["static_crop_height"],
        circle=circle
    )

    base64_preview = service.to_base64_jpeg(preview_img)

    snippet = service.generate_config_snippet(
        code=req.code,
        name=req.name,
        static_url=req.image_url,
        loop_page_url=req.loop_page_url or "",
        loop_gif_url=req.loop_gif_url or "",
        lat=req.lat,
        lng=req.lng,
        radius_km=req.radius_km,
        crop_info=crop_info
    )

    deg_offset = req.radius_km / 111.0
    calc_bbox = {
        "lat_max": round(req.lat + deg_offset, 2),
        "lng_min": round(req.lng - deg_offset, 2),
        "lat_min": round(req.lat - deg_offset, 2),
        "lng_max": round(req.lng + deg_offset, 2)
    }

    return {
        "code": req.code,
        "name": req.name,
        "circle_detected": circle is not None,
        "detected_circle": circle,
        "crop_info": crop_info,
        "calculated_bbox": calc_bbox,
        "preview_image_base64": base64_preview,
        "code_snippet": snippet
    }
@router.get("/presets")
async def get_radar_presets():
    """Returns catalog of known TMD radar station presets for Admin quick-select."""
    from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
    return KNOWN_TMD_RADAR_PRESETS

@router.post("/seed")
async def seed_radar_stations_to_db(db=Depends(get_async_db)):
    """Seeds validated TMD radar stations into DB (cleaning unvalidated ones first)."""
    from app.database import engine, Base
    import app.models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
    from sqlalchemy import delete
    from app.models import RadarStationModel

    # Delete existing stations to reset to validated list only
    valid_codes = [p["code"] for p in KNOWN_TMD_RADAR_PRESETS]
    await db.execute(delete(RadarStationModel).where(RadarStationModel.code.not_in(valid_codes)))
    await db.commit()

    repo = RadarStationRepository(db)
    count = 0
    for preset in KNOWN_TMD_RADAR_PRESETS:
        await repo.upsert_station(preset)
        count += 1
    radar_registry.invalidate_cache()
    return {"status": "ok", "message": f"Successfully synced DB to {count} validated radar stations."}

@router.get("/stations")
async def list_radar_stations(db=Depends(get_async_db)):
    from app.database import engine, Base
    import app.models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    repo = RadarStationRepository(db)
    stations = await repo.get_all_stations()
    return [
        {
            "code": s.code,
            "name": s.name,
            "static_image_url": s.static_image_url,
            "loop_page_url": s.loop_page_url,
            "loop_gif_url": s.loop_gif_url,
            "center_lat": s.center_lat,
            "center_lng": s.center_lng,
            "radius_km": s.radius_km,
            "bbox": {
                "lat_max": s.lat_max,
                "lng_min": s.lng_min,
                "lat_min": s.lat_min,
                "lng_max": s.lng_max
            },
            "static_crop": {
                "x": s.static_crop_x,
                "y": s.static_crop_y,
                "width": s.static_crop_width,
                "height": s.static_crop_height
            },
            "is_active": bool(s.is_active),
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        }
        for s in stations
    ]

@router.post("/stations")
async def save_radar_station(req: RadarStationSaveRequest, db=Depends(get_async_db)):
    repo = RadarStationRepository(db)
    saved = await repo.upsert_station(req.model_dump())
    radar_registry.invalidate_cache()
    return {"status": "ok", "code": saved.code, "message": "Radar station saved successfully to DB."}

@router.patch("/stations/{code}/toggle")
async def toggle_radar_station(code: str, is_active: bool, db=Depends(get_async_db)):
    repo = RadarStationRepository(db)
    updated = await repo.toggle_active(code, is_active)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Radar station {code} not found.")
    radar_registry.invalidate_cache()
    return {"status": "ok", "code": code, "is_active": bool(updated.is_active)}
