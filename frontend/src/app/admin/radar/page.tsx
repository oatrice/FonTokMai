"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Header } from "@/components/ui/Header";
import { RadarCoverageMap, DEFAULT_STATIONS, RadarStationCoverage } from "@/components/RadarCoverageMap";
import { 
  Radio, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Clock, 
  ExternalLink, 
  Sliders, 
  SlidersHorizontal,
  MapPin,
  Save,
  Wand2,
  Layers,
  Search
} from "lucide-react";

interface Station {
  code: string;
  name: string;
  static_image_url: string;
  loop_page_url?: string;
  loop_gif_url?: string;
  center_lat: number;
  center_lng: number;
  radius_km: number;
  static_crop: { x: number; y: number; width: number; height: number };
  loop_crop?: { x: number; y: number; width: number; height: number };
  is_active: boolean;
}

interface Preset {
  code: string;
  name: string;
  static_image_url: string;
  loop_page_url?: string;
  loop_gif_url?: string;
  center_lat: number;
  center_lng: number;
  radius_km: number;
  static_crop_x: number;
  static_crop_y: number;
  static_crop_width: number;
  static_crop_height: number;
}

interface StationStatusInfo {
  code: string;
  name: string;
  center_lat: number;
  center_lng: number;
  radius_km: number;
  status: "online" | "delayed" | "offline";
  latency_minutes: number;
  last_frame_timestamp: string;
  image_url?: string;
  loop_url?: string;
}

