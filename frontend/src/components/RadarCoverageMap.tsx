"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import * as d3geo from "d3-geo";
import * as turf from "@turf/turf";
import { 
  Radio, 
  MapPin, 
  Layers, 
  Compass, 
  Eye,
  EyeOff
} from "lucide-react";
import { GlassCard } from "./ui/GlassCard";
import { GlassBadge } from "./ui/GlassBadge";

export interface RadarStationCoverage {
  code: string;
  name: string;
  center_lat: number;
  center_lng: number;
  radius_km: number;
  is_active: boolean;
  region: "north" | "northeast" | "central" | "east" | "south";
}

export interface ProvinceMarker {
  code: string;
  name: string;
  lat: number;
  lng: number;
  x: number;
  y: number;
  region: string;
}

export const PROVINCE_MARKERS: ProvinceMarker[] = [
  { code: 'CMI', name: 'เชียงใหม่', lat: 18.79, lng: 98.98, x: 114.4, y: 102.5, region: 'north' },
  { code: 'CRI', name: 'เชียงราย', lat: 19.91, lng: 99.83, x: 163.5, y: 45.4, region: 'north' },
  { code: 'LPN', name: 'ลำพูน', lat: 18.57, lng: 99.01, x: 116.1, y: 113.7, region: 'north' },
  { code: 'LPG', name: 'ลำปาง', lat: 18.29, lng: 99.51, x: 145.0, y: 128.0, region: 'north' },
  { code: 'PRE', name: 'แพร่', lat: 18.14, lng: 100.14, x: 181.4, y: 135.6, region: 'north' },
  { code: 'NAN', name: 'น่าน', lat: 18.78, lng: 100.78, x: 218.4, y: 103.0, region: 'north' },
  { code: 'TAK', name: 'ตาก', lat: 16.88, lng: 99.12, x: 122.5, y: 199.8, region: 'north' },
  { code: 'UTD', name: 'อุตรดิตถ์', lat: 17.62, lng: 100.1, x: 179.1, y: 162.1, region: 'north' },
  { code: 'PHS', name: 'พิษณุโลก', lat: 16.83, lng: 100.26, x: 188.4, y: 202.4, region: 'north' },
  { code: 'SUK', name: 'สุโขทัย', lat: 17.01, lng: 99.82, x: 162.9, y: 193.2, region: 'north' },
  { code: 'PCT', name: 'พิจิตร', lat: 16.44, lng: 100.35, x: 193.6, y: 222.3, region: 'north' },
  { code: 'KPT', name: 'กำแพงเพชร', lat: 16.48, lng: 99.52, x: 145.6, y: 220.2, region: 'north' },
  { code: 'PNB', name: 'เพชรบูรณ์', lat: 16.42, lng: 101.16, x: 240.4, y: 223.3, region: 'north' },
  { code: 'NSN', name: 'นครสวรรค์', lat: 15.7, lng: 100.12, x: 180.3, y: 260.0, region: 'north' },
  { code: 'UTI', name: 'อุทัยธานี', lat: 15.38, lng: 99.72, x: 157.2, y: 276.3, region: 'north' },
  { code: 'KKN', name: 'ขอนแก่น', lat: 16.44, lng: 102.83, x: 336.8, y: 222.3, region: 'northeast' },
  { code: 'UDN', name: 'อุดรธานี', lat: 17.41, lng: 102.78, x: 334.0, y: 172.8, region: 'northeast' },
  { code: 'NKI', name: 'หนองคาย', lat: 17.88, lng: 102.74, x: 331.6, y: 148.9, region: 'northeast' },
  { code: 'NBP', name: 'หนองบัวลำภู', lat: 17.2, lng: 102.43, x: 313.7, y: 183.5, region: 'northeast' },
  { code: 'LEI', name: 'เลย', lat: 17.49, lng: 101.73, x: 273.3, y: 168.7, region: 'northeast' },
  { code: 'SKN', name: 'สกลนคร', lat: 17.16, lng: 104.15, x: 413.1, y: 185.6, region: 'northeast' },
  { code: 'NPM', name: 'นครพนม', lat: 17.39, lng: 104.78, x: 449.5, y: 173.8, region: 'northeast' },
  { code: 'MDH', name: 'มุกดาหาร', lat: 16.54, lng: 104.72, x: 446.0, y: 217.2, region: 'northeast' },
  { code: 'KSN', name: 'กาฬสินธุ์', lat: 16.43, lng: 103.51, x: 376.1, y: 222.8, region: 'northeast' },
  { code: 'MKM', name: 'มหาสารคาม', lat: 16.18, lng: 103.3, x: 364.0, y: 235.5, region: 'northeast' },
  { code: 'RET', name: 'ร้อยเอ็ด', lat: 16.05, lng: 103.65, x: 384.2, y: 242.2, region: 'northeast' },
  { code: 'YSO', name: 'ยโสธร', lat: 15.79, lng: 104.14, x: 412.5, y: 255.4, region: 'northeast' },
  { code: 'ACN', name: 'อำนาจเจริญ', lat: 15.86, lng: 104.63, x: 440.8, y: 251.8, region: 'northeast' },
  { code: 'UBN', name: 'อุบลราชธานี', lat: 15.24, lng: 104.86, x: 454.1, y: 283.5, region: 'northeast' },
  { code: 'SIS', name: 'ศรีสะเกษ', lat: 15.11, lng: 104.33, x: 423.5, y: 290.1, region: 'northeast' },
  { code: 'SRN', name: 'สุรินทร์', lat: 14.88, lng: 103.49, x: 375.0, y: 301.8, region: 'northeast' },
  { code: 'BRM', name: 'บุรีรัมย์', lat: 14.99, lng: 103.1, x: 352.4, y: 296.2, region: 'northeast' },
  { code: 'NMA', name: 'นครราชสีมา', lat: 14.97, lng: 102.1, x: 294.7, y: 297.2, region: 'northeast' },
  { code: 'BKN', name: 'บึงกาฬ', lat: 18.36, lng: 103.65, x: 384.2, y: 124.4, region: 'northeast' },
  { code: 'BKK', name: 'กรุงเทพฯ', lat: 13.75, lng: 100.51, x: 202.8, y: 359.4, region: 'central' },
  { code: 'NTP', name: 'นนทบุรี', lat: 13.86, lng: 100.51, x: 202.8, y: 353.8, region: 'central' },
  { code: 'PTE', name: 'ปทุมธานี', lat: 14.02, lng: 100.53, x: 204.0, y: 345.6, region: 'central' },
  { code: 'AYU', name: 'อยุธยา', lat: 14.35, lng: 100.57, x: 206.3, y: 328.8, region: 'central' },
  { code: 'CNT', name: 'ชัยนาท', lat: 15.18, lng: 100.12, x: 180.3, y: 286.5, region: 'central' },
  { code: 'LBR', name: 'ลพบุรี', lat: 14.8, lng: 100.65, x: 210.9, y: 305.9, region: 'central' },
  { code: 'SBR', name: 'สระบุรี', lat: 14.53, lng: 100.91, x: 225.9, y: 319.6, region: 'central' },
  { code: 'SPB', name: 'สุพรรณบุรี', lat: 14.47, lng: 100.12, x: 180.3, y: 322.7, region: 'central' },
  { code: 'NPT', name: 'นครปฐม', lat: 13.82, lng: 100.04, x: 175.6, y: 355.8, region: 'central' },
  { code: 'SKN_C', name: 'สมุทรสาคร', lat: 13.54, lng: 100.27, x: 188.9, y: 370.1, region: 'central' },
  { code: 'SKM', name: 'สมุทรสงคราม', lat: 13.41, lng: 100.0, x: 173.3, y: 376.7, region: 'central' },
  { code: 'SPK', name: 'สมุทรปราการ', lat: 13.59, lng: 100.6, x: 208.0, y: 367.6, region: 'central' },
  { code: 'KNB', name: 'กาญจนบุรี', lat: 14.02, lng: 99.53, x: 146.2, y: 345.6, region: 'central' },
  { code: 'RBR', name: 'ราชบุรี', lat: 13.53, lng: 99.82, x: 162.9, y: 370.6, region: 'central' },
  { code: 'PBI', name: 'เพชรบุรี', lat: 13.11, lng: 99.94, x: 169.9, y: 392.0, region: 'central' },
  { code: 'PKN', name: 'ประจวบคีรีขันธ์', lat: 11.81, lng: 99.79, x: 161.2, y: 458.3, region: 'central' },
  { code: 'NYK', name: 'นครนายก', lat: 14.2, lng: 101.21, x: 243.2, y: 336.5, region: 'east' },
  { code: 'PRI', name: 'ปราจีนบุรี', lat: 14.05, lng: 101.37, x: 252.5, y: 344.1, region: 'east' },
  { code: 'SKW', name: 'สระแก้ว', lat: 13.82, lng: 102.07, x: 292.9, y: 355.8, region: 'east' },
  { code: 'CCO', name: 'ฉะเชิงเทรา', lat: 13.69, lng: 101.07, x: 235.2, y: 362.5, region: 'east' },
  { code: 'CBI', name: 'ชลบุรี', lat: 13.36, lng: 100.98, x: 230.0, y: 379.3, region: 'east' },
  { code: 'RYG', name: 'ระยอง', lat: 12.68, lng: 101.28, x: 247.3, y: 414.0, region: 'east' },
  { code: 'CTI', name: 'จันทบุรี', lat: 12.61, lng: 102.1, x: 294.7, y: 417.5, region: 'east' },
  { code: 'TRT', name: 'ตราด', lat: 12.24, lng: 102.51, x: 318.4, y: 436.4, region: 'east' },
  { code: 'CPN', name: 'ชุมพร', lat: 10.49, lng: 99.18, x: 126.0, y: 525.6, region: 'south' },
  { code: 'UNN', name: 'ระนอง', lat: 9.96, lng: 98.63, x: 94.2, y: 552.6, region: 'south' },
  { code: 'SNI', name: 'สุราษฎร์ธานี', lat: 9.13, lng: 99.33, x: 134.6, y: 594.9, region: 'south' },
  { code: 'PNA', name: 'พังงา', lat: 8.45, lng: 98.52, x: 87.8, y: 629.6, region: 'south' },
  { code: 'PKT', name: 'ภูเก็ต', lat: 7.95, lng: 98.33, x: 76.8, y: 655.1, region: 'south' },
  { code: 'KBI', name: 'กระบี่', lat: 8.08, lng: 98.91, x: 110.4, y: 648.5, region: 'south' },
  { code: 'NSI', name: 'นครศรีธรรมราช', lat: 8.43, lng: 99.96, x: 171.0, y: 630.6, region: 'south' },
  { code: 'TRG', name: 'ตรัง', lat: 7.55, lng: 99.61, x: 150.8, y: 675.5, region: 'south' },
  { code: 'PLG', name: 'พัทลุง', lat: 7.61, lng: 100.07, x: 177.4, y: 672.4, region: 'south' },
  { code: 'SKA', name: 'สงขลา', lat: 7.19, lng: 100.59, x: 207.4, y: 693.8, region: 'south' },
  { code: 'STN', name: 'สตูล', lat: 6.62, lng: 100.06, x: 176.8, y: 722.9, region: 'south' },
  { code: 'PTN', name: 'ปัตตานี', lat: 6.86, lng: 101.25, x: 245.6, y: 710.7, region: 'south' },
  { code: 'YLA', name: 'ยะลา', lat: 6.54, lng: 101.28, x: 247.3, y: 727.0, region: 'south' },
  { code: 'NWT', name: 'นราธิวาส', lat: 6.42, lng: 101.82, x: 278.5, y: 733.1, region: 'south' }
];

