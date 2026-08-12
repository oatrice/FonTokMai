"use client";

import React, { useState } from "react";
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

// Preset active stations data matching FonMaYang backend config
export const DEFAULT_STATIONS: RadarStationCoverage[] = [
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

export function RadarCoverageMap({ stations = DEFAULT_STATIONS, onSelectStation }: RadarCoverageMapProps) {
  const [selectedStationCode, setSelectedStationCode] = useState<string | null>(null);
  const [hoveredStationCode, setHoveredStationCode] = useState<string | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<string>("all");
  const [showCoverageCircles, setShowCoverageCircles] = useState(true);

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

  const filteredStations = stations.filter(s => {
    if (selectedRegion === "all") return true;
    return s.region === selectedRegion;
  });

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
          <GlassBadge variant="cyan" dot className="px-3 py-1.5 text-xs font-semibold">
            เปิดใช้งาน {activeCount} / {totalCount} สถานี
          </GlassBadge>
          <GlassBadge variant="emerald" className="px-3 py-1.5 text-xs font-semibold">
            ครอบคลุม ~92.4% พื้นที่ประเทศไทย
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

        <button
          onClick={() => setShowCoverageCircles(!showCoverageCircles)}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-xl bg-slate-900/80 border border-white/10 text-slate-300 hover:text-white transition-all"
        >
          {showCoverageCircles ? <Eye className="h-4 w-4 text-cyan-400" /> : <EyeOff className="h-4 w-4 text-slate-500" />}
          <span>{showCoverageCircles ? "ซ่อนวงกลมรัศมีครอบคลุม" : "แสดงวงกลมรัศมีครอบคลุม"}</span>
        </button>
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
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.04)" strokeWidth="1" />
              </pattern>
              
              <radialGradient id="radarPulse" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="rgba(34, 211, 238, 0.25)" />
                <stop offset="70%" stopColor="rgba(14, 165, 233, 0.12)" />
                <stop offset="100%" stopColor="rgba(2, 132, 199, 0.0)" />
              </radialGradient>
            </defs>

            <rect width={svgWidth} height={svgHeight} fill="url(#grid)" rx="16" />

            {/* Thailand Vector Map Background Shape */}
            <path
              d="M 166.4,17.3 L 178.0,25.5 L 204.5,33.1 L 199.3,58.6 L 218.4,71.4 L 251.3,66.3 L 241.5,86.7 L 222.4,112.2 L 254.2,132.5 L 332.2,150.4 L 358.2,127.5 L 404.4,130.0 L 447.8,173.3 L 444.9,203.9 L 482.4,244.7 L 491.1,280.4 L 485.3,326.3 L 392.9,331.4 L 323.6,336.5 L 317.8,362.0 L 306.2,387.5 L 335.1,438.4 L 317.8,469.0 L 288.9,428.2 L 254.2,418.0 L 225.3,412.9 L 208.0,372.2 L 173.3,372.2 L 170.4,423.1 L 138.7,499.6 L 132.9,504.7 L 92.4,550.6 L 86.7,560.8 L 75.1,591.4 L 75.1,652.5 L 121.3,678.0 L 179.1,729.0 L 242.7,744.3 L 236.9,774.9 L 294.7,744.3 L 271.6,713.7 L 208.0,693.3 L 173.3,647.5 L 167.6,591.4 L 121.3,550.6 L 150.2,474.1 L 167.6,438.4 L 167.6,387.5 L 138.7,356.9 L 80.9,316.1 L 80.9,285.5 L 98.2,244.7 L 86.7,219.2 L 57.8,173.3 L 23.1,137.6 L 52.0,112.2 L 52.0,71.4 L 63.6,56.1 L 144.4,40.8 Z"
              fill="rgba(30, 41, 59, 0.75)"
              stroke="rgba(56, 189, 248, 0.45)"
              strokeWidth="2.5"
              className="drop-shadow-[0_0_15px_rgba(56,189,248,0.25)] transition-all"
            />


            {/* Render Coverage Circles */}
            {showCoverageCircles && filteredStations.map(st => {
              const { x, y } = latLngToSvg(st.center_lat, st.center_lng);
              const r = kmToSvgRadius(st.radius_km);
              const isSelected = selectedStationCode === st.code;
              const isHovered = hoveredStationCode === st.code;
              const isSpecial = st.code === "tak";

              return (
                <g key={`circle-${st.code}`}>
                  <circle
                    cx={x}
                    cy={y}
                    r={r}
                    fill={isSelected || isHovered ? "rgba(34, 211, 238, 0.2)" : isSpecial ? "rgba(245, 158, 11, 0.12)" : "url(#radarPulse)"}
                    stroke={isSelected || isHovered ? "#22d3ee" : isSpecial ? "#f59e0b" : "rgba(14, 165, 233, 0.4)"}
                    strokeWidth={isSelected || isHovered ? 2.5 : isSpecial ? 2 : 1.2}
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
              const isSpecial = st.code === "tak";

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
                    fill={isSpecial ? "#f59e0b" : isSelected ? "#22d3ee" : "#0284c7"}
                    stroke="#ffffff"
                    strokeWidth="2"
                    className="transition-all duration-200"
                  />

                  <circle cx={x} cy={y} r="2.5" fill="#ffffff" />

                  <text
                    x={x + 10}
                    y={y + 4}
                    fill={isSelected || isHovered ? "#38bdf8" : isSpecial ? "#fbbf24" : "#94a3b8"}
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
              <span className="w-3 h-3 rounded-full bg-amber-500 inline-block"></span>
              <span className="text-slate-300">สถานีเรดาร์ตาก (Tak tuned)</span>
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
              const isSpecial = st.code === "tak";

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
                      : isSpecial
                      ? "bg-amber-500/10 border-amber-500/30 hover:border-amber-500/50"
                      : "bg-slate-900/60 border-white/10 hover:border-white/20 hover:bg-slate-900/90"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${isSpecial ? "bg-amber-500/20 text-amber-400" : "bg-cyan-500/20 text-cyan-400"}`}>
                      <MapPin className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-white">{st.name}</span>
                        {isSpecial && (
                          <GlassBadge variant="amber" className="py-0.5 px-1.5 text-[9px]">
                            CALIBRATED TAK
                          </GlassBadge>
                        )}
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
