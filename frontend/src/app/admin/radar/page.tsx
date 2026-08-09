"use client";

import React, { useState, useEffect, useRef } from "react";

interface Station {
  code: string;
  name: string;
  static_image_url: string;
  center_lat: number;
  center_lng: number;
  radius_km: number;
  static_crop: { x: number; y: number; width: number; height: number };
  is_active: boolean;
}

interface Preset {
  code: string;
  name: string;
  static_image_url: string;
  center_lat: number;
  center_lng: number;
  radius_km: number;
  static_crop_x: number;
  static_crop_y: number;
  static_crop_width: number;
  static_crop_height: number;
}

export default function AdminRadarPage() {
  const [stations, setStations] = useState<Station[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);

  const [code, setCode] = useState("svp240");
  const [name, setName] = useState("Bangkok Suvarnabhumi (240km)");
  const [imageUrl, setImageUrl] = useState("https://weather.tmd.go.th/svp/svp240_latest.jpg");
  const [lat, setLat] = useState(13.6860);
  const [lng, setLng] = useState(100.7486);
  const [radiusKm, setRadiusKm] = useState(240.0);

  // Crop Controls
  const [cropX, setCropX] = useState<number | null>(null);
  const [cropY, setCropY] = useState<number | null>(null);
  const [cropW, setCropW] = useState<number | null>(null);
  const [cropH, setCropH] = useState<number | null>(null);

  const [previewB64, setPreviewB64] = useState<string | null>(null);
  const [calculatedBbox, setCalculatedBbox] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  // Mouse Drag & Canvas Overlay State
  const imgRef = useRef<HTMLImageElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [currentDragBox, setCurrentDragBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  const fetchStations = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/admin/radar/stations`);
      if (res.ok) {
        const data = await res.json();
        setStations(data);
      }
    } catch (err) {
      console.error("Failed to fetch stations", err);
    }
  };

  const fetchPresets = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/admin/radar/presets`);
      if (res.ok) {
        const data = await res.json();
        setPresets(data);
      }
    } catch (err) {
      console.error("Failed to fetch presets", err);
    }
  };

  useEffect(() => {
    fetchStations();
    fetchPresets();
  }, []);

  const handleSelectPreset = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedCode = e.target.value;
    if (!selectedCode) return;

    const preset = presets.find((p) => p.code === selectedCode);
    if (preset) {
      setCode(preset.code);
      setName(preset.name);
      setImageUrl(preset.static_image_url);
      setLat(preset.center_lat);
      setLng(preset.center_lng);
      setRadiusKm(preset.radius_km);
      setCropX(preset.static_crop_x);
      setCropY(preset.static_crop_y);
      setCropW(preset.static_crop_width);
      setCropH(preset.static_crop_height);
      setPreviewB64(null);
      setCalculatedBbox(null);
    }
  };

  const handleSeedDatabase = async () => {
    setLoading(true);
    setMessage("");
    try {
      const res = await fetch(`${backendUrl}/api/v1/admin/radar/seed`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setMessage(`✅ ${data.message}`);
        fetchStations();
      } else {
        const data = await res.json();
        setMessage(`❌ เกิดข้อผิดพลาดในการนำเข้าข้อมูล: ${data.detail || res.statusText}`);
      }
    } catch (err: any) {
      setMessage(`❌ Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async (overrideX?: number, overrideY?: number, overrideW?: number, overrideH?: number) => {
    setLoading(true);
    setMessage("");
    try {
      const targetX = overrideX !== undefined ? overrideX : cropX;
      const targetY = overrideY !== undefined ? overrideY : cropY;
      const targetW = overrideW !== undefined ? overrideW : cropW;
      const targetH = overrideH !== undefined ? overrideH : cropH;

      const payload: any = {
        code,
        name,
        image_url: imageUrl,
        lat: Number(lat),
        lng: Number(lng),
        radius_km: Number(radiusKm)
      };
      if (targetX !== null) payload.crop_x = targetX;
      if (targetY !== null) payload.crop_y = targetY;
      if (targetW !== null) payload.crop_width = targetW;
      if (targetH !== null) payload.crop_height = targetH;

      const res = await fetch(`${backendUrl}/api/v1/admin/radar/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (res.ok) {
        setPreviewB64(data.preview_image_base64);
        setCalculatedBbox(data.calculated_bbox);
        setCropX(data.crop_info.static_crop_x);
        setCropY(data.crop_info.static_crop_y);
        setCropW(data.crop_info.static_crop_width);
        setCropH(data.crop_info.static_crop_height);
      } else {
        setMessage(`⚠️ Error: ${data.detail || "Failed to generate preview"}`);
      }
    } catch (err: any) {
      setMessage(`❌ Network Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!calculatedBbox) {
      alert("โปรดกด Preview & Auto-Detect ก่อนทำการบันทึกครับ");
      return;
    }
    setLoading(true);
    try {
      const savePayload = {
        code,
        name,
        static_image_url: imageUrl,
        loop_page_url: `https://weather.tmd.go.th/${code.substring(0, 3)}Loop.php`,
        loop_gif_url: "",
        center_lat: Number(lat),
        center_lng: Number(lng),
        radius_km: Number(radiusKm),
        lat_max: calculatedBbox.lat_max,
        lng_min: calculatedBbox.lng_min,
        lat_min: calculatedBbox.lat_min,
        lng_max: calculatedBbox.lng_max,
        static_crop_x: cropX ?? 0,
        static_crop_y: cropY ?? 0,
        static_crop_width: cropW ?? 800,
        static_crop_height: cropH ?? 800,
        loop_crop_x: cropX ?? 0,
        loop_crop_y: cropY ?? 0,
        loop_crop_width: cropW ?? 680,
        loop_crop_height: cropH ?? 680,
        is_active: true
      };

      const res = await fetch(`${backendUrl}/api/v1/admin/radar/stations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(savePayload)
      });

      if (res.ok) {
        setMessage(`✅ บันทึกสถานีเรดาร์ [${code}] เข้าสู่ Neon DB สำเร็จเรียบร้อย!`);
        fetchStations();
      } else {
        const data = await res.json();
        setMessage(`❌ เกิดข้อผิดพลาดในการบันทึก: ${data.detail}`);
      }
    } catch (err: any) {
      setMessage(`❌ Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (stCode: string, currentActive: boolean) => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/admin/radar/stations/${stCode}/toggle?is_active=${!currentActive}`, {
        method: "PATCH"
      });
      if (res.ok) {
        fetchStations();
      }
    } catch (err) {
      console.error("Failed to toggle station", err);
    }
  };

  // Accurate Mouse Coordinate Translation (Natural Image 800x800 vs Rendered Size)
  const getNaturalCoords = (e: MouseEvent | React.MouseEvent) => {
    if (!imgRef.current) return { x: 0, y: 0 };
    const rect = imgRef.current.getBoundingClientRect();
    const naturalWidth = imgRef.current.naturalWidth || 800;
    const naturalHeight = imgRef.current.naturalHeight || 800;

    const scaleX = naturalWidth / rect.width;
    const scaleY = naturalHeight / rect.height;

    // Clamp mouse position within image bounds and scale to natural 800x800 coords
    const mouseX = Math.round(Math.max(0, Math.min(naturalWidth, (e.clientX - rect.left) * scaleX)));
    const mouseY = Math.round(Math.max(0, Math.min(naturalHeight, (e.clientY - rect.top) * scaleY)));

    return { x: mouseX, y: mouseY, rectWidth: rect.width, rectHeight: rect.height, naturalWidth, naturalHeight };
  };

  // Dragging active handle: 'create' | 'top' | 'bottom' | 'left' | 'right' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
  const [activeHandle, setActiveHandle] = useState<string | null>(null);
  const [handleDragStart, setHandleDragStart] = useState<{ mouseX: number; mouseY: number; initX: number; initY: number; initW: number; initH: number; natW: number; natH: number } | null>(null);

  const startHandleDrag = (handle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    if (!imgRef.current) return;
    const coords = getNaturalCoords(e);
    const natW = imgRef.current.naturalWidth || 800;
    const natH = imgRef.current.naturalHeight || 800;
    setActiveHandle(handle);
    setHandleDragStart({
      mouseX: coords.x,
      mouseY: coords.y,
      initX: cropX ?? 0,
      initY: cropY ?? 0,
      initW: cropW ?? natW,
      initH: cropH ?? natH,
      natW,
      natH
    });
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLImageElement>) => {
    e.preventDefault();
    const coords = getNaturalCoords(e);
    setIsDragging(true);
    setActiveHandle("create");
    setDragStart({ x: coords.x, y: coords.y });
    setCurrentDragBox({ x: coords.x, y: coords.y, w: 0, h: 0 });
  };

  // Hover Crosshair state
  const [hoverPos, setHoverPos] = useState<{ pixelX: number; pixelY: number; relX: number; relY: number } | null>(null);

  const handleMouseMove = (e: React.MouseEvent<HTMLImageElement>) => {
    const coords = getNaturalCoords(e);
    if (imgRef.current) {
      const rect = imgRef.current.getBoundingClientRect();
      const relX = e.clientX - rect.left;
      const relY = e.clientY - rect.top;
      setHoverPos({ pixelX: coords.x, pixelY: coords.y, relX, relY });
    }
  };

  // Global Window-level MouseMove & MouseUp listeners to prevent drag loss when mouse leaves container
  useEffect(() => {
    if (!isDragging && !activeHandle) return;

    const onGlobalMouseMove = (e: MouseEvent) => {
      const coords = getNaturalCoords(e);

      if (activeHandle && handleDragStart && activeHandle !== "create") {
        const dx = coords.x - handleDragStart.mouseX;
        const dy = coords.y - handleDragStart.mouseY;

        let newX = handleDragStart.initX;
        let newY = handleDragStart.initY;
        let newW = handleDragStart.initW;
        let newH = handleDragStart.initH;

        const natW = handleDragStart.natW;
        const natH = handleDragStart.natH;

        if (activeHandle.includes("left")) {
          newX = Math.max(0, Math.min(handleDragStart.initX + handleDragStart.initW - 20, handleDragStart.initX + dx));
          newW = handleDragStart.initX + handleDragStart.initW - newX;
        }
        if (activeHandle.includes("right")) {
          // Max width: from initX to the far edge of the image
          newW = Math.max(20, Math.min(natW - handleDragStart.initX, handleDragStart.initW + dx));
        }
        if (activeHandle.includes("top")) {
          newY = Math.max(0, Math.min(handleDragStart.initY + handleDragStart.initH - 20, handleDragStart.initY + dy));
          newH = handleDragStart.initY + handleDragStart.initH - newY;
        }
        if (activeHandle.includes("bottom")) {
          newH = Math.max(20, Math.min(natH - handleDragStart.initY, handleDragStart.initH + dy));
        }

        setCropX(newX);
        setCropY(newY);
        setCropW(newW);
        setCropH(newH);
      } else if (isDragging && dragStart) {
        const x = Math.min(dragStart.x, coords.x);
        const y = Math.min(dragStart.y, coords.y);
        const w = Math.abs(coords.x - dragStart.x);
        const h = Math.abs(coords.y - dragStart.y);
        setCurrentDragBox({ x, y, w, h });
      }
    };

    const onGlobalMouseUp = () => {
      if (activeHandle && activeHandle !== "create") {
        setActiveHandle(null);
        setHandleDragStart(null);
        handlePreview(cropX ?? 0, cropY ?? 0, cropW ?? 800, cropH ?? 800);
      } else if (isDragging) {
        setIsDragging(false);
        setActiveHandle(null);
        if (currentDragBox && currentDragBox.w > 10 && currentDragBox.h > 10) {
          setCropX(currentDragBox.x);
          setCropY(currentDragBox.y);
          setCropW(currentDragBox.w);
          setCropH(currentDragBox.h);
          handlePreview(currentDragBox.x, currentDragBox.y, currentDragBox.w, currentDragBox.h);
        }
        setCurrentDragBox(null);
      }
    };

    window.addEventListener("mousemove", onGlobalMouseMove);
    window.addEventListener("mouseup", onGlobalMouseUp);

    return () => {
      window.removeEventListener("mousemove", onGlobalMouseMove);
      window.removeEventListener("mouseup", onGlobalMouseUp);
    };
  }, [isDragging, activeHandle, handleDragStart, dragStart, cropX, cropY, cropW, cropH, currentDragBox]);

  const handleMouseLeave = () => {
    setHoverPos(null);
  };

  const handleMouseUp = () => {
    // Handled by global listener
  };

  // Calculate visual style for dragging overlay box
  const getDragOverlayStyle = () => {
    if (!currentDragBox || !imgRef.current) return { display: "none" };
    const rect = imgRef.current.getBoundingClientRect();
    const naturalWidth = imgRef.current.naturalWidth || 800;
    const naturalHeight = imgRef.current.naturalHeight || 800;

    const scaleX = rect.width / naturalWidth;
    const scaleY = rect.height / naturalHeight;

    return {
      position: "absolute" as const,
      left: `${currentDragBox.x * scaleX}px`,
      top: `${currentDragBox.y * scaleY}px`,
      width: `${currentDragBox.w * scaleX}px`,
      height: `${currentDragBox.h * scaleY}px`,
      border: "2px dashed #f59e0b",
      backgroundColor: "rgba(245, 158, 11, 0.2)",
      pointerEvents: "none" as const,
      boxSizing: "border-box" as const,
      zIndex: 10
    };
  };

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "2rem", fontFamily: "sans-serif", color: "#1e293b", position: "relative" }}>
      {/* Full-screen Loading Modal Overlay during image processing */}
      {loading && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(15, 23, 42, 0.65)",
          backdropFilter: "blur(4px)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 9999,
          color: "#ffffff"
        }}>
          <div style={{
            width: 50,
            height: 50,
            border: "5px solid rgba(255, 255, 255, 0.2)",
            borderTopColor: "#38bdf8",
            borderRadius: "50%",
            animation: "spin 1s linear infinite"
          }} />
          <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
          <p style={{ marginTop: "1.25rem", fontSize: "1.125rem", fontWeight: 600, color: "#f8fafc" }}>
            ⏳ กำลังดาวน์โหลดและประมวลผลคำนวณขอบเขตเรดาร์...
          </p>
          <p style={{ fontSize: "0.875rem", color: "#cbd5e1", marginTop: "0.25rem" }}>
            โปรดรอสักครู่ ระบบกำลังปรับจูนรูปภาพและวิเคราะห์ Hough Circle
          </p>
        </div>
      )}

      <header style={{ marginBottom: "2rem", borderBottom: "2px solid #e2e8f0", paddingBottom: "1rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "1.875rem", fontWeight: "bold", color: "#0f172a" }}>📡 Dynamic Radar Management Portal</h1>
          <p style={{ color: "#64748b" }}>เพิ่ม/แก้ไข/ปรับแต่งขอบเขตสถานีเรดาร์ TMD ทั่วไทย เชื่อมต่อฐานข้อมูล Neon Postgres DB</p>
        </div>
        {/* Only show Seed button if DB has no stations */}
        {stations.length === 0 && (
          <button onClick={handleSeedDatabase} disabled={loading} style={{ padding: "0.75rem 1.25rem", backgroundColor: "#0284c7", color: "#fff", fontWeight: 600, border: "none", borderRadius: 8, cursor: "pointer" }}>
            📦 นำเข้าข้อมูลเรดาร์ตั้งต้นเข้า Neon DB
          </button>
        )}
      </header>

      {message && (
        <div style={{ padding: "1rem", borderRadius: 8, backgroundColor: message.startsWith("✅") ? "#dcfce7" : "#fee2e2", color: message.startsWith("✅") ? "#166534" : "#991b1b", marginBottom: "1.5rem", fontWeight: 500 }}>
          {message}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
        {/* Left Form Column */}
        <div style={{ background: "#ffffff", padding: "1.5rem", borderRadius: 12, boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0" }}>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>1. ค้นหาและระบุสถานีเรดาร์ (Station Metadata)</h2>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div style={{ backgroundColor: "#f0f9ff", padding: "0.75rem", borderRadius: 8, border: "1px solid #bae6fd" }}>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, color: "#0369a1", marginBottom: 4 }}>🎯 Quick-Select สถานีเรดาร์สำเร็จรูป (Presets)</label>
              <select onChange={handleSelectPreset} style={{ width: "100%", padding: "0.5rem", borderRadius: 6, border: "1px solid #7dd3fc", backgroundColor: "#ffffff" }}>
                <option value="">-- เลือกสถานีเรดาร์ที่มีอยู่ในระบบเพื่อค้นหา Lat/Lng อัตโนมัติ --</option>
                {presets.map((p) => (
                  <option key={p.code} value={p.code}>
                    [{p.code}] {p.name} — Lat: {p.center_lat}, Lng: {p.center_lng}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, marginBottom: 4 }}>รหัสสถานี (Station Code)</label>
              <input type="text" value={code} onChange={(e) => setCode(e.target.value)} style={{ width: "100%", padding: "0.5rem", borderRadius: 6, border: "1px solid #cbd5e1" }} />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, marginBottom: 4 }}>ชื่อสถานี (Station Name)</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} style={{ width: "100%", padding: "0.5rem", borderRadius: 6, border: "1px solid #cbd5e1" }} />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, marginBottom: 4 }}>URL ภาพเรดาร์ (Static Image URL)</label>
              <input type="text" value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} style={{ width: "100%", padding: "0.5rem", borderRadius: 6, border: "1px solid #cbd5e1" }} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, marginBottom: 4 }}>Latitude</label>
                <input type="number" step="0.0001" value={lat} onChange={(e) => setLat(parseFloat(e.target.value))} style={{ width: "100%", padding: "0.5rem", borderRadius: 6, border: "1px solid #cbd5e1" }} />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, marginBottom: 4 }}>Longitude</label>
                <input type="number" step="0.0001" value={lng} onChange={(e) => setLng(parseFloat(e.target.value))} style={{ width: "100%", padding: "0.5rem", borderRadius: 6, border: "1px solid #cbd5e1" }} />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, marginBottom: 4 }}>Radius (km)</label>
                <input type="number" value={radiusKm} onChange={(e) => setRadiusKm(parseFloat(e.target.value))} style={{ width: "100%", padding: "0.5rem", borderRadius: 6, border: "1px solid #cbd5e1" }} />
              </div>
            </div>

            <hr style={{ border: 0, borderTop: "1px solid #e2e8f0", margin: "0.5rem 0" }} />

            <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#334155" }}>2. จูนกรอบขอบเขต (Fine-Tune Sliders)</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600 }}>Crop X: {cropX ?? "-"}</label>
                <input type="range" min="0" max="400" value={cropX ?? 0} onChange={(e) => setCropX(parseInt(e.target.value))} style={{ width: "100%" }} />
              </div>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600 }}>Crop Y: {cropY ?? "-"}</label>
                <input type="range" min="0" max="400" value={cropY ?? 0} onChange={(e) => setCropY(parseInt(e.target.value))} style={{ width: "100%" }} />
              </div>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600 }}>Crop Width: {cropW ?? "-"}</label>
                <input type="range" min="200" max="800" value={cropW ?? 800} onChange={(e) => setCropW(parseInt(e.target.value))} style={{ width: "100%" }} />
              </div>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600 }}>Crop Height: {cropH ?? "-"}</label>
                <input type="range" min="200" max="800" value={cropH ?? 800} onChange={(e) => setCropH(parseInt(e.target.value))} style={{ width: "100%" }} />
              </div>
            </div>

            <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
              <button onClick={() => handlePreview()} disabled={loading} style={{ flex: 1, padding: "0.75rem", backgroundColor: "#2563eb", color: "#fff", fontWeight: 600, border: "none", borderRadius: 8, cursor: "pointer" }}>
                {loading ? "⏳ กำลังประมวลผล..." : "🔍 Preview & Auto-Detect"}
              </button>
              <button onClick={handleSubmit} disabled={loading || !calculatedBbox} style={{ flex: 1, padding: "0.75rem", backgroundColor: "#16a34a", color: "#fff", fontWeight: 600, border: "none", borderRadius: 8, cursor: "pointer", opacity: calculatedBbox ? 1 : 0.5 }}>
                💾 Submit to Neon DB
              </button>
            </div>
          </div>
        </div>

        {/* Right Preview Column & Mouse Interactive Drag */}
        <div style={{ background: "#ffffff", padding: "1.5rem", borderRadius: 12, boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0", display: "flex", flexDirection: "column", alignItems: "center" }}>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem", alignSelf: "flex-start" }}>3. ภาพพรีวิวขอบเขต & Interactive Mouse Crop</h2>
          <p style={{ fontSize: "0.875rem", color: "#64748b", marginBottom: "1rem", alignSelf: "flex-start" }}>
            💡 <b>เคล็ดลับ:</b> คุณสามารถใช้เมาส์ <b>คลิกแล้วลากกรอบบนภาพพรีวิว</b> เพื่อกำหนดพื้นที่ Crop ได้ทันที
          </p>

          {previewB64 ? (
            <div style={{ position: "relative", display: "inline-block", userSelect: "none" }}>
              <img
                ref={imgRef}
                src={previewB64}
                alt="Radar Preview Overlay"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseLeave}
                style={{ maxWidth: "100%", maxHeight: 420, borderRadius: 8, border: "2px solid #cbd5e1", display: "block", cursor: "crosshair" }}
              />

              {/* Laser Crosshair Guide Lines on Hover */}
              {hoverPos && (
                <>
                  {/* Vertical Crosshair Line */}
                  <div
                    style={{
                      position: "absolute",
                      top: 0,
                      bottom: 0,
                      left: `${hoverPos.relX}px`,
                      width: "1px",
                      borderLeft: "3px dashed #ef4444",
                      pointerEvents: "none",
                      zIndex: 8
                    }}
                  />
                  {/* Horizontal Crosshair Line */}
                  <div
                    style={{
                      position: "absolute",
                      left: 0,
                      right: 0,
                      top: `${hoverPos.relY}px`,
                      height: "1px",
                      borderTop: "3px dashed #ef4444",
                      pointerEvents: "none",
                      zIndex: 8
                    }}
                  />
                  {/* Live Coordinates Tooltip */}
                  <div
                    style={{
                      position: "absolute",
                      left: `${Math.min(hoverPos.relX + 12, (imgRef.current?.getBoundingClientRect().width || 400) - 100)}px`,
                      top: `${Math.max(hoverPos.relY - 24, 8)}px`,
                      backgroundColor: "rgba(15, 23, 42, 0.85)",
                      color: "#38bdf8",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      padding: "2px 6px",
                      borderRadius: 4,
                      pointerEvents: "none",
                      zIndex: 12,
                      fontFamily: "monospace"
                    }}
                  >
                    X: {hoverPos.pixelX}, Y: {hoverPos.pixelY}
                  </div>
                </>
              )}

              {/* Dynamic Drag Box Overlay (While Drag-Creating New Box) */}
              <div style={getDragOverlayStyle()} />

              {/* Active Crop Box with Interactive 4-Edge & 4-Corner Handles */}
              {cropX !== null && cropY !== null && cropW !== null && cropH !== null && imgRef.current && (
                (() => {
                  const rect = imgRef.current.getBoundingClientRect();
                  const scaleX = rect.width / (imgRef.current.naturalWidth || 800);
                  const scaleY = rect.height / (imgRef.current.naturalHeight || 800);
                  const boxLeft = cropX * scaleX;
                  const boxTop = cropY * scaleY;
                  const boxW = cropW * scaleX;
                  const boxH = cropH * scaleY;

                  return (
                    <div
                      style={{
                        position: "absolute",
                        left: `${boxLeft}px`,
                        top: `${boxTop}px`,
                        width: `${boxW}px`,
                        height: `${boxH}px`,
                        border: "2px solid #3b82f6",
                        backgroundColor: "rgba(59, 130, 246, 0.1)",
                        boxSizing: "border-box",
                        zIndex: 9
                      }}
                    >
                      {/* Edge Handles */}
                      <div onMouseDown={(e) => startHandleDrag("top", e)} style={{ position: "absolute", top: -4, left: "20%", right: "20%", height: 8, cursor: "ns-resize", backgroundColor: "rgba(59, 130, 246, 0.6)", borderRadius: 4 }} />
                      <div onMouseDown={(e) => startHandleDrag("bottom", e)} style={{ position: "absolute", bottom: -4, left: "20%", right: "20%", height: 8, cursor: "ns-resize", backgroundColor: "rgba(59, 130, 246, 0.6)", borderRadius: 4 }} />
                      <div onMouseDown={(e) => startHandleDrag("left", e)} style={{ position: "absolute", left: -4, top: "20%", bottom: "20%", width: 8, cursor: "ew-resize", backgroundColor: "rgba(59, 130, 246, 0.6)", borderRadius: 4 }} />
                      <div onMouseDown={(e) => startHandleDrag("right", e)} style={{ position: "absolute", right: -4, top: "20%", bottom: "20%", width: 8, cursor: "ew-resize", backgroundColor: "rgba(59, 130, 246, 0.6)", borderRadius: 4 }} />

                      {/* Corner Handles */}
                      <div onMouseDown={(e) => startHandleDrag("top-left", e)} style={{ position: "absolute", top: -5, left: -5, width: 10, height: 10, cursor: "nwse-resize", backgroundColor: "#1d4ed8", border: "1px solid #fff", borderRadius: "50%" }} />
                      <div onMouseDown={(e) => startHandleDrag("top-right", e)} style={{ position: "absolute", top: -5, right: -5, width: 10, height: 10, cursor: "nesw-resize", backgroundColor: "#1d4ed8", border: "1px solid #fff", borderRadius: "50%" }} />
                      <div onMouseDown={(e) => startHandleDrag("bottom-left", e)} style={{ position: "absolute", bottom: -5, left: -5, width: 10, height: 10, cursor: "nesw-resize", backgroundColor: "#1d4ed8", border: "1px solid #fff", borderRadius: "50%" }} />
                      <div onMouseDown={(e) => startHandleDrag("bottom-right", e)} style={{ position: "absolute", bottom: -5, right: -5, width: 10, height: 10, cursor: "nwse-resize", backgroundColor: "#1d4ed8", border: "1px solid #fff", borderRadius: "50%" }} />
                    </div>
                  );
                })()
              )}

              <p style={{ marginTop: "0.75rem", fontSize: "0.875rem", color: "#475569", textAlign: "center" }}>
                🔴 <b>เส้นสีแดง</b>: เส้นเล็งเลเซอร์ | 🔵 <b>กรอบสีน้ำเงิน</b>: ขอบ Crop พร้อมปุ่มจับลากทั้ง 4 ด้านและ 4 มุม | 🟡 <b>เส้นสีส้ม</b>: กรอบสร้างใหม่
              </p>
            </div>
          ) : (
            <div style={{ color: "#94a3b8", textAlign: "center", padding: "4rem 0" }}>
              <p style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>🖼️</p>
              <p>กดปุ่ม <b>Preview & Auto-Detect</b> หรือเลือก Preset เพื่อดูภาพพรีวิว</p>
            </div>
          )}
        </div>
      </div>

      {/* Active Stations Table */}
      <section style={{ marginTop: "3rem", background: "#ffffff", padding: "1.5rem", borderRadius: 12, boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0" }}>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>📋 รายการสถานีเรดาร์ใน Neon DB ({stations.length} สถานี)</h2>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
            <thead>
              <tr style={{ background: "#f8fafc", borderBottom: "2px solid #e2e8f0" }}>
                <th style={{ padding: "0.75rem" }}>Code</th>
                <th style={{ padding: "0.75rem" }}>Name</th>
                <th style={{ padding: "0.75rem" }}>Center (Lat, Lng)</th>
                <th style={{ padding: "0.75rem" }}>Radius</th>
                <th style={{ padding: "0.75rem" }}>Crop (X, Y, W, H)</th>
                <th style={{ padding: "0.75rem" }}>Status</th>
                <th style={{ padding: "0.75rem" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {stations.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: "1.5rem", textAlign: "center", color: "#64748b" }}>
                    ไม่พบสถานีเรดาร์ใน Neon DB — กดปุ่ม <b>"📦 นำเข้าข้อมูลเรดาร์ตั้งต้นเข้า Neon DB"</b> ด้านบนเพื่อดึงข้อมูลสำเร็จรูปเข้าระบบ
                  </td>
                </tr>
              ) : (
                stations.map((st) => (
                  <tr key={st.code} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "0.75rem", fontFamily: "monospace", fontWeight: 600 }}>{st.code}</td>
                    <td style={{ padding: "0.75rem" }}>{st.name}</td>
                    <td style={{ padding: "0.75rem" }}>{st.center_lat}, {st.center_lng}</td>
                    <td style={{ padding: "0.75rem" }}>{st.radius_km} km</td>
                    <td style={{ padding: "0.75rem" }}>{st.static_crop.x}, {st.static_crop.y}, {st.static_crop.width}, {st.static_crop.height}</td>
                    <td style={{ padding: "0.75rem" }}>
                      <span style={{ padding: "0.25rem 0.5rem", borderRadius: 9999, fontSize: "0.75rem", fontWeight: 600, background: st.is_active ? "#dcfce7" : "#f1f5f9", color: st.is_active ? "#15803d" : "#64748b" }}>
                        {st.is_active ? "Active" : "Disabled"}
                      </span>
                    </td>
                    <td style={{ padding: "0.75rem" }}>
                      <button onClick={() => handleToggle(st.code, st.is_active)} style={{ padding: "0.25rem 0.75rem", borderRadius: 6, border: "1px solid #cbd5e1", background: "#f8fafc", cursor: "pointer" }}>
                        {st.is_active ? "Disable" : "Enable"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