// Preset active stations data matching FonMaYang backend config
export const DEFAULT_STATIONS: RadarStationCoverage[] = [
  { code: "cri", name: "เชียงราย", center_lat: 19.9609, center_lng: 99.8824, radius_km: 240, is_active: true, region: "north" },
  { code: "tak", name: "ตาก (ดอยมูเซอ)", center_lat: 16.75, center_lng: 98.93, radius_km: 240, is_active: true, region: "north" },
  { code: "cmi240", name: "เชียงใหม่", center_lat: 18.77, center_lng: 98.97, radius_km: 240, is_active: true, region: "north" },
  { code: "phs240", name: "พิษณุโลก", center_lat: 16.7828, center_lng: 100.2786, radius_km: 240, is_active: true, region: "north" },
  { code: "kkn240", name: "ขอนแก่น (240k)", center_lat: 16.4322, center_lng: 102.8236, radius_km: 240, is_active: true, region: "northeast" },
  { code: "kkn120", name: "ขอนแก่น (120k)", center_lat: 16.4322, center_lng: 102.8236, radius_km: 120, is_active: true, region: "northeast" },
  { code: "skn240", name: "สกลนคร", center_lat: 17.1607, center_lng: 104.1486, radius_km: 240, is_active: true, region: "northeast" },
  { code: "ubn240", name: "อุบลราชธานี", center_lat: 15.25, center_lng: 104.88, radius_km: 240, is_active: true, region: "northeast" },
  { code: "chn", name: "ชัยนาท", center_lat: 15.1582, center_lng: 100.1912, radius_km: 240, is_active: true, region: "central" },
  { code: "svp240", name: "สุวรรณภูมิ (กรุงเทพฯ)", center_lat: 13.686, center_lng: 100.7486, radius_km: 240, is_active: true, region: "central" },
  { code: "ntp240", name: "นนทบุรี / ดอนเมือง", center_lat: 13.87, center_lng: 100.53, radius_km: 240, is_active: true, region: "central" },
  { code: "ryg", name: "ระยอง", center_lat: 12.6814, center_lng: 101.2817, radius_km: 240, is_active: true, region: "east" },
  { code: "cmp", name: "ชุมพร", center_lat: 10.4931, center_lng: 99.18, radius_km: 240, is_active: true, region: "south" },
  { code: "srt240", name: "สุราษฎร์ธานี", center_lat: 9.13, center_lng: 99.18, radius_km: 240, is_active: true, region: "south" },
  { code: "pkt240", name: "ภูเก็ต", center_lat: 7.88, center_lng: 98.32, radius_km: 240, is_active: true, region: "south" }
];