export default function AdminRadarPage() {
  const [stations, setStations] = useState<Station[]>([]);
  const [stationStatuses, setStationStatuses] = useState<StationStatusInfo[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [tableLoading, setTableLoading] = useState<boolean>(true);
  const [message, setMessage] = useState<string>("");
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  // Active Station in Fine-Tuning Panel
  const [code, setCode] = useState("hyi");
  const [name, setName] = useState("Hat Yai (240km) / หาดใหญ่");
  const [imageUrl, setImageUrl] = useState("https://weather.tmd.go.th/hyi/hyi240_latest.jpg");
  const [loopPageUrl, setLoopPageUrl] = useState("https://weather.tmd.go.th/hyiloop.php");
  const [loopGifUrl, setLoopGifUrl] = useState("https://weather.tmd.go.th/hyi/hyiloop.gif");
  const [lat, setLat] = useState(6.9248);
  const [lng, setLng] = useState(100.4385);
  const [radiusKm, setRadiusKm] = useState(240.0);

  // Crop Controls
  const [cropX, setCropX] = useState<number | null>(null);
  const [cropY, setCropY] = useState<number | null>(null);
  const [cropW, setCropW] = useState<number | null>(null);
  const [cropH, setCropH] = useState<number | null>(null);

  const [loopOffsetX, setLoopOffsetX] = useState<number>(0);
  const [loopOffsetY, setLoopOffsetY] = useState<number>(0);
  const [loopOffsetW, setLoopOffsetW] = useState<number>(0);
  const [loopOffsetH, setLoopOffsetH] = useState<number>(0);

  const [previewB64, setPreviewB64] = useState<string | null>(null);
  const [loopPreviewB64, setLoopPreviewB64] = useState<string | null>(null);
  const [telegramPreviewB64, setTelegramPreviewB64] = useState<string | null>(null);
  const [loopTelegramPreviewB64, setLoopTelegramPreviewB64] = useState<string | null>(null);
  const [activePreviewTab, setActivePreviewTab] = useState<"static" | "loop">("static");
  const [calculatedBbox, setCalculatedBbox] = useState<any>(null);
  const [detectedCircle, setDetectedCircle] = useState<number[] | null>(null);
  const [frozenStationCenter, setFrozenStationCenter] = useState<{ cx: number; cy: number } | null>(null);

  // Interactive Drag & Hover Coordinates
  const imgRef = useRef<HTMLImageElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [currentDragBox, setCurrentDragBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const [hoverPos, setHoverPos] = useState<{ pixelX: number; pixelY: number } | null>(null);

  const calibrationSectionRef = useRef<HTMLDivElement>(null);
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  // Fetch DB Stations and Live Statuses
  const fetchAllData = useCallback(async () => {
    setTableLoading(true);
    try {
      const [dbRes, statusRes, presetsRes] = await Promise.all([
        fetch(`${backendUrl}/api/v1/admin/radar/stations`),
        fetch("/api/admin/radar"),
        fetch(`${backendUrl}/api/v1/admin/radar/presets`)
      ]);

      if (dbRes.ok) {
        const dbData = await dbRes.json();
        setStations(dbData);
      }
      if (statusRes.ok) {
        const stData = await statusRes.json();
        setStationStatuses(stData.stations || []);
      }
      if (presetsRes.ok) {
        const prData = await presetsRes.json();
        setPresets(prData);
      }
    } catch (err) {
      console.error("Failed to fetch radar management data:", err);
    } finally {
      setTableLoading(false);
      setLastRefreshed(new Date());
    }
  }, [backendUrl]);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // Select station from map or table
  const handleSelectStation = (st: Station) => {
    setCode(st.code);
    setName(st.name);
    setImageUrl(st.static_image_url);
    setLoopPageUrl(st.loop_page_url || `https://weather.tmd.go.th/${st.code.substring(0, 3)}Loop.php`);
    setLoopGifUrl(st.loop_gif_url || `https://weather.tmd.go.th/${st.code.substring(0, 3)}/${st.code.substring(0, 3)}loop.gif`);
    setLat(st.center_lat);
    setLng(st.center_lng);
    setRadiusKm(st.radius_km);

    const cX = st.static_crop.x;
    const cY = st.static_crop.y;
    const cW = st.static_crop.width;
    const cH = st.static_crop.height;

    setCropX(cX);
    setCropY(cY);
    setCropW(cW);
    setCropH(cH);

    if (st.loop_crop) {
      setLoopOffsetX(st.loop_crop.x - st.static_crop.x);
      setLoopOffsetY(st.loop_crop.y - st.static_crop.y);
      setLoopOffsetW(st.loop_crop.width - st.static_crop.width);
      setLoopOffsetH(st.loop_crop.height - st.static_crop.height);
    } else {
      setLoopOffsetX(0);
      setLoopOffsetY(0);
      setLoopOffsetW(0);
      setLoopOffsetH(0);
    }

    handlePreview(cX, cY, cW, cH, st.code, st.name, st.static_image_url, st.center_lat, st.center_lng, st.radius_km);

    // Smooth scroll down to calibration tool
    calibrationSectionRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSelectPreset = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedCode = e.target.value;
    if (!selectedCode) return;

    const preset = presets.find((p) => p.code === selectedCode);
    if (preset) {
      setCode(preset.code);
      setName(preset.name);
      setImageUrl(preset.static_image_url);
      setLoopPageUrl(preset.loop_page_url || `https://weather.tmd.go.th/${preset.code.substring(0, 3)}Loop.php`);
      setLoopGifUrl(preset.loop_gif_url || `https://weather.tmd.go.th/${preset.code.substring(0, 3)}/${preset.code.substring(0, 3)}loop.gif`);
      setLat(preset.center_lat);
      setLng(preset.center_lng);
      setRadiusKm(preset.radius_km);
      setCropX(preset.static_crop_x);
      setCropY(preset.static_crop_y);
      setCropW(preset.static_crop_width);
      setCropH(preset.static_crop_height);
      setPreviewB64(null);
      setCalculatedBbox(null);
      handlePreview(preset.static_crop_x, preset.static_crop_y, preset.static_crop_width, preset.static_crop_height, preset.code, preset.name, preset.static_image_url, preset.center_lat, preset.center_lng, preset.radius_km);
    }
  };

  const handlePreview = async (
    overrideX?: number | null,
    overrideY?: number | null,
    overrideW?: number | null,
    overrideH?: number | null,
    overrideCode?: string,
    overrideName?: string,
    overrideImageUrl?: string,
    overrideLat?: number,
    overrideLng?: number,
    overrideRadiusKm?: number
  ) => {
    setLoading(true);
    setMessage("");
    try {
      const targetX = overrideX !== undefined ? overrideX : cropX;
      const targetY = overrideY !== undefined ? overrideY : cropY;
      const targetW = overrideW !== undefined ? overrideW : cropW;
      const targetH = overrideH !== undefined ? overrideH : cropH;

      const payload: any = {
        code: overrideCode || code,
        name: overrideName || name,
        image_url: overrideImageUrl || imageUrl,
        loop_gif_url: loopGifUrl,
        lat: Number(overrideLat !== undefined ? overrideLat : lat),
        lng: Number(overrideLng !== undefined ? overrideLng : lng),
        radius_km: Number(overrideRadiusKm !== undefined ? overrideRadiusKm : radiusKm),
      };
      if (targetX !== null) {
        payload.crop_x = targetX;
        payload.crop_y = targetY;
        payload.crop_width = targetW;
        payload.crop_height = targetH;
        payload.loop_crop_x = (targetX ?? 0) + loopOffsetX;
        payload.loop_crop_y = (targetY ?? 0) + loopOffsetY;
        payload.loop_crop_width = (targetW ?? 800) + loopOffsetW;
        payload.loop_crop_height = (targetH ?? 800) + loopOffsetH;
      }

      const res = await fetch(`${backendUrl}/api/v1/admin/radar/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok) {
        setPreviewB64(data.preview_image_base64);
        setLoopPreviewB64(data.loop_preview_image_base64 || null);
        setTelegramPreviewB64(data.telegram_preview_base64 || null);
        setLoopTelegramPreviewB64(data.loop_telegram_preview_base64 || null);
        setCalculatedBbox(data.calculated_bbox);
        setDetectedCircle(data.detected_circle || null);
        if (data.detected_circle) {
          setFrozenStationCenter({ cx: data.detected_circle[0], cy: data.detected_circle[1] });
        }
        setCropX(data.crop_info.static_crop_x);
        setCropY(data.crop_info.static_crop_y);
        setCropW(data.crop_info.static_crop_width);
        setCropH(data.crop_info.static_crop_height);

        if (targetX === null) {
          setLoopOffsetX(data.crop_info.loop_crop_x - data.crop_info.static_crop_x);
          setLoopOffsetY(data.crop_info.loop_crop_y - data.crop_info.static_crop_y);
          setLoopOffsetW(data.crop_info.loop_crop_width - data.crop_info.static_crop_width);
          setLoopOffsetH(data.crop_info.loop_crop_height - data.crop_info.static_crop_height);
        }
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
        loop_page_url: loopPageUrl || `https://weather.tmd.go.th/${code.substring(0, 3)}Loop.php`,
        loop_gif_url: loopGifUrl || `https://weather.tmd.go.th/${code.substring(0, 3)}/${code.substring(0, 3)}loop.gif`,
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
        loop_crop_x: (cropX ?? 0) + loopOffsetX,
        loop_crop_y: (cropY ?? 0) + loopOffsetY,
        loop_crop_width: (cropW ?? 680) + loopOffsetW,
        loop_crop_height: (cropH ?? 680) + loopOffsetH,
        is_active: true,
      };

      const res = await fetch(`${backendUrl}/api/v1/admin/radar/stations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(savePayload),
      });

      if (res.ok) {
        setMessage(`✅ บันทึกสถานีเรดาร์ [${code}] เข้าสู่ Neon DB สำเร็จเรียบร้อย!`);
        fetchAllData();
      } else {
        const data = await res.json();
        setMessage(`❌ เกิดข้อผิดพลาดในการบันทึก: ${data.detail}`);
      }
    } catch (err: any) {
      setMessage(`❌ Network Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (stCode: string, currentStatus: boolean) => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/admin/radar/stations/${stCode}/toggle?is_active=${!currentStatus}`, {
        method: "PATCH",
      });
      if (res.ok) {
        fetchAllData();
      }
    } catch (err) {
      console.error("Failed to toggle station", err);
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
        fetchAllData();
      } else {
        const data = await res.json();
        setMessage(`❌ เกิดข้อผิดพลาด: ${data.detail || res.statusText}`);
      }
    } catch (err: any) {
      setMessage(`❌ Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Convert Pixel on Radar image to Lat/Lng
  const pixelToLatLng = (px: number, py: number) => {
    const cX = (cropX ?? 0) + (cropW ?? 800) / 2.0;
    const cY = (cropY ?? 0) + (cropH ?? 800) / 2.0;
    const dx = px - cX;
    const dy = cY - py;
    const rPx = (cropW ?? 800) / 2.0;
    if (rPx <= 0) return { hoverLat: lat, hoverLng: lng };

    const distKm = (Math.hypot(dx, dy) / rPx) * radiusKm;
    const bearing = Math.atan2(dx, dy);

    const R = 6371.0;
    const lat1 = (lat * Math.PI) / 180.0;
    const lon1 = (lng * Math.PI) / 180.0;
    const dR = distKm / R;

    const lat2 = Math.asin(
      Math.sin(lat1) * Math.cos(dR) + Math.cos(lat1) * Math.sin(dR) * Math.cos(bearing)
    );
    const lon2 =
      lon1 +
      Math.atan2(
        Math.sin(bearing) * Math.sin(dR) * Math.cos(lat1),
        Math.cos(dR) - Math.sin(lat1) * Math.sin(lat2)
      );

    return {
      hoverLat: (lat2 * 180.0) / Math.PI,
      hoverLng: (lon2 * 180.0) / Math.PI,
    };
  };

  const hoverCoords = hoverPos ? pixelToLatLng(hoverPos.pixelX, hoverPos.pixelY) : null;

  // KPI Metrics
  const onlineCount = stationStatuses.filter((st) => st.status === "online").length;
  const delayedCount = stationStatuses.filter((st) => st.status === "delayed").length;
  const offlineCount = stationStatuses.filter((st) => st.status === "offline").length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 pb-20">
      <Header />

      {/* Global Loading Spinner */}
      {loading && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50 flex flex-col items-center justify-center text-white">
          <div className="w-12 h-12 border-4 border-slate-700 border-t-sky-400 rounded-full animate-spin" />
          <p className="mt-4 text-base font-semibold text-slate-200">⏳ กำลังประมวลผลคำนวณขอบเขตเรดาร์...</p>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-10">
        {/* Top Header & Overview */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
              <Radio className="w-8 h-8 text-sky-400 animate-pulse" />
              TMD Radar Administration & Live Operations
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              ระบบตรวจสอบสถานะความพร้อมและปรับแต่งขอบเขตสถานีเรดาร์ตรวจอากาศทั่วประเทศ (13 สถานี)
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 hidden sm:flex items-center gap-1.5 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
              <Clock className="w-3.5 h-3.5 text-slate-500" /> อัปเดตล่าสุด: {lastRefreshed.toLocaleTimeString()}
            </span>
            <button
              onClick={fetchAllData}
              disabled={tableLoading}
              className="flex items-center gap-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold px-4 py-2 rounded-xl shadow-lg shadow-sky-600/20 transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${tableLoading ? "animate-spin" : ""}`} />
              รีเฟรชข้อมูล
            </button>
            {stations.length === 0 && (
              <button
                onClick={handleSeedDatabase}
                disabled={loading}
                className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all"
              >
                📦 นำเข้า 13 สถานีตั้งต้นเข้า Neon DB
              </button>
            )}
          </div>
        </div>

        {/* Message Banner */}
        {message && (
          <div className={`p-4 rounded-2xl border font-medium text-sm ${
            message.startsWith("✅") ? "bg-emerald-950/40 border-emerald-800 text-emerald-300" : "bg-rose-950/40 border-rose-800 text-rose-300"
          }`}>
            {message}
          </div>
        )}

        {/* Section 1: KPI Metrics Overview */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Stations</span>
            <div className="text-3xl font-extrabold text-white mt-1">{stations.length || 13}</div>
          </div>
          <div className="bg-emerald-950/20 border border-emerald-800/40 rounded-2xl p-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> Online (&lt;30m)
            </span>
            <div className="text-3xl font-extrabold text-emerald-300 mt-1">{onlineCount || 13}</div>
          </div>
          <div className="bg-amber-950/20 border border-amber-800/40 rounded-2xl p-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" /> Delayed
            </span>
            <div className="text-3xl font-extrabold text-amber-300 mt-1">{delayedCount}</div>
          </div>
          <div className="bg-rose-950/20 border border-rose-800/40 rounded-2xl p-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
              <XCircle className="w-3.5 h-3.5" /> Offline
            </span>
            <div className="text-3xl font-extrabold text-rose-300 mt-1">{offlineCount}</div>
          </div>
        </div>

        {/* Section 2: Interactive SVG Thailand Nationwide Map */}
        <section className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 shadow-2xl backdrop-blur">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
                1. แผนที่เรดาร์และขอบเขตความคุ้มครองประเทศไทย (Nationwide SVG Coverage Map)
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                💡 <b>เคล็ดลับ:</b> คุณสามารถ <b>คลิกที่หมุดสถานีเรดาร์บนแผนที่</b> เพื่อโหลดข้อมูลขึ้นมาปรับจูนในเครื่องมือด้านล่างได้ทันที
              </p>
            </div>
          </div>

          <RadarCoverageMap
            stations={
              stations.length > 0
                ? stations.map((s) => ({
                    code: s.code,
                    name: s.name,
                    center_lat: s.center_lat,
                    center_lng: s.center_lng,
                    radius_km: s.radius_km,
                    is_active: s.is_active,
                    region:
                      s.code.startsWith("cmi") || s.code.startsWith("phs") || s.code === "tak" || s.code === "cri"
                        ? "north"
                        : s.code.startsWith("kkn") || s.code.startsWith("skn") || s.code.startsWith("ubn")
                        ? "northeast"
                        : s.code.startsWith("chn") || s.code.startsWith("svp") || s.code.startsWith("ntp")
                        ? "central"
                        : s.code.startsWith("ryg")
                        ? "east"
                        : "south",
                  }))
                : DEFAULT_STATIONS
            }
            onSelectStation={(stCode) => {
              const found = stations.find((s) => s.code === stCode);
              if (found) {
                handleSelectStation(found);
              }
            }}
          />
        </section>

        {/* Section 3: Fine-Tuning & Live Image Calibration Panel */}
        <div ref={calibrationSectionRef} className="space-y-6">
          <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                <Sliders className="w-5 h-5 text-sky-400" />
                2. เครื่องมือปรับจูนขอบเขตเรดาร์สด (Live Station Calibration Tool)
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                สถานีที่เลือกในปัจจุบัน: <b className="text-sky-300 font-mono">[{code}] {name}</b>
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Form Controls Column */}
            <div className="lg:col-span-6 bg-slate-900/60 border border-slate-800 rounded-3xl p-6 space-y-6">
              <div className="bg-sky-950/30 border border-sky-800/50 rounded-2xl p-4">
                <label className="block text-xs font-semibold text-sky-400 mb-1.5 flex items-center gap-1.5">
                  <Search className="w-3.5 h-3.5" /> Quick-Select สถานีเรดาร์จาก Catalog
                </label>
                <select
                  value={code}
                  onChange={handleSelectPreset}
                  className="w-full bg-slate-900 border border-sky-700/60 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500"
                >
                  <option value="">-- เลือกสถานีเรดาร์ที่มีอยู่ในระบบเพื่อค้นหา Lat/Lng อัตโนมัติ --</option>
                  {presets.map((p) => (
                    <option key={p.code} value={p.code}>
                      {p.name} [{p.code}] (Lat: {p.center_lat}, Lng: {p.center_lng})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">รหัสสถานี (Code)</label>
                  <input
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm font-mono text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">ชื่อสถานี (Name)</label>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Static Radar Image URL</label>
                  <input
                    value={imageUrl}
                    onChange={(e) => setImageUrl(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-300 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Loop Page URL</label>
                    <input
                      value={loopPageUrl}
                      onChange={(e) => setLoopPageUrl(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-300 focus:outline-none focus:ring-1 focus:ring-sky-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Loop GIF URL</label>
                    <input
                      value={loopGifUrl}
                      onChange={(e) => setLoopGifUrl(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-300 focus:outline-none focus:ring-1 focus:ring-sky-500"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Center Lat</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={lat}
                    onChange={(e) => setLat(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Center Lng</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={lng}
                    onChange={(e) => setLng(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Radius (km)</label>
                  <input
                    type="number"
                    value={radiusKm}
                    onChange={(e) => setRadiusKm(parseFloat(e.target.value) || 240)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none"
                  />
                </div>
              </div>

              {/* Crop Sliders */}
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-4 space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-sky-400" /> ปรับจูนแถบเลื่อน Crop Area (Fine-Tuning)
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-slate-400">Crop X: {cropX ?? "-"} px</span>
                    <input
                      type="range"
                      min="0"
                      max="400"
                      value={cropX ?? 0}
                      onChange={(e) => setCropX(parseInt(e.target.value))}
                      className="w-full accent-sky-400"
                    />
                  </div>
                  <div>
                    <span className="text-xs text-slate-400">Crop Y: {cropY ?? "-"} px</span>
                    <input
                      type="range"
                      min="0"
                      max="400"
                      value={cropY ?? 0}
                      onChange={(e) => setCropY(parseInt(e.target.value))}
                      className="w-full accent-sky-400"
                    />
                  </div>
                  <div>
                    <span className="text-xs text-slate-400">Crop Width: {cropW ?? "-"} px</span>
                    <input
                      type="range"
                      min="200"
                      max="800"
                      value={cropW ?? 800}
                      onChange={(e) => setCropW(parseInt(e.target.value))}
                      className="w-full accent-sky-400"
                    />
                  </div>
                  <div>
                    <span className="text-xs text-slate-400">Crop Height: {cropH ?? "-"} px</span>
                    <input
                      type="range"
                      min="200"
                      max="800"
                      value={cropH ?? 800}
                      onChange={(e) => setCropH(parseInt(e.target.value))}
                      className="w-full accent-sky-400"
                    />
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-3 pt-2">
                <button
                  onClick={() => handlePreview()}
                  disabled={loading}
                  className="flex-1 min-w-[130px] flex items-center justify-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold py-3 px-4 rounded-xl border border-slate-700 transition"
                >
                  🔍 Preview Sliders
                </button>
                <button
                  onClick={() => {
                    setCropX(null);
                    setCropY(null);
                    setCropW(null);
                    setCropH(null);
                    handlePreview(null, null, null, null);
                  }}
                  disabled={loading}
                  className="flex-1 min-w-[130px] flex items-center justify-center gap-1.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold py-3 px-4 rounded-xl shadow-lg shadow-sky-600/20 transition"
                >
                  <Wand2 className="w-3.5 h-3.5" /> Auto-Detect
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={loading || !calculatedBbox}
                  className="flex-1 min-w-[130px] flex items-center justify-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold py-3 px-4 rounded-xl shadow-lg shadow-emerald-600/20 transition"
                >
                  <Save className="w-3.5 h-3.5" /> บันทึกลง Neon DB
                </button>
              </div>
            </div>

            {/* Live Image Preview Column */}
            <div className="lg:col-span-6 bg-slate-900/60 border border-slate-800 rounded-3xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-sky-400" />
                  ภาพพรีวิวขอบเขต & พิกัด Lat/Lng เรียลไทม์
                </h3>
                <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
                  <button
                    onClick={() => setActivePreviewTab("static")}
                    className={`px-3 py-1 rounded-md transition ${activePreviewTab === "static" ? "bg-slate-800 text-white" : "text-slate-400"}`}
                  >
                    Static Frame
                  </button>
                  <button
                    onClick={() => setActivePreviewTab("loop")}
                    className={`px-3 py-1 rounded-md transition ${activePreviewTab === "loop" ? "bg-slate-800 text-white" : "text-slate-400"}`}
                  >
                    Loop Preview
                  </button>
                </div>
              </div>

              {/* Interactive Image Container */}
              <div className="relative border border-slate-800 rounded-2xl overflow-hidden bg-slate-950 flex items-center justify-center min-h-[380px]">
                {activePreviewTab === "static" ? (
                  previewB64 ? (
                    <div
                      className="relative inline-block select-none cursor-crosshair"
                      onMouseMove={(e) => {
                        if (!imgRef.current) return;
                        const rect = imgRef.current.getBoundingClientRect();
                        const naturalW = imgRef.current.naturalWidth || 800;
                        const naturalH = imgRef.current.naturalHeight || 800;
                        const px = Math.round(((e.clientX - rect.left) / rect.width) * naturalW);
                        const py = Math.round(((e.clientY - rect.top) / rect.height) * naturalH);
                        setHoverPos({ pixelX: px, pixelY: py });
                      }}
                      onMouseLeave={() => setHoverPos(null)}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        ref={imgRef}
                        src={previewB64}
                        alt="Radar Preview"
                        className="max-w-full max-h-[500px] object-contain"
                      />
                    </div>
                  ) : (
                    <div className="text-center p-8 text-slate-500">
                      <Radio className="w-12 h-12 mx-auto mb-2 text-slate-700" />
                      <p className="text-xs">กดปุ่ม <b>"Auto-Detect"</b> หรือ <b>"Preview Sliders"</b> เพื่อโหลดภาพเรดาร์</p>
                    </div>
                  )
                ) : loopPreviewB64 ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img src={loopPreviewB64} alt="Loop Preview" className="max-w-full max-h-[500px] object-contain" />
                ) : (
                  <div className="text-center p-8 text-slate-500">
                    <p className="text-xs">ไม่มีภาพ Loop GIF พรีวิวสำหรับสถานีนี้</p>
                  </div>
                )}
              </div>

              {/* Coordinates Inspector Readout */}
              <div className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-3.5 text-xs text-slate-400">
                {hoverCoords && hoverPos ? (
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-slate-300">
                      🖼️ Pixel: <b>({hoverPos.pixelX}, {hoverPos.pixelY})</b> px
                    </span>
                    <span className="font-mono text-sky-400">
                      🌐 GPS: <b>{hoverCoords.hoverLat.toFixed(5)}°N, {hoverCoords.hoverLng.toFixed(5)}°E</b>
                    </span>
                  </div>
                ) : (
                  <span className="text-slate-500">
                    เลื่อนเมาส์บนภาพพรีวิวเรดาร์ด้านบนเพื่อตรวจสอบค่า Pixel (X, Y) และพิกัด Lat/Lng แบบเรียลไทม์
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Section 4: All Stations Table */}
        <section className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 shadow-2xl backdrop-blur">
          <h2 className="text-lg font-bold text-slate-100 mb-1 flex items-center gap-2">
            📋 3. รายการสถานีเรดาร์ทั้งหมดในระบบ ({stations.length} สถานี)
          </h2>
          <p className="text-xs text-slate-400 mb-4">
            💡 คลิกแถวสถานีในตารางเพื่อเลือกและเลื่อนไปยังเครื่องมือปรับจูนขอบเขตทันที
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4">Code</th>
                  <th className="py-3 px-4">Name</th>
                  <th className="py-3 px-4">Center (Lat, Lng)</th>
                  <th className="py-3 px-4">Radius</th>
                  <th className="py-3 px-4">Crop (X, Y, W, H)</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {tableLoading ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-400">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-sky-400" />
                      กำลังโหลดข้อมูลสถานีเรดาร์จาก Database...
                    </td>
                  </tr>
                ) : stations.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-6 text-center text-slate-500">
                      ไม่พบสถานีเรดาร์ — กดปุ่ม <b>"นำเข้า 13 สถานีตั้งต้นเข้า Neon DB"</b> ด้านบน
                    </td>
                  </tr>
                ) : (
                  stations.map((st) => {
                    const isSelected = code === st.code;
                    return (
                      <tr
                        key={st.code}
                        onClick={() => handleSelectStation(st)}
                        className={`cursor-pointer transition-colors ${
                          isSelected ? "bg-sky-950/40 text-white" : "hover:bg-slate-800/40 text-slate-300"
                        }`}
                      >
                        <td className="py-3 px-4 font-mono font-bold text-sky-400">{st.code}</td>
                        <td className="py-3 px-4 font-medium">{st.name}</td>
                        <td className="py-3 px-4 font-mono">{st.center_lat}, {st.center_lng}</td>
                        <td className="py-3 px-4">{st.radius_km} km</td>
                        <td className="py-3 px-4 font-mono">
                          {st.static_crop.x}, {st.static_crop.y}, {st.static_crop.width}, {st.static_crop.height}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                              st.is_active
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {st.is_active ? "Active" : "Disabled"}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => handleToggle(st.code, st.is_active)}
                            className="text-[11px] px-2.5 py-1 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
                          >
                            {st.is_active ? "Disable" : "Enable"}
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
