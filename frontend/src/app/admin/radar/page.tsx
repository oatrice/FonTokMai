"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Header } from "@/components/ui/Header";
import { RadarCoverageMap, DEFAULT_STATIONS, RadarStationCoverage } from "@/components/RadarCoverageMap";
import { RadarCloudMap, CloudCluster, RadarStation } from "@/components/map/RadarCloudMap";
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
  Search,
  MessageSquare,
  Crosshair,
  Target,
  CloudRain
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
  const [activeTab, setActiveTab] = useState<"static" | "loop">("static");
  const [mapDisplayTab, setMapDisplayTab] = useState<"coverage" | "trajectory">("coverage");
  const [calculatedBbox, setCalculatedBbox] = useState<any>(null);
  const [detectedCircle, setDetectedCircle] = useState<number[] | null>(null);
  const [frozenStationCenter, setFrozenStationCenter] = useState<{ cx: number; cy: number } | null>(null);

  const DEMO_CLUSTERS: CloudCluster[] = [
    {
      id: "cluster-kkn-storm",
      label: "Maha Sarakham Storm Cell",
      lat: 16.05,
      lng: 103.30,
      cx: 362,
      cy: 242,
      radius: 22,
      intensity_dbz: 52.0,
      velocity_kmh: 35.0,
      heading_deg: 75,
      eta_min: 15,
      history_trajectory: [
        { time_offset_min: -45, lat: 15.52, lng: 102.10, cx: 295, cy: 275, dbz: 42.0 },
        { time_offset_min: -30, lat: 15.82, lng: 102.35, cx: 310, cy: 252, dbz: 46.0 },
        { time_offset_min: -15, lat: 15.70, lng: 102.85, cx: 338, cy: 262, dbz: 49.0 },
        { time_offset_min: -5, lat: 16.00, lng: 103.10, cx: 352, cy: 246, dbz: 51.5 },
      ],
      sub_clusters: [
        {
          id: "sub-kkn-muang",
          label: "อ.เมืองมหาสารคาม (Core A)",
          lat: 16.18,
          lng: 103.30,
          radius: 13,
          intensity_dbz: 52.0,
          velocity_kmh: 36.0,
          heading_deg: 72,
          history_trajectory: [
            { time_offset_min: -15, lat: 15.85, lng: 102.88, dbz: 49.5 },
            { time_offset_min: -5, lat: 16.12, lng: 103.12, dbz: 51.5 },
          ],
        },
        {
          id: "sub-kkn-borabue",
          label: "อ.บรบือ (Cell B)",
          lat: 15.98,
          lng: 103.12,
          radius: 12,
          intensity_dbz: 46.5,
          velocity_kmh: 32.0,
          heading_deg: 80,
          history_trajectory: [
            { time_offset_min: -15, lat: 15.68, lng: 102.72, dbz: 43.0 },
            { time_offset_min: -5, lat: 15.90, lng: 102.98, dbz: 45.0 },
          ],
        },
        {
          id: "sub-kkn-kosum",
          label: "อ.โกสุมพิสัย (Cell C)",
          lat: 16.25,
          lng: 103.06,
          radius: 11,
          intensity_dbz: 41.0,
          velocity_kmh: 34.0,
          heading_deg: 65,
          history_trajectory: [
            { time_offset_min: -15, lat: 15.92, lng: 102.65, dbz: 38.0 },
            { time_offset_min: -5, lat: 16.18, lng: 102.88, dbz: 40.0 },
          ],
        },
      ],
    },
    {
      id: "cluster-skn-band",
      label: "Nakhon Phanom Rain Band",
      lat: 17.48,
      lng: 104.75,
      cx: 446,
      cy: 168,
      radius: 19,
      intensity_dbz: 38.0,
      velocity_kmh: 28.0,
      heading_deg: 115,
      eta_min: 25,
      history_trajectory: [
        { time_offset_min: -45, lat: 17.98, lng: 103.70, cx: 388, cy: 138, dbz: 32.0 },
        { time_offset_min: -30, lat: 17.68, lng: 103.95, cx: 402, cy: 160, dbz: 35.0 },
        { time_offset_min: -15, lat: 17.85, lng: 104.35, cx: 424, cy: 147, dbz: 37.0 },
        { time_offset_min: -5, lat: 17.58, lng: 104.58, cx: 437, cy: 164, dbz: 37.8 },
      ],
      sub_clusters: [
        {
          id: "sub-skn-thatphanom",
          label: "อ.ธาตุพนม (Rainband South)",
          lat: 16.94,
          lng: 104.71,
          radius: 11,
          intensity_dbz: 38.0,
          velocity_kmh: 29.0,
          heading_deg: 120,
        },
        {
          id: "sub-skn-mueang",
          label: "อ.เมืองนครพนม (Rainband North)",
          lat: 17.40,
          lng: 104.78,
          radius: 12,
          intensity_dbz: 35.5,
          velocity_kmh: 26.5,
          heading_deg: 110,
        },
      ],
    },
    {
      id: "cluster-south-cell",
      label: "Buriram Inbound Cell",
      lat: 14.72,
      lng: 102.95,
      cx: 342,
      cy: 312,
      radius: 17,
      intensity_dbz: 42.5,
      velocity_kmh: 24.0,
      heading_deg: 60,
      eta_min: 35,
      history_trajectory: [
        { time_offset_min: -45, lat: 14.15, lng: 102.20, cx: 302, cy: 346, dbz: 36.0 },
        { time_offset_min: -30, lat: 14.65, lng: 102.35, cx: 310, cy: 316, dbz: 38.5 },
        { time_offset_min: -15, lat: 14.35, lng: 102.70, cx: 328, cy: 334, dbz: 40.5 },
        { time_offset_min: -5, lat: 14.60, lng: 102.88, cx: 338, cy: 319, dbz: 41.8 },
      ],
      sub_clusters: [
        {
          id: "sub-brm-prakhonchai",
          label: "อ.ประโคนชัย (Front Core)",
          lat: 14.62,
          lng: 103.12,
          radius: 11,
          intensity_dbz: 42.5,
          velocity_kmh: 25.0,
          heading_deg: 58,
        },
        {
          id: "sub-brm-nangrong",
          label: "อ.นางรอง (Rear Flank)",
          lat: 14.63,
          lng: 102.78,
          radius: 10,
          intensity_dbz: 39.0,
          velocity_kmh: 23.0,
          heading_deg: 64,
        },
      ],
    },
  ];

  // Interactive Mouse Drag & Handles State
  const imgRef = useRef<HTMLImageElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [currentDragBox, setCurrentDragBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const [activeHandle, setActiveHandle] = useState<string | null>(null);
  const [handleDragStart, setHandleDragStart] = useState<{
    mouseX: number;
    mouseY: number;
    initX: number;
    initY: number;
    initW: number;
    initH: number;
    natW: number;
    natH: number;
  } | null>(null);

  // Hover Crosshair & Coordinate Inspector
  const [hoverPos, setHoverPos] = useState<{ pixelX: number; pixelY: number; relX: number; relY: number } | null>(null);

  const calibrationSectionRef = useRef<HTMLDivElement>(null);
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";

  const [liveClusters, setLiveClusters] = useState<CloudCluster[]>([]);
  const [modalStation, setModalStation] = useState<any | null>(null);

  // Helper to resolve exact live TMD radar image URL with guaranteed fallbacks
  const getStationImageUrl = (st: any): string => {
    if (st.static_image_url) return st.static_image_url;
    if (st.image_url) return st.image_url;
    const code = (st.code || "").toLowerCase();
    if (code.includes("skn")) return "https://weather.tmd.go.th/skn/skn240_latest.jpg";
    if (code.includes("srt")) return "https://weather.tmd.go.th/srt/srt240_latest.png";
    if (code.includes("tak")) return "https://weather.tmd.go.th/tak/tak240_latest.jpg";
    if (code.includes("cri")) return "https://weather.tmd.go.th/cri/cri240_latest.jpg";
    if (code.includes("hyi")) return "https://weather.tmd.go.th/hyi/hyi240_latest.jpg";
    if (code.includes("ryg")) return "https://weather.tmd.go.th/ryg/ryg240_latest.jpg";
    if (code.includes("chn")) return "https://weather.tmd.go.th/chn/chn240_latest.gif";
    if (code.includes("kkn")) return "https://weather.tmd.go.th/kkn/kkn240_latest.gif";
    if (code.includes("svp")) return "https://weather.tmd.go.th/svp/svp240_latest.jpg";
    if (code.includes("phs")) return "https://weather.tmd.go.th/phs/phs240_latest.jpg";
    if (code.includes("ubn")) return "https://weather.tmd.go.th/ubn/ubn240_latest.jpg";
    if (code.includes("cmp")) return "https://weather.tmd.go.th/cmp/cmp240_latest.jpg";
    if (code.includes("cmi")) return "https://weather.tmd.go.th/cmi/cmi240_latest.jpg";
    return `https://weather.tmd.go.th/${code}/${code}240_latest.jpg`;
  };

  // Fetch DB Stations, Live Statuses and Presets
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
        setStations(Array.isArray(dbData) ? dbData : (dbData?.stations || []));
      }
      if (statusRes.ok) {
        const stData = await statusRes.json();
        setStationStatuses(Array.isArray(stData) ? stData : (stData?.stations || []));
        if (stData?.clusters && Array.isArray(stData.clusters) && stData.clusters.length > 0) {
          setLiveClusters(stData.clusters);
        }
      }
      if (presetsRes.ok) {
        const prData = await presetsRes.json();
        setPresets(Array.isArray(prData) ? prData : (prData?.presets || []));
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
        } else {
          const cx = data.crop_info.static_crop_x + data.crop_info.static_crop_width / 2;
          const cy = data.crop_info.static_crop_y + data.crop_info.static_crop_height / 2;
          setFrozenStationCenter({ cx, cy });
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

  // Natural Coordinates Helpers for Mouse Dragging & Resizing
  const getNaturalCoords = (e: React.MouseEvent | MouseEvent) => {
    if (!imgRef.current) return { x: 0, y: 0 };
    const rect = imgRef.current.getBoundingClientRect();
    const naturalWidth = imgRef.current.naturalWidth || 800;
    const naturalHeight = imgRef.current.naturalHeight || 800;

    const scaleX = naturalWidth / rect.width;
    const scaleY = naturalHeight / rect.height;

    const clientX = e.clientX;
    const clientY = e.clientY;

    const x = Math.max(0, Math.min(naturalWidth, Math.round((clientX - rect.left) * scaleX)));
    const y = Math.max(0, Math.min(naturalHeight, Math.round((clientY - rect.top) * scaleY)));

    return { x, y };
  };

  const startHandleDrag = (handle: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setActiveHandle(handle);

    const coords = getNaturalCoords(e);
    const natW = imgRef.current?.naturalWidth || 800;
    const natH = imgRef.current?.naturalHeight || 800;

    const initX = activeTab === "loop" ? (cropX ?? 0) + loopOffsetX : (cropX ?? 0);
    const initY = activeTab === "loop" ? (cropY ?? 0) + loopOffsetY : (cropY ?? 0);
    const initW = activeTab === "loop" ? (cropW ?? natW) + loopOffsetW : (cropW ?? natW);
    const initH = activeTab === "loop" ? (cropH ?? natH) + loopOffsetH : (cropH ?? natH);

    setHandleDragStart({
      mouseX: coords.x,
      mouseY: coords.y,
      initX,
      initY,
      initW,
      initH,
      natW,
      natH,
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

  const handleMouseMove = (e: React.MouseEvent<HTMLImageElement>) => {
    const coords = getNaturalCoords(e);
    if (imgRef.current) {
      const rect = imgRef.current.getBoundingClientRect();
      const relX = e.clientX - rect.left;
      const relY = e.clientY - rect.top;
      setHoverPos({ pixelX: coords.x, pixelY: coords.y, relX, relY });
    }
  };

  // Global Window-level MouseMove & MouseUp listeners
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
          newW = Math.max(20, Math.min(natW - handleDragStart.initX, handleDragStart.initW + dx));
        }
        if (activeHandle.includes("top")) {
          newY = Math.max(0, Math.min(handleDragStart.initY + handleDragStart.initH - 20, handleDragStart.initY + dy));
          newH = handleDragStart.initY + handleDragStart.initH - newY;
        }
        if (activeHandle.includes("bottom")) {
          newH = Math.max(20, Math.min(natH - handleDragStart.initY, handleDragStart.initH + dy));
        }

        if (activeTab === "loop") {
          setLoopOffsetX(newX - (cropX ?? 0));
          setLoopOffsetY(newY - (cropY ?? 0));
          setLoopOffsetW(newW - (cropW ?? 800));
          setLoopOffsetH(newH - (cropH ?? 800));
        } else {
          setCropX(newX);
          setCropY(newY);
          setCropW(newW);
          setCropH(newH);
        }
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
      } else if (isDragging) {
        setIsDragging(false);
        setActiveHandle(null);
        if (currentDragBox && currentDragBox.w > 10 && currentDragBox.h > 10) {
          if (activeTab === "loop") {
            setLoopOffsetX(currentDragBox.x - (cropX ?? 0));
            setLoopOffsetY(currentDragBox.y - (cropY ?? 0));
            setLoopOffsetW(currentDragBox.w - (cropW ?? 800));
            setLoopOffsetH(currentDragBox.h - (cropH ?? 800));
          } else {
            setCropX(currentDragBox.x);
            setCropY(currentDragBox.y);
            setCropW(currentDragBox.w);
            setCropH(currentDragBox.h);
          }
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
  }, [isDragging, activeHandle, handleDragStart, dragStart, cropX, cropY, cropW, cropH, currentDragBox, activeTab, loopOffsetX, loopOffsetY, loopOffsetW, loopOffsetH]);

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

  // Calculate visual style for dragging overlay box
  const getDragOverlayStyle = (): React.CSSProperties => {
    if (!currentDragBox || !imgRef.current) return { display: "none" };
    const rect = imgRef.current.getBoundingClientRect();
    const naturalWidth = imgRef.current.naturalWidth || 800;
    const naturalHeight = imgRef.current.naturalHeight || 800;

    const scaleX = rect.width / naturalWidth;
    const scaleY = rect.height / naturalHeight;

    return {
      position: "absolute",
      left: `${currentDragBox.x * scaleX}px`,
      top: `${currentDragBox.y * scaleY}px`,
      width: `${currentDragBox.w * scaleX}px`,
      height: `${currentDragBox.h * scaleY}px`,
      border: "2px dashed #f59e0b",
      backgroundColor: "rgba(245, 158, 11, 0.2)",
      pointerEvents: "none",
      zIndex: 10,
    };
  };

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
            <div className="text-3xl font-extrabold text-white mt-1">
              {tableLoading ? (
                <div className="h-8 w-12 bg-slate-800 rounded animate-pulse my-0.5" />
              ) : (
                stations.length || 13
              )}
            </div>
          </div>
          <div className="bg-emerald-950/20 border border-emerald-800/40 rounded-2xl p-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> Online (&lt;30m)
            </span>
            <div className="text-3xl font-extrabold text-emerald-300 mt-1">
              {tableLoading ? (
                <div className="h-8 w-12 bg-emerald-900/40 rounded animate-pulse my-0.5" />
              ) : (
                onlineCount
              )}
            </div>
          </div>
          <div className="bg-amber-950/20 border border-amber-800/40 rounded-2xl p-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" /> Delayed
            </span>
            <div className="text-3xl font-extrabold text-amber-300 mt-1">
              {tableLoading ? (
                <div className="h-8 w-12 bg-amber-900/40 rounded animate-pulse my-0.5" />
              ) : (
                delayedCount
              )}
            </div>
          </div>
          <div className="bg-rose-950/20 border border-rose-800/40 rounded-2xl p-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
              <XCircle className="w-3.5 h-3.5" /> Offline
            </span>
            <div className="text-3xl font-extrabold text-rose-300 mt-1">
              {tableLoading ? (
                <div className="h-8 w-12 bg-rose-900/40 rounded animate-pulse my-0.5" />
              ) : (
                offlineCount
              )}
            </div>
          </div>
        </div>

        {/* Section 2: Interactive SVG Thailand Nationwide Map (Live Status Aware & Cloud Trajectory) */}
        <section className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 shadow-2xl backdrop-blur">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
                1. แผนที่เรดาร์และขอบเขตความคุ้มครองประเทศไทย (Nationwide SVG Coverage & Live Status)
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                {mapDisplayTab === "coverage" ? (
                  <>💡 <b>เคล็ดลับ:</b> สีของหมุดและวงรัศมีจะแสดงสถานะสด (เขียว = Online, ส้ม = Delayed, แดง = Offline) คลิกเพื่อปรับจูนได้ทันที</>
                ) : (
                  <>🌧️ <b>Issue #188:</b> นำเมาส์ไปชี้ (Hover) ที่ก้อนเมฆเพื่อดูเส้นทางเดินย้อนหลัง (Historical Trajectory Vectors) ในอดีต</>
                )}
              </p>
            </div>

            {/* Map View Switcher Tabs */}
            <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-950/80 border border-slate-800 text-xs">
              <button
                onClick={() => setMapDisplayTab("coverage")}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition-all ${
                  mapDisplayTab === "coverage"
                    ? "bg-sky-600 text-white font-semibold shadow-md shadow-sky-600/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>13 สถานีเรดาร์ (Coverage)</span>
              </button>
              <button
                onClick={() => setMapDisplayTab("trajectory")}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition-all ${
                  mapDisplayTab === "trajectory"
                    ? "bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <CloudRain className="w-3.5 h-3.5" />
                <span>วิเคราะห์ทิศทางเมฆฝน (Hover Trajectory)</span>
              </button>
            </div>
          </div>

          {mapDisplayTab === "coverage" ? (
            <RadarCoverageMap
              stations={
                stations.length > 0
                  ? stations.map((s) => {
                      const stStatus = stationStatuses.find(st => st.code === s.code);
                      return {
                        code: s.code,
                        name: s.name,
                        center_lat: s.center_lat,
                        center_lng: s.center_lng,
                        radius_km: s.radius_km,
                        is_active: s.is_active,
                        status: stStatus ? stStatus.status : (s.is_active ? "online" : "offline"),
                        latency_minutes: stStatus?.latency_minutes,
                        last_frame_timestamp: stStatus?.last_frame_timestamp,
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
                      };
                    })
                  : DEFAULT_STATIONS
              }
              onSelectStation={(stCode) => {
                const found = stations.find((s) => s.code === stCode);
                if (found) {
                  handleSelectStation(found);
                }
              }}
            />
          ) : (
            <RadarCloudMap
              stations={
                (stations.length > 0 ? stations : DEFAULT_STATIONS)
                  .filter((s) => s.is_active && s.code !== "kkn120")
                  .map((s) => {
                    const stStatus = stationStatuses.find(st => st.code === s.code);
                    return {
                      code: s.code,
                      name: s.name,
                      center_lat: s.center_lat,
                      center_lng: s.center_lng,
                      radius_km: s.radius_km,
                      status: (stStatus?.status || (s.is_active ? "online" : "offline")) as "online" | "delayed" | "offline",
                      latency_minutes: stStatus?.latency_minutes || 0,
                      last_frame_timestamp: stStatus?.last_frame_timestamp || new Date().toISOString(),
                    };
                  })
              }
              clusters={liveClusters.length > 0 ? liveClusters : DEMO_CLUSTERS}
              selectedStationCode={code}
              onSelectStation={(st) => {
                const found = stations.find((s) => s.code === st.code);
                if (found) {
                  handleSelectStation(found);
                }
              }}
            />
          )}
        </section>

        {/* Section 2.5: Nationwide Real Radar Imagery vs SVG Contour Verification Gallery */}
        <section className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 shadow-2xl backdrop-blur space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Radio className="w-5 h-5 text-cyan-400" />
                ภาพเรดาร์ตรวจอากาศจริง 13 สถานีทั่วประเทศ vs ขอบเขตกลุ่มฝนที่สกัดได้ (Live Radar Contour Verification)
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                เปรียบเทียบภาพเรดาร์จริง (TMD Raw Frames) กับรัศมีและกลุ่มฝนที่ระบบสกัดได้ เพื่อตรวจสอบความถูกต้องของการตรวจจับแบบ Real-Time
              </p>
            </div>
            <div className="text-xs text-slate-400 bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span>คลิกที่การ์ดเพื่อเลือกสถานีไปปรับจูนได้ทันที</span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 pt-2">
            {(stations.length > 0 ? stations : DEFAULT_STATIONS)
              .filter((s) => s.code !== "kkn120")
              .map((st) => {
                const stStatus = stationStatuses.find((s) => s.code === st.code);
                const isSelected = code === st.code;
                const stationClusters = (liveClusters.length > 0 ? liveClusters : DEMO_CLUSTERS).filter((c) => {
                  if (c.lat === undefined || c.lng === undefined) return false;
                  const dist = Math.hypot(c.lat - st.center_lat, c.lng - st.center_lng);
                  return dist <= 2.2; // approx within 240km
                });

                const imgSrc = getStationImageUrl(st);

                return (
                  <div
                    key={st.code}
                    onClick={() => setModalStation(st)}
                    className={`group relative flex flex-col rounded-2xl border transition-all duration-200 overflow-hidden cursor-pointer ${
                      isSelected
                        ? "bg-slate-900 border-sky-500 shadow-lg shadow-sky-500/10 ring-1 ring-sky-500"
                        : "bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/80"
                    }`}
                  >
                    {/* Header */}
                    <div className="p-3 bg-slate-900/90 border-b border-slate-800/80 flex items-center justify-between">
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className={`w-2 h-2 rounded-full flex-shrink-0 ${
                            stStatus?.status === "online"
                              ? "bg-emerald-400 shadow-[0_0_8px_#34d399]"
                              : stStatus?.status === "delayed"
                              ? "bg-amber-400"
                              : "bg-rose-400"
                          }`}
                        />
                        <span className="text-xs font-bold text-slate-200 truncate">{st.name.split("/")[0]}</span>
                      </div>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-sky-400 font-semibold uppercase">
                        {st.code}
                      </span>
                    </div>

                    {/* Image Preview with Real SVG Contour Overlay */}
                    <div className="relative aspect-square w-full bg-slate-950 flex items-center justify-center overflow-hidden">
                      <img
                        src={imgSrc}
                        alt={st.name}
                        className="w-full h-full object-contain filter group-hover:scale-105 transition-transform duration-300"
                      />

                      {/* SVG Contour & Vector Overlay directly on radar image (Telegram-style Neon) */}
                      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100">
                        <defs>
                          <filter id={`neonGlowGal-${st.code}`} x="-50%" y="-50%" width="200%" height="200%">
                            <feGaussianBlur in="SourceGraphic" stdDeviation="1.8" result="blur1" />
                            <feGaussianBlur in="SourceGraphic" stdDeviation="0.8" result="blur2" />
                            <feMerge>
                              <feMergeNode in="blur1" />
                              <feMergeNode in="blur2" />
                              <feMergeNode in="SourceGraphic" />
                            </feMerge>
                          </filter>
                        </defs>

                        {/* Station Center Indicator */}
                        <circle cx="50" cy="50" r="1.5" fill="#38bdf8" stroke="#ffffff" strokeWidth="0.5" />
                        <circle cx="50" cy="50" r="45" fill="none" stroke="#38bdf8" strokeWidth="0.5" strokeDasharray="2 2" strokeOpacity="0.4" />

                        {/* Rain Clusters Projected onto Radar Polar Space */}
                        {stationClusters.map((cl) => {
                          const dLat = (cl.lat ?? st.center_lat) - st.center_lat;
                          const dLng = (cl.lng ?? st.center_lng) - st.center_lng;
                          const normX = 50 + (dLng / 2.2) * 45;
                          const normY = 50 - (dLat / 2.2) * 45;
                          const normR = Math.max(3, (cl.radius / 24) * 8);

                          // Generate organic polygon path
                          const vertices = 8;
                          const polyPts: string[] = [];
                          for (let i = 0; i < vertices; i++) {
                            const angle = (i / vertices) * Math.PI * 2;
                            const noiseFactor = 1 + Math.sin(i * 2.5 + (cl.id.charCodeAt(cl.id.length - 1) % 5)) * 0.15;
                            const vx = normX + Math.cos(angle) * (normR * noiseFactor);
                            const vy = normY + Math.sin(angle) * (normR * noiseFactor);
                            polyPts.push(`${vx.toFixed(1)},${vy.toFixed(1)}`);
                          }
                          const polyD = `M ${polyPts.join(" L ")} Z`;

                          return (
                            <g key={cl.id}>
                              {/* Layer 1: Semi-transparent Fill */}
                              <path d={polyD} fill="#f43f5e" fillOpacity="0.35" />
                              
                              {/* Layer 2: Glowing Multi-Pass Neon Border */}
                              <path d={polyD} fill="none" stroke="#f43f5e" strokeWidth="2.2" strokeOpacity="0.8" strokeLinejoin="round" filter={`url(#neonGlowGal-${st.code})`} />

                              {/* Layer 3: Sharp Inner White Core */}
                              <path
                                d={polyD}
                                fill="none"
                                stroke="#ffffff"
                                strokeWidth="0.8"
                                strokeOpacity="0.95"
                                strokeLinejoin="round"
                              />

                              {/* Velocity Heading Vector Arrow */}
                              {(() => {
                                const rad = ((cl.heading_deg ?? 90) - 90) * (Math.PI / 180);
                                const tox = normX + Math.cos(rad) * 7;
                                const toy = normY + Math.sin(rad) * 7;
                                return (
                                    <line
                                      x1={normX}
                                      y1={normY}
                                      x2={tox}
                                      y2={toy}
                                      stroke="#38bdf8"
                                      strokeWidth="1.2"
                                    />
                                  );
                                })()}
                              </g>
                            );
                          })}
                        </svg>
                      
                      {/* Live Rain Detected Badge */}
                      {stationClusters.length > 0 ? (
                        <div className="absolute bottom-2 left-2 right-2 bg-slate-950/90 backdrop-blur border border-rose-500/50 rounded-xl p-2 text-xs flex items-center justify-between shadow-lg">
                          <div className="flex items-center gap-1.5 text-rose-300 font-medium">
                            <CloudRain className="w-3.5 h-3.5 text-rose-400 animate-bounce" />
                            <span>Contour {stationClusters.length} จุด</span>
                          </div>
                          <span className="text-[10px] font-bold text-amber-300 bg-amber-950/60 px-1.5 py-0.5 rounded">
                            {Math.max(...stationClusters.map((c) => c.intensity_dbz)).toFixed(0)} dBZ
                          </span>
                        </div>
                      ) : (
                        <div className="absolute bottom-2 left-2 bg-slate-950/80 backdrop-blur border border-slate-800 rounded-lg px-2 py-1 text-[10px] text-slate-400">
                          ☀️ ท้องฟ้าแจ่มใส / ไม่มีกลุ่มฝน
                        </div>
                      )}
                    </div>

                    {/* Footer Info */}
                    <div className="p-2.5 bg-slate-900/40 text-[11px] text-slate-400 flex items-center justify-between border-t border-slate-800/60">
                      <span>รัศมี {st.radius_km} km</span>
                      <span className="text-sky-400 hover:underline font-semibold flex items-center gap-1">
                        🔍 ดูขนาดเต็ม
                      </span>
                    </div>
                  </div>
                );
              })}
          </div>
        </section>

        {/* Full-Screen Radar Image & Contour Modal */}
        {modalStation && (
          <div
            className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-200"
            onClick={() => setModalStation(null)}
          >
            <div
              className="bg-slate-900 border border-slate-700 rounded-3xl max-w-4xl w-full p-6 shadow-2xl space-y-4 relative flex flex-col max-h-[90vh]"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-3">
                  <span className="p-2 rounded-xl bg-sky-500/20 text-sky-400">
                    <Radio className="w-6 h-6" />
                  </span>
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      {modalStation.name}
                      <span className="text-xs font-mono px-2 py-0.5 bg-slate-800 text-sky-400 rounded-lg">
                        {modalStation.code}
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      พิกัดจุดศูนย์กลาง: Lat {modalStation.center_lat}, Lng {modalStation.center_lng} (รัศมี {modalStation.radius_km} km)
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setModalStation(null)}
                  className="w-8 h-8 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center transition-all"
                >
                  ✕
                </button>
              </div>

              {/* Full Image Container with High-Res Overlays */}
              <div className="relative flex-1 min-h-[400px] bg-slate-950 rounded-2xl flex items-center justify-center overflow-hidden border border-slate-800">
                <img
                  src={getStationImageUrl(modalStation)}
                  alt={modalStation.name}
                  className="w-full h-full max-h-[65vh] object-contain"
                />

                {/* SVG Overlay on Full Image (Telegram-style Multi-Pass Neon) */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100">
                  <defs>
                    <filter id="modalNeonGlow" x="-50%" y="-50%" width="200%" height="200%">
                      <feGaussianBlur in="SourceGraphic" stdDeviation="2.2" result="blur1" />
                      <feGaussianBlur in="SourceGraphic" stdDeviation="1.0" result="blur2" />
                      <feMerge>
                        <feMergeNode in="blur1" />
                        <feMergeNode in="blur2" />
                        <feMergeNode in="SourceGraphic" />
                      </feMerge>
                    </filter>
                  </defs>

                  <circle cx="50" cy="50" r="1.5" fill="#38bdf8" stroke="#ffffff" strokeWidth="0.5" />
                  <circle cx="50" cy="50" r="45" fill="none" stroke="#38bdf8" strokeWidth="0.6" strokeDasharray="3 3" strokeOpacity="0.5" />

                  {(liveClusters.length > 0 ? liveClusters : DEMO_CLUSTERS)
                    .filter((c) => {
                      if (c.lat === undefined || c.lng === undefined) return false;
                      return Math.hypot(c.lat - modalStation.center_lat, c.lng - modalStation.center_lng) <= 2.2;
                    })
                    .map((cl) => {
                      const dLat = (cl.lat ?? modalStation.center_lat) - modalStation.center_lat;
                      const dLng = (cl.lng ?? modalStation.center_lng) - modalStation.center_lng;
                      const normX = 50 + (dLng / 2.2) * 45;
                      const normY = 50 - (dLat / 2.2) * 45;
                      const normR = Math.max(3.5, (cl.radius / 24) * 8);

                      // Organic polygon contour matching real radar rain formation
                      const vertices = 8;
                      const polyPts: string[] = [];
                      for (let i = 0; i < vertices; i++) {
                        const angle = (i / vertices) * Math.PI * 2;
                        const noiseFactor = 1 + Math.sin(i * 2.5 + (cl.id.charCodeAt(cl.id.length - 1) % 5)) * 0.15;
                        const vx = normX + Math.cos(angle) * (normR * noiseFactor);
                        const vy = normY + Math.sin(angle) * (normR * noiseFactor);
                        polyPts.push(`${vx.toFixed(1)},${vy.toFixed(1)}`);
                      }
                      const polyD = `M ${polyPts.join(" L ")} Z`;

                      return (
                        <g key={cl.id}>
                          {/* Layer 1: Semi-transparent Inner Area */}
                          <path d={polyD} fill="#f43f5e" fillOpacity="0.35" />
                          
                          {/* Layer 2: Glowing Multi-Pass Neon Border */}
                          <path
                            d={polyD}
                            fill="none"
                            stroke="#f43f5e"
                            strokeWidth="2.4"
                            strokeOpacity="0.85"
                            strokeLinejoin="round"
                            filter="url(#modalNeonGlow)"
                          />

                          {/* Layer 3: Sharp Inner White Core */}
                          <path
                            d={polyD}
                            fill="none"
                            stroke="#ffffff"
                            strokeWidth="0.9"
                            strokeOpacity="0.95"
                            strokeLinejoin="round"
                          />

                          {/* dBZ Label Badge */}
                          <text
                            x={normX}
                            y={normY - normR - 1.8}
                            textAnchor="middle"
                            fill="#ffffff"
                            fontSize="2.8"
                            fontWeight="bold"
                            style={{ paintOrder: "stroke fill", stroke: "#000000", strokeWidth: "0.8px" }}
                          >
                            {cl.label.split(" ")[0]} ({cl.intensity_dbz.toFixed(0)} dBZ)
                          </text>
                        </g>
                      );
                    })}
                </svg>
              </div>

              {/* Modal Actions */}
              <div className="flex items-center justify-between pt-2">
                <a
                  href={getStationImageUrl(modalStation)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-sky-400 hover:text-sky-300 underline font-medium"
                >
                  🔗 เปิดไฟล์ภาพต้นฉบับตรงจาก TMD Server
                </a>
                <button
                  onClick={() => {
                    const found = stations.find((s) => s.code === modalStation.code);
                    if (found) {
                      handleSelectStation(found);
                      setModalStation(null);
                    }
                  }}
                  className="bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all shadow-md shadow-sky-600/20"
                >
                  🎯 นำสถานีนี้ไปปรับจูนพิกัดในเครื่องมือด้านล่าง
                </button>
              </div>
            </div>
          </div>
        )}

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
                  {Array.isArray(presets) ? presets.map((p) => (
                    <option key={p.code} value={p.code}>
                      {p.name} [{p.code}] (Lat: {p.center_lat}, Lng: {p.center_lng})
                    </option>
                  )) : null}
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

            {/* Live Image Preview Column & Interactive Mouse Drag */}
            <div className="lg:col-span-6 bg-slate-900/60 border border-slate-800 rounded-3xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-sky-400" />
                  ภาพพรีวิวขอบเขต & Interactive Mouse Crop
                </h3>
                <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
                  <button
                    onClick={() => setActiveTab("static")}
                    className={`px-3 py-1 rounded-md transition ${activeTab === "static" ? "bg-sky-600 text-white font-semibold" : "text-slate-400"}`}
                  >
                    📷 Static Frame
                  </button>
                  <button
                    onClick={() => setActiveTab("loop")}
                    disabled={!loopPreviewB64}
                    className={`px-3 py-1 rounded-md transition ${activeTab === "loop" ? "bg-sky-600 text-white font-semibold" : "text-slate-400 disabled:opacity-40"}`}
                  >
                    🌀 Loop GIF
                  </button>
                </div>
              </div>

              {/* Interactive Image Container with Crosshair & Resizable Box */}
              <div className="relative border border-slate-800 rounded-2xl overflow-hidden bg-slate-950 flex items-center justify-center min-h-[380px] p-2">
                {previewB64 ? (
                  <div className="relative inline-block select-none cursor-crosshair">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      ref={imgRef}
                      src={activeTab === "loop" && loopPreviewB64 ? loopPreviewB64 : previewB64}
                      alt="Radar Preview"
                      onMouseDown={handleMouseDown}
                      onMouseMove={handleMouseMove}
                      onMouseLeave={() => setHoverPos(null)}
                      className="max-w-full max-h-[460px] object-contain block rounded-lg"
                    />

                    {/* Laser Crosshair Guide Lines on Hover */}
                    {hoverPos && (
                      <>
                        <div
                          style={{
                            position: "absolute",
                            top: 0,
                            bottom: 0,
                            left: `${hoverPos.relX}px`,
                            width: "1px",
                            borderLeft: "2px dashed #ef4444",
                            pointerEvents: "none",
                            zIndex: 8,
                          }}
                        />
                        <div
                          style={{
                            position: "absolute",
                            left: 0,
                            right: 0,
                            top: `${hoverPos.relY}px`,
                            height: "1px",
                            borderTop: "2px dashed #ef4444",
                            pointerEvents: "none",
                            zIndex: 8,
                          }}
                        />
                        {/* Live Coordinates Tooltip */}
                        {(() => {
                          const targetCropX = activeTab === "loop" ? (cropX ?? 0) + loopOffsetX : (cropX ?? 0);
                          const targetCropY = activeTab === "loop" ? (cropY ?? 0) + loopOffsetY : (cropY ?? 0);
                          const targetCropW = cropW ?? 800;
                          const targetCropH = cropH ?? 800;

                          const cropRelX = hoverPos.pixelX - targetCropX;
                          const cropRelY = hoverPos.pixelY - targetCropY;
                          const inCrop = cropRelX >= 0 && cropRelX <= targetCropW && cropRelY >= 0 && cropRelY <= targetCropH;

                          return (
                            <div
                              style={{
                                position: "absolute",
                                left: `${Math.min(hoverPos.relX + 15, (imgRef.current?.getBoundingClientRect().width || 400) - 270)}px`,
                                top: `${Math.max(hoverPos.relY - 50, 8)}px`,
                                backgroundColor: inCrop ? "rgba(14, 165, 233, 0.95)" : "rgba(15, 23, 42, 0.95)",
                                color: "#ffffff",
                                fontSize: "0.72rem",
                                fontWeight: 600,
                                padding: "4px 10px",
                                borderRadius: 6,
                                pointerEvents: "none",
                                zIndex: 12,
                                fontFamily: "monospace",
                                boxShadow: "0 6px 16px rgba(0,0,0,0.5)",
                                border: inCrop ? "1px solid #38bdf8" : "1px solid #475569",
                              }}
                            >
                              {inCrop ? (
                                <span>
                                  🔵 Crop: (<b>{cropRelX}</b>, <b>{cropRelY}</b>) | Full: ({hoverPos.pixelX}, {hoverPos.pixelY})
                                </span>
                              ) : (
                                <span>
                                  ⚪ Full Radar: ({hoverPos.pixelX}, {hoverPos.pixelY})
                                </span>
                              )}
                            </div>
                          );
                        })()}
                      </>
                    )}

                    {/* Dynamic Drag Box Overlay */}
                    <div style={getDragOverlayStyle()} />

                    {/* Active Crop Box with Interactive 4-Edge & 4-Corner Handles */}
                    {cropX !== null && cropY !== null && cropW !== null && cropH !== null && imgRef.current && (
                      (() => {
                        const targetCropX = activeTab === "loop" ? (cropX ?? 0) + loopOffsetX : cropX;
                        const targetCropY = activeTab === "loop" ? (cropY ?? 0) + loopOffsetY : cropY;
                        const targetCropW = activeTab === "loop" ? (cropW ?? 800) + loopOffsetW : cropW;
                        const targetCropH = activeTab === "loop" ? (cropH ?? 800) + loopOffsetH : cropH;

                        const rect = imgRef.current.getBoundingClientRect();
                        const scaleX = rect.width / (imgRef.current.naturalWidth || 800);
                        const scaleY = rect.height / (imgRef.current.naturalHeight || 800);
                        const boxLeft = targetCropX * scaleX;
                        const boxTop = targetCropY * scaleY;
                        const boxW = targetCropW * scaleX;
                        const boxH = targetCropH * scaleY;

                        return (
                          <div
                            style={{
                              position: "absolute",
                              left: `${boxLeft}px`,
                              top: `${boxTop}px`,
                              width: `${boxW}px`,
                              height: `${boxH}px`,
                              border: "2px solid #38bdf8",
                              backgroundColor: "rgba(56, 189, 248, 0.12)",
                              boxSizing: "border-box",
                              pointerEvents: "none",
                              zIndex: 9,
                            }}
                          >
                            {/* Edge Handles */}
                            <div onMouseDown={(e) => startHandleDrag("top", e)} style={{ position: "absolute", top: -4, left: "20%", right: "20%", height: 8, cursor: "ns-resize", backgroundColor: "rgba(56, 189, 248, 0.7)", borderRadius: 4, pointerEvents: "auto" }} />
                            <div onMouseDown={(e) => startHandleDrag("bottom", e)} style={{ position: "absolute", bottom: -4, left: "20%", right: "20%", height: 8, cursor: "ns-resize", backgroundColor: "rgba(56, 189, 248, 0.7)", borderRadius: 4, pointerEvents: "auto" }} />
                            <div onMouseDown={(e) => startHandleDrag("left", e)} style={{ position: "absolute", left: -4, top: "20%", bottom: "20%", width: 8, cursor: "ew-resize", backgroundColor: "rgba(56, 189, 248, 0.7)", borderRadius: 4, pointerEvents: "auto" }} />
                            <div onMouseDown={(e) => startHandleDrag("right", e)} style={{ position: "absolute", right: -4, top: "20%", bottom: "20%", width: 8, cursor: "ew-resize", backgroundColor: "rgba(56, 189, 248, 0.7)", borderRadius: 4, pointerEvents: "auto" }} />

                            {/* Corner Handles */}
                            <div onMouseDown={(e) => startHandleDrag("top-left", e)} style={{ position: "absolute", top: -5, left: -5, width: 10, height: 10, cursor: "nwse-resize", backgroundColor: "#0284c7", border: "1px solid #fff", borderRadius: "50%", pointerEvents: "auto" }} />
                            <div onMouseDown={(e) => startHandleDrag("top-right", e)} style={{ position: "absolute", top: -5, right: -5, width: 10, height: 10, cursor: "nesw-resize", backgroundColor: "#0284c7", border: "1px solid #fff", borderRadius: "50%", pointerEvents: "auto" }} />
                            <div onMouseDown={(e) => startHandleDrag("bottom-left", e)} style={{ position: "absolute", bottom: -5, left: -5, width: 10, height: 10, cursor: "nesw-resize", backgroundColor: "#0284c7", border: "1px solid #fff", borderRadius: "50%", pointerEvents: "auto" }} />
                            <div onMouseDown={(e) => startHandleDrag("bottom-right", e)} style={{ position: "absolute", bottom: -5, right: -5, width: 10, height: 10, cursor: "nwse-resize", backgroundColor: "#0284c7", border: "1px solid #fff", borderRadius: "50%", pointerEvents: "auto" }} />
                          </div>
                        );
                      })()
                    )}
                  </div>
                ) : (
                  <div className="text-center p-8 text-slate-500">
                    <Radio className="w-12 h-12 mx-auto mb-2 text-slate-700" />
                    <p className="text-xs">กดปุ่ม <b>"Auto-Detect"</b> หรือ <b>"Preview Sliders"</b> เพื่อโหลดภาพเรดาร์</p>
                  </div>
                )}
              </div>

              {/* Coordinates & Alignment Inspector Readout */}
              <div className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-4 space-y-3 text-xs">
                {/* Live Hover Readout */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
                  <span className="font-mono text-slate-300">
                    🖼️ Cursor Pixel: <b>{hoverPos ? `(${hoverPos.pixelX}, ${hoverPos.pixelY})` : "-"}</b> px
                  </span>
                  <span className="font-mono text-sky-400">
                    🌐 GPS: <b>{hoverCoords ? `${hoverCoords.hoverLat.toFixed(5)}°N, ${hoverCoords.hoverLng.toFixed(5)}°E` : "-"}</b>
                  </span>
                </div>

                {/* Alignment Debugger */}
                {(() => {
                  const targetCropX = activeTab === "loop" ? (cropX ?? 0) + loopOffsetX : (cropX ?? 0);
                  const targetCropY = activeTab === "loop" ? (cropY ?? 0) + loopOffsetY : (cropY ?? 0);
                  const targetCropW = cropW ?? 800;
                  const targetCropH = cropH ?? 800;

                  const cropCenterX = targetCropX + targetCropW / 2;
                  const cropCenterY = targetCropY + targetCropH / 2;

                  const radarCx = detectedCircle ? detectedCircle[0] : cropCenterX;
                  const radarCy = detectedCircle ? detectedCircle[1] : cropCenterY;

                  const dx = cropCenterX - radarCx;
                  const dy = cropCenterY - radarCy;
                  const hasDeviation = Math.abs(dx) > 0 || Math.abs(dy) > 0;

                  return (
                    <div className={`p-3 rounded-xl border ${hasDeviation ? "bg-rose-950/30 border-rose-800/50" : "bg-emerald-950/30 border-emerald-800/50"}`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className={`font-semibold flex items-center gap-1.5 ${hasDeviation ? "text-rose-300" : "text-emerald-300"}`}>
                          <Crosshair className="w-3.5 h-3.5" /> Center Radar Alignment
                        </span>
                        {hasDeviation && (
                          <button
                            onClick={() => {
                              const IMG_SIZE = 800;
                              const halfW = Math.min(targetCropW / 2, radarCx, IMG_SIZE - radarCx);
                              const halfH = Math.min(targetCropH / 2, radarCy, IMG_SIZE - radarCy);
                              const half = Math.min(halfW, halfH);
                              const newW = Math.round(half * 2);
                              const newH = Math.round(half * 2);
                              const newCropX = Math.round(radarCx - half);
                              const newCropY = Math.round(radarCy - half);
                              handlePreview(newCropX, newCropY, newW, newH);
                            }}
                            className="bg-sky-600 hover:bg-sky-500 text-white px-2.5 py-1 rounded-lg text-[10px] font-bold"
                          >
                            🎯 Auto-Center Crop Box
                          </button>
                        )}
                      </div>
                      <div className="grid grid-cols-3 gap-2 font-mono text-[11px]">
                        <div>🔵 Crop Center: <b>{cropCenterX}, {cropCenterY}</b></div>
                        <div>🔴 Radar Center: <b className="text-amber-300">{radarCx}, {radarCy}</b></div>
                        <div>⚖️ Offset: <b className={hasDeviation ? "text-rose-400" : "text-emerald-400"}>ΔX:{dx}, ΔY:{dy}</b></div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>

        {/* Section 4: Telegram Simulated UI (`/rain_pro`) Container */}
        <section className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 shadow-2xl backdrop-blur space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-sky-400" />
                3. Telegram Live Preview & Coordinate Inspector (`/rain_pro`)
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                จำลองการตัดรูปภาพและคำนวณพิกัด Pixel (X, Y) กับ Lat/Lng เสมือนส่งลงแชท Telegram จริง
              </p>
            </div>
            <span className="text-xs font-semibold px-3 py-1 rounded-lg bg-sky-950/60 border border-sky-800 text-sky-300">
              Telegram Simulated UI
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left simulated Telegram Chat Card */}
            <div className="lg:col-span-5 bg-[#17212b] border border-[#242f3d] rounded-3xl p-5 shadow-2xl space-y-4">
              <div className="flex items-center gap-3 border-b border-[#242f3d] pb-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center font-bold text-white text-sm shadow">
                  FM
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                    FonMaYang Bot <span className="text-[10px] bg-sky-500/20 text-sky-400 px-1.5 py-0.5 rounded font-mono">BOT</span>
                  </h3>
                  <span className="text-xs text-sky-400 font-mono">/rain_pro {lat.toFixed(4)} {lng.toFixed(4)}</span>
                </div>
              </div>

              {/* Telegram Cropped Image Box */}
              <div className="relative rounded-2xl overflow-hidden bg-[#0e1621] border border-[#242f3d] flex items-center justify-center min-h-[260px]">
                {telegramPreviewB64 || loopTelegramPreviewB64 ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={activeTab === "loop" && loopTelegramPreviewB64 ? loopTelegramPreviewB64 : (telegramPreviewB64 || previewB64 || "")}
                    alt="Telegram Cropped Preview"
                    className="w-full h-auto object-cover block"
                  />
                ) : (
                  <div className="text-center p-8 text-slate-500 text-xs">
                    โปรดกด Preview เพื่อดูภาพจำลองแชท Telegram
                  </div>
                )}
              </div>

              {/* Telegram Message Caption */}
              <div className="bg-[#0e1621] p-3.5 rounded-xl border border-[#242f3d] text-xs text-slate-300 space-y-1">
                <p className="font-bold text-white">🌧️ รายงานเรดาร์ติดตามกลุ่มฝน [{code}]</p>
                <p>📍 จุดศูนย์กลางเรดาร์: Lat {lat}, Lng {lng}</p>
                <p>📡 รัศมีครอบคลุม: {radiusKm} กม.</p>
                <p className="text-[11px] text-slate-500 mt-1 font-mono">Timestamp: {new Date().toISOString()}</p>
              </div>
            </div>

            {/* Right Bounding Box & Alignment Breakdown */}
            <div className="lg:col-span-7 bg-slate-950/60 border border-slate-800 rounded-3xl p-6 space-y-6">
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <Target className="w-4 h-4 text-sky-400" />
                สรุป BoundingBox & พิกัดเรดาร์ใน Neon Database
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-2xl">
                  <span className="text-xs text-slate-400 block mb-1">🎯 Center Radar Coordinates</span>
                  <div className="text-base font-bold font-mono text-white">Lat {lat}, Lng {lng}</div>
                  <span className="text-[11px] text-slate-500 block mt-1">
                    Pixel Center: X: {(cropX ?? 0) + (cropW ?? 800) / 2}, Y: {(cropY ?? 0) + (cropH ?? 800) / 2}
                  </span>
                </div>

                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-2xl">
                  <span className="text-xs text-slate-400 block mb-1">✂️ Static Crop Settings</span>
                  <div className="text-base font-bold font-mono text-sky-400">
                    X: {cropX ?? 0}, Y: {cropY ?? 0} | {cropW ?? 800}×{cropH ?? 800} px
                  </div>
                  <span className="text-[11px] text-slate-500 block mt-1">
                    Loop Offset: X: {(cropX ?? 0) + loopOffsetX}, Y: {(cropY ?? 0) + loopOffsetY}
                  </span>
                </div>
              </div>

              {/* Geographic Bounding Box */}
              <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-2xl space-y-2">
                <span className="text-xs font-semibold text-slate-300 block">
                  🗺️ Neon DB BoundingBox Coverage
                </span>
                {calculatedBbox ? (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs text-sky-300">
                    <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Top (lat_max)</span>
                      <b className="text-white text-sm">{calculatedBbox.lat_max}</b>
                    </div>
                    <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Bottom (lat_min)</span>
                      <b className="text-white text-sm">{calculatedBbox.lat_min}</b>
                    </div>
                    <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Left (lng_min)</span>
                      <b className="text-white text-sm">{calculatedBbox.lng_min}</b>
                    </div>
                    <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Right (lng_max)</span>
                      <b className="text-white text-sm">{calculatedBbox.lng_max}</b>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-500">กดปุ่ม Preview & Auto-Detect เพื่อคำนวณ BoundingBox</div>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Section 5: All Stations Table */}
        <section className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 shadow-2xl backdrop-blur">
          <h2 className="text-lg font-bold text-slate-100 mb-1 flex items-center gap-2">
            📋 4. รายการสถานีเรดาร์ทั้งหมดในระบบ ({stations.length} สถานี)
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
                    const stStatus = stationStatuses.find(s => s.code === st.code);
                    const statusLabel = stStatus?.status || (st.is_active ? "online" : "offline");

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
                              statusLabel === "online"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : statusLabel === "delayed"
                                ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            }`}
                          >
                            {statusLabel}
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