interface RadarCoverageMapProps {
  stations?: RadarStationCoverage[];
  onSelectStation?: (code: string) => void;
}

type ProvincePath = { id: string; nameTh: string; nameEn: string; d: string };

export function RadarCoverageMap({ stations = DEFAULT_STATIONS, onSelectStation }: RadarCoverageMapProps) {
  const [selectedStationCode, setSelectedStationCode] = useState<string | null>(null);
  const [hoveredStationCode, setHoveredStationCode] = useState<string | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<string>("all");
  const [showCoverageCircles, setShowCoverageCircles] = useState(true);
  const [showProvinceNames, setShowProvinceNames] = useState(true);
  const [showProvinceBorders, setShowProvinceBorders] = useState(true);
  const [showIntersectionMode, setShowIntersectionMode] = useState(false);
  const [provincePaths, setProvincePaths] = useState<ProvincePath[]>([]);
  const [rawGeoJson, setRawGeoJson] = useState<GeoJSON.FeatureCollection | null>(null);
  const projectionRef = useRef<d3geo.GeoProjection | null>(null);

  // Map Thailand Lat/Lng Box to SVG Coordinates
  const latMin = 5.5;
  const latMax = 20.8;
  const lngMin = 97.0;
  const lngMax = 106.0;

  const svgWidth = 520;
  const svgHeight = 780;

  const latLngToSvg = (lat: number, lng: number) => {
    const x = ((lng - lngMin) / (lngMax - lngMin)) * svgWidth;
    const y = ((latMax - lat) / (latMax - latMin)) * svgHeight;
    return { x, y };
  };

  const kmToSvgRadius = (km: number) => {
    const degLat = km / 111.0;
    return (degLat / (latMax - latMin)) * svgHeight;
  };

  // Load Thailand province GeoJSON and compute SVG paths
  useEffect(() => {
    import("../data/thailand_provinces.json").then((module) => {
      const geojson = module.default as GeoJSON.FeatureCollection;

      // Build a Mercator projection fitted to Thailand bounding box within SVG
      const projection = d3geo.geoMercator().fitExtent(
        [[8, 8], [svgWidth - 8, svgHeight - 8]],
        geojson
      );
      projectionRef.current = projection;

      const pathGenerator = d3geo.geoPath().projection(projection);

      const paths: ProvincePath[] = geojson.features.map((feat) => {
        const props = feat.properties as { pro_code: string; pro_th: string; pro_en: string };
        return {
          id: props.pro_code,
          nameTh: props.pro_th,
          nameEn: props.pro_en,
          d: pathGenerator(feat) ?? "",
        };
      });

      setProvincePaths(paths);
      setRawGeoJson(geojson);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredStations = stations.filter(s => {
    if (selectedRegion === "all") return true;
    return s.region === selectedRegion;
  });

  const filteredProvinces = PROVINCE_MARKERS.filter(p => {
    if (selectedRegion === "all") return true;
    return p.region === selectedRegion;
  });

  // Calculate Coverage status for each province feature using Turf.js
  const provinceCoverageMap = useMemo(() => {
    if (!rawGeoJson) return new Map<string, boolean>();

    const activeStations = stations.filter(s => s.is_active);
    const stationPoints = activeStations.map(s => turf.point([s.center_lng, s.center_lat], { radius_km: s.radius_km }));

    const map = new Map<string, boolean>();

    for (const feat of rawGeoJson.features) {
      const code = (feat.properties as { pro_code: string }).pro_code;
      // Check distance from station centers to province centroid / bbox
      try {
        const bbox = turf.bbox(feat);
        const centerLng = (bbox[0] + bbox[2]) / 2;
        const centerLat = (bbox[1] + bbox[3]) / 2;
        const provCenter = turf.point([centerLng, centerLat]);

        // Province is covered if any active station reaches within radius_km
        const isCovered = stationPoints.some(pt => {
          const dist = turf.distance(pt, provCenter, { units: 'kilometers' });
          return dist <= (pt.properties?.radius_km ?? 240);
        });

        map.set(code, isCovered);
      } catch {
        map.set(code, true);
      }
    }

    return map;
  }, [rawGeoJson, stations]);

  const coveredCount = useMemo(() => {
    let count = 0;
    provinceCoverageMap.forEach(isCovered => { if (isCovered) count++; });
    return count;
  }, [provinceCoverageMap]);

  const totalProvincesCount = rawGeoJson?.features.length || 77;
  const coveragePercent = Math.round((coveredCount / totalProvincesCount) * 100);

  const activeCount = stations.filter(s => s.is_active).length;
  const totalCount = stations.length;

  return (
    <GlassCard className="p-6 overflow-hidden relative border-cyan-500/30">
      {/* Top Header & Overview Badges */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <Radio className="h-6 w-6 text-cyan-400 animate-pulse" />
            <h2 className="text-xl font-bold text-white tracking-tight">
              แผนที่ขอบเขตพื้นที่ครอบคลุมเรดาร์ตรวจอากาศทั่วประเทศ (Thailand Radar Coverage Map)
            </h2>
          </div>
          <p className="text-xs text-slate-400">
            แสดงรัศมีครอบคลุมการเฝ้าระวังพายุฝน (Coverage Radius 240km / 120km) ของสถานีเรดาร์ TMD ทั้งหมดที่เชื่อมต่อในระบบ FonMaYang
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {showIntersectionMode && (
            <GlassBadge variant="emerald" dot className="px-3 py-1.5 text-xs font-semibold animate-pulse">
              🎯 ครอบคลุมแล้ว {coveredCount}/{totalProvincesCount} จังหวัด ({coveragePercent}%)
            </GlassBadge>
          )}
          <GlassBadge variant="cyan" dot className="px-3 py-1.5 text-xs font-semibold">
            เปิดใช้งาน {activeCount} / {totalCount} สถานี
          </GlassBadge>
          <GlassBadge variant="emerald" className="px-3 py-1.5 text-xs font-semibold">
            ⚡ 100% Fully Calibrated เรดาร์ทุกสถานีจูนพิกัดครบแล้ว
          </GlassBadge>
        </div>
      </div>

      {/* Region Filter Bar & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 my-4">
        <div className="flex flex-wrap items-center gap-1.5 bg-slate-900/60 p-1.5 rounded-xl border border-white/10">
          {[
            { id: "all", label: "ทั้งหมด" },
            { id: "north", label: "ภาคเหนือ" },
            { id: "northeast", label: "ภาคตะวันออกเฉียงเหนือ" },
            { id: "central", label: "ภาคกลาง" },
            { id: "east", label: "ภาคตะวันออก" },
            { id: "south", label: "ภาคใต้" },
          ].map(r => (
            <button
              key={r.id}
              onClick={() => setSelectedRegion(r.id)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                selectedRegion === r.id
                  ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                  : "text-slate-300 hover:text-white hover:bg-white/5"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setShowIntersectionMode(!showIntersectionMode)}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-xl border transition-all ${
              showIntersectionMode
                ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-lg shadow-emerald-500/10"
                : "bg-slate-900/80 border-white/10 text-slate-300 hover:text-white"
            }`}
          >
            <Layers className={`h-4 w-4 ${showIntersectionMode ? "text-emerald-400" : "text-slate-400"}`} />
            <span>{showIntersectionMode ? "🎯 ปิดโหมดวิเคราะห์พื้นที่ (Intersection)" : "🎯 เปิดโหมดวิเคราะห์พื้นที่ครอบคลุม/ไม่ครอบคลุม"}</span>
          </button>

          <button
            onClick={() => setShowProvinceBorders(!showProvinceBorders)}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-xl border transition-all ${
              showProvinceBorders
                ? "bg-sky-500/20 border-sky-500/40 text-sky-300"
                : "bg-slate-900/80 border-white/10 text-slate-400 hover:text-white"
            }`}
          >
            <Layers className="h-4 w-4 text-sky-400" />
            <span>{showProvinceBorders ? "ซ่อนเส้นขอบจังหวัด" : "แสดงเส้นขอบจังหวัด"}</span>
          </button>

          <button
            onClick={() => setShowProvinceNames(!showProvinceNames)}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-xl border transition-all ${
              showProvinceNames
                ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-300"
                : "bg-slate-900/80 border-white/10 text-slate-400 hover:text-white"
            }`}
          >
            <MapPin className="h-4 w-4 text-amber-400" />
            <span>{showProvinceNames ? "ซ่อนชื่อจังหวัด" : "แสดงชื่อ 72 จังหวัด"}</span>
          </button>

          <button
            onClick={() => setShowCoverageCircles(!showCoverageCircles)}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-xl bg-slate-900/80 border border-white/10 text-slate-300 hover:text-white transition-all"
          >
            {showCoverageCircles ? <Eye className="h-4 w-4 text-cyan-400" /> : <EyeOff className="h-4 w-4 text-slate-500" />}
            <span>{showCoverageCircles ? "ซ่อนวงกลมรัศมีเรดาร์" : "แสดงวงกลมรัศมีเรดาร์"}</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Visual SVG Map + Station Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* SVG Interactive Map Column */}
        <div className="lg:col-span-7 bg-slate-950/80 rounded-2xl border border-white/10 p-4 relative flex justify-center items-center overflow-hidden min-h-[580px]">
          <div className="absolute top-4 left-4 z-10 flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900/80 border border-white/10 text-slate-400 text-[11px]">
            <Compass className="h-3.5 w-3.5 text-cyan-400" />
            <span>N (ทิศเหนือ)</span>
          </div>

          <svg
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            className="w-full h-auto max-h-[620px] drop-shadow-[0_0_20px_rgba(6,182,212,0.15)]"
          >
            {/* Defs for Grid, Radar Pulse & Dynamic Coverage ClipPath */}
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.04)" strokeWidth="1" />
              </pattern>
              
              <radialGradient id="radarPulse" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="rgba(34, 211, 238, 0.25)" />
                <stop offset="70%" stopColor="rgba(14, 165, 233, 0.12)" />
                <stop offset="100%" stopColor="rgba(2, 132, 199, 0.0)" />
              </radialGradient>

              {/* Combined ClipPath of ALL Active Station Radar Coverage Circles */}
              <clipPath id="allRadarCoverageClip">
                {stations.filter(s => s.is_active).map(st => {
                  const pt = latLngToSvg(st.center_lat, st.center_lng);
                  const r = kmToSvgRadius(st.radius_km);
                  return <circle key={`clip-${st.code}`} cx={pt.x} cy={pt.y} r={r} />;
                })}
              </clipPath>
            </defs>

            <rect width={svgWidth} height={svgHeight} fill="url(#grid)" rx="16" />

            {/* Thailand Province Polygon Boundaries — Base Layer (Default or Uncovered Red) */}
            {showProvinceBorders && provincePaths.map((prov) => (
              <path
                key={`base-${prov.id}`}
                d={prov.d}
                fill={showIntersectionMode ? "rgba(244, 63, 94, 0.35)" : "rgba(15, 23, 42, 0.65)"}
                stroke={showIntersectionMode ? "rgba(251, 113, 133, 0.40)" : "rgba(56, 189, 248, 0.30)"}
                strokeWidth={showIntersectionMode ? "0.8" : "0.8"}
                className="transition-all duration-300"
              />
            ))}

            {/* Thailand Province Polygon Boundaries — Covered Layer (Clipped by Active Radar Circles) */}
            {showProvinceBorders && showIntersectionMode && (
              <g clipPath="url(#allRadarCoverageClip)">
                {provincePaths.map((prov) => (
                  <path
                    key={`covered-${prov.id}`}
                    d={prov.d}
                    fill="rgba(16, 185, 129, 0.45)"
                    stroke="rgba(52, 211, 153, 0.80)"
                    strokeWidth="1.2"
                    className="transition-all duration-300"
                  />
                ))}
              </g>
            )}

            {/* Render 72 Province Name Labels & Markers */}
            {showProvinceNames && filteredProvinces.map(prov => (
              <g key={`prov-${prov.code}`} className="pointer-events-none select-none">
                <circle
                  cx={prov.x}
                  cy={prov.y}
                  r="2"
                  fill="rgba(245, 158, 11, 0.7)"
                  stroke="rgba(255, 255, 255, 0.4)"
                  strokeWidth="0.8"
                />
                <text
                  x={prov.x + 3}
                  y={prov.y + 3}
                  fill="rgba(226, 232, 240, 0.65)"
                  fontSize="8.5"
                  fontWeight="500"
                  className="font-sans drop-shadow-sm"
                >
                  {prov.name}
                </text>
              </g>
            ))}

            {/* Render Coverage Circles */}
            {showCoverageCircles && filteredStations.map(st => {
              const { x, y } = latLngToSvg(st.center_lat, st.center_lng);
              const r = kmToSvgRadius(st.radius_km);
              const isSelected = selectedStationCode === st.code;
              const isHovered = hoveredStationCode === st.code;

              return (
                <g key={`circle-${st.code}`}>
                  <circle
                    cx={x}
                    cy={y}
                    r={r}
                    fill={isSelected || isHovered ? "rgba(34, 211, 238, 0.25)" : "url(#radarPulse)"}
                    stroke={isSelected || isHovered ? "#22d3ee" : "rgba(14, 165, 233, 0.45)"}
                    strokeWidth={isSelected || isHovered ? 2.5 : 1.2}
                    strokeDasharray={st.radius_km === 120 ? "3 3" : undefined}
                    className="transition-all duration-300 pointer-events-none"
                  />
                  <circle
                    cx={x}
                    cy={y}
                    r={r * 0.5}
                    fill="none"
                    stroke={isSelected ? "rgba(34, 211, 238, 0.5)" : "rgba(255, 255, 255, 0.05)"}
                    strokeWidth="0.8"
                    strokeDasharray="2 2"
                  />
                </g>
              );
            })}

            {/* Render Station Center Pins */}
            {filteredStations.map(st => {
              const { x, y } = latLngToSvg(st.center_lat, st.center_lng);
              const isSelected = selectedStationCode === st.code;
              const isHovered = hoveredStationCode === st.code;

              return (
                <g
                  key={`pin-${st.code}`}
                  className="cursor-pointer group"
                  onClick={() => {
                    setSelectedStationCode(st.code);
                    onSelectStation?.(st.code);
                  }}
                  onMouseEnter={() => setHoveredStationCode(st.code)}
                  onMouseLeave={() => setHoveredStationCode(null)}
                >
                  {(isSelected || isHovered) && (
                    <circle
                      cx={x}
                      cy={y}
                      r="16"
                      fill="none"
                      stroke="#22d3ee"
                      strokeWidth="2"
                      className="animate-ping origin-center"
                    />
                  )}

                  <circle
                    cx={x}
                    cy={y}
                    r={isSelected ? "9" : "7"}
                    fill={isSelected || isHovered ? "#22d3ee" : "#0284c7"}
                    stroke="#ffffff"
                    strokeWidth="2"
                    className="transition-all duration-200"
                  />

                  <circle cx={x} cy={y} r="2.5" fill="#ffffff" />

                  <text
                    x={x + 10}
                    y={y + 4}
                    fill={isSelected || isHovered ? "#38bdf8" : "#94a3b8"}
                    fontSize={isSelected ? "12" : "10"}
                    fontWeight={isSelected ? "bold" : "600"}
                    className="pointer-events-none select-none drop-shadow-md"
                  >
                    {st.name.split(" ")[0]} ({st.radius_km}k)
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Floating Map Legend */}
          <div className="absolute bottom-4 right-4 bg-slate-900/90 backdrop-blur-md border border-white/10 p-3 rounded-xl text-[11px] space-y-1.5 shadow-xl">
            <div className="font-semibold text-slate-300 border-b border-white/10 pb-1 mb-1">สัญลักษณ์แผนที่</div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-emerald-400 inline-block"></span>
              <span className="text-slate-300">สถานีเรดาร์จูนพิกัดครบแล้ว (100% Calibrated)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-cyan-400 inline-block"></span>
              <span className="text-slate-300">รัศมีเรดาร์ 240km</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full border border-dashed border-cyan-400 inline-block"></span>
              <span className="text-slate-300">รัศมีเรดาร์ 120km</span>
            </div>
          </div>
        </div>

        {/* Station List Sidebar Column */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <Layers className="h-4 w-4 text-cyan-400" />
              <span>รายชื่อสถานีเรดาร์ในระบบ ({filteredStations.length})</span>
            </h3>
            <span className="text-xs text-slate-500">คลิกสถานีเพื่อโฟกัส</span>
          </div>

          <div className="space-y-2 max-h-[550px] overflow-y-auto pr-1 custom-scrollbar">
            {filteredStations.map(st => {
              const isSelected = selectedStationCode === st.code;

              return (
                <div
                  key={st.code}
                  onClick={() => {
                    setSelectedStationCode(st.code);
                    onSelectStation?.(st.code);
                  }}
                  onMouseEnter={() => setHoveredStationCode(st.code)}
                  onMouseLeave={() => setHoveredStationCode(null)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? "bg-cyan-500/15 border-cyan-500/50 shadow-lg shadow-cyan-500/10"
                      : "bg-slate-900/60 border-white/10 hover:border-white/20 hover:bg-slate-900/90"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-400">
                      <MapPin className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-white">{st.name}</span>
                        <GlassBadge variant="emerald" className="py-0.5 px-1.5 text-[9px]">
                          CALIBRATED
                        </GlassBadge>
                      </div>
                      <div className="text-xs text-slate-400 font-mono mt-0.5">
                        Code: <span className="text-cyan-300 font-bold">{st.code}</span> | Lat: {st.center_lat}, Lng: {st.center_lng}
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <GlassBadge variant={st.radius_km === 240 ? "cyan" : "emerald"} className="text-[10px]">
                      {st.radius_km} km
                    </GlassBadge>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </GlassCard>
  );
}
