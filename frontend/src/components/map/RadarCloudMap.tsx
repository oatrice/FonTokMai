"use client";

import React, { useState } from "react";
import { Radio, Navigation, Clock, Activity, CloudRain, Zap } from "lucide-react";

export interface TrajectoryPoint {
  time_offset_min: number; // e.g. -15, -10, -5
  cx: number;
  cy: number;
  dbz: number;
}

export interface CloudCluster {
  id: string;
  label: string;
  cx: number;
  cy: number;
  radius: number;
  intensity_dbz: number;
  velocity_kmh: number;
  heading_deg: number;
  eta_min?: number;
  history_trajectory?: TrajectoryPoint[];
}

export interface RadarStation {
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

interface RadarCloudMapProps {
  stations?: RadarStation[];
  clusters?: CloudCluster[];
  selectedStationCode?: string;
  onSelectStation?: (station: RadarStation) => void;
}

export function RadarCloudMap({
  stations = [],
  clusters = [],
  selectedStationCode,
  onSelectStation,
}: RadarCloudMapProps) {
  const [hoveredCluster, setHoveredCluster] = useState<CloudCluster | null>(null);
  const [hoveredStation, setHoveredStation] = useState<RadarStation | null>(null);

  // Geographic projection bounds (North-East Thailand focus)
  const minLat = 14.0, maxLat = 19.5;
  const minLng = 100.0, maxLng = 106.5;
  const svgWidth = 800, svgHeight = 600;

  const projectLatLng = (lat: number, lng: number) => {
    const x = ((lng - minLng) / (maxLng - minLng)) * svgWidth;
    const y = ((maxLat - lat) / (maxLat - minLat)) * svgHeight;
    return { x: Math.max(40, Math.min(svgWidth - 40, x)), y: Math.max(40, Math.min(svgHeight - 40, y)) };
  };

  const getDbzColor = (dbz: number) => {
    if (dbz >= 50) return "#ef4444"; // Red (Severe)
    if (dbz >= 40) return "#f97316"; // Orange (Heavy)
    if (dbz >= 30) return "#eab308"; // Yellow (Moderate)
    if (dbz >= 20) return "#22c55e"; // Green (Light)
    return "#06b6d4"; // Cyan
  };

  const getStatusColor = (status: string) => {
    if (status === "online") return { stroke: "#10b981", fill: "#059669", bg: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" };
    if (status === "delayed") return { stroke: "#f59e0b", fill: "#d97706", bg: "bg-amber-500/20 text-amber-400 border-amber-500/30" };
    return { stroke: "#ef4444", fill: "#dc2626", bg: "bg-red-500/20 text-red-400 border-red-500/30" };
  };

  return (
    <div className="relative w-full rounded-2xl overflow-hidden bg-zinc-950/80 border border-white/10 shadow-2xl backdrop-blur-xl">
      {/* Map Header Toolbar */}
      <div className="p-4 border-b border-white/10 flex flex-wrap items-center justify-between gap-3 bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">Interactive Radar Coverage & Cloud Trajectory</h3>
            <p className="text-xs text-zinc-400">Hover over cloud clusters to preview historical movement vectors</p>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5 text-zinc-300">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
            <span>Online (&lt;30m)</span>
          </div>
          <div className="flex items-center gap-1.5 text-zinc-300">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span>Delayed (30-60m)</span>
          </div>
          <div className="flex items-center gap-1.5 text-zinc-300">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span>Offline</span>
          </div>
        </div>
      </div>

      {/* SVG Canvas Map */}
      <div className="relative w-full aspect-[4/3] max-h-[560px] bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px]">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-full select-none"
          role="img"
          aria-label="Radar Coverage Map"
        >
          <defs>
            {/* Grid Radial Overlay */}
            <radialGradient id="radarScanGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
            </radialGradient>
            {/* Arrow Marker for Heading */}
            <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8" />
            </marker>
          </defs>

          {/* Background Map Frame */}
          <rect width={svgWidth} height={svgHeight} fill="transparent" />

          {/* Geographic Guide Rings & Meridians */}
          <line x1="0" y1="300" x2="800" y2="300" stroke="#334155" strokeDasharray="4 4" strokeWidth="0.8" opacity="0.4" />
          <line x1="400" y1="0" x2="400" y2="600" stroke="#334155" strokeDasharray="4 4" strokeWidth="0.8" opacity="0.4" />

          {/* Render Station Coverage Radii & Centers */}
          {stations.map((st) => {
            const pos = projectLatLng(st.center_lat, st.center_lng);
            const statusStyle = getStatusColor(st.status);
            const isSelected = selectedStationCode === st.code;
            const rPx = st.radius_km * 1.15; // Scaled pixel radius

            return (
              <g key={st.code} className="cursor-pointer" onClick={() => onSelectStation?.(st)} onMouseEnter={() => setHoveredStation(st)} onMouseLeave={() => setHoveredStation(null)}>
                {/* Coverage Outer Ring */}
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={rPx}
                  fill={statusStyle.stroke}
                  fillOpacity={isSelected ? 0.12 : 0.04}
                  stroke={statusStyle.stroke}
                  strokeWidth={isSelected ? 2 : 1}
                  strokeDasharray="6 4"
                  className="transition-all duration-300"
                />
                
                {/* Station Center Marker */}
                <circle
                  data-testid={`station-marker-${st.code}`}
                  cx={pos.x}
                  cy={pos.y}
                  r={isSelected ? 9 : 7}
                  fill={statusStyle.fill}
                  stroke="#ffffff"
                  strokeWidth={2}
                  className="hover:scale-125 transition-transform"
                />

                {/* Station Label */}
                <text
                  x={pos.x}
                  y={pos.y + 22}
                  textAnchor="middle"
                  fill="#e2e8f0"
                  fontSize="11"
                  fontWeight="600"
                  className="pointer-events-none drop-shadow-md"
                >
                  {st.name}
                </text>
              </g>
            );
          })}

          {/* Render Active Cloud Clusters & Trajectories (Issue #188) */}
          {clusters.map((cluster) => {
            const isHovered = hoveredCluster?.id === cluster.id;
            const dbzColor = getDbzColor(cluster.intensity_dbz);

            return (
              <g
                key={cluster.id}
                data-testid={`cloud-cluster-${cluster.id}`}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredCluster(cluster)}
                onMouseLeave={() => setHoveredCluster(null)}
              >
                {/* Historical Trajectory Vectors (Visible when hovered) */}
                {isHovered && cluster.history_trajectory && cluster.history_trajectory.length > 0 && (
                  <g data-testid={`trajectory-path-${cluster.id}`}>
                    {/* Path line connecting historical coordinates to current position */}
                    <path
                      d={`M ${cluster.history_trajectory.map((p) => `${p.cx},${p.cy}`).join(" L ")} L ${cluster.cx},${cluster.cy}`}
                      fill="none"
                      stroke="#38bdf8"
                      strokeWidth="3"
                      strokeDasharray="6 4"
                      strokeLinecap="round"
                      className="filter drop-shadow-[0_0_8px_rgba(56,189,248,0.8)]"
                    />

                    {/* Historical frame waypoints */}
                    {cluster.history_trajectory.map((pt, idx) => (
                      <g key={idx}>
                        <circle
                          cx={pt.cx}
                          cy={pt.cy}
                          r={5}
                          fill="#38bdf8"
                          stroke="#0f172a"
                          strokeWidth="2"
                        />
                        <text
                          x={pt.cx}
                          y={pt.cy - 10}
                          textAnchor="middle"
                          fill="#7dd3fc"
                          fontSize="10"
                          fontWeight="bold"
                          className="drop-shadow"
                        >
                          {pt.time_offset_min}m
                        </text>
                      </g>
                    ))}

                    {/* Velocity & Heading Vector Arrow (Predictive forward vector) */}
                    {(() => {
                      const rad = (cluster.heading_deg - 90) * (Math.PI / 180);
                      const targetX = cluster.cx + Math.cos(rad) * 45;
                      const targetY = cluster.cy + Math.sin(rad) * 45;
                      return (
                        <line
                          x1={cluster.cx}
                          y1={cluster.cy}
                          x2={targetX}
                          y2={targetY}
                          stroke="#38bdf8"
                          strokeWidth="2.5"
                          markerEnd="url(#arrow)"
                        />
                      );
                    })()}
                  </g>
                )}

                {/* Cloud Cluster Body */}
                <circle
                  cx={cluster.cx}
                  cy={cluster.cy}
                  r={isHovered ? cluster.radius * 1.15 : cluster.radius}
                  fill={dbzColor}
                  fillOpacity={isHovered ? 0.85 : 0.65}
                  stroke={isHovered ? "#ffffff" : dbzColor}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  className="transition-all duration-200"
                />

                {/* Cluster Label / ID */}
                <text
                  x={cluster.cx}
                  y={cluster.cy + 4}
                  textAnchor="middle"
                  fill="#ffffff"
                  fontSize="10"
                  fontWeight="bold"
                  className="pointer-events-none drop-shadow"
                >
                  {cluster.intensity_dbz} dBZ
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover Trajectory Floating Card (Issue #188) */}
        {hoveredCluster && (
          <div
            data-testid="trajectory-preview-card"
            className="absolute bottom-4 right-4 z-20 max-w-sm w-full p-4 rounded-xl bg-zinc-900/95 border border-cyan-500/40 shadow-2xl backdrop-blur-md text-white animate-in fade-in zoom-in-95 duration-150"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <CloudRain className="w-4 h-4 text-cyan-400" />
                <span className="font-bold text-sm tracking-tight">{hoveredCluster.label}</span>
              </div>
              <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 font-mono">
                {hoveredCluster.intensity_dbz} dBZ
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs text-zinc-300 mb-3">
              <div className="flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-zinc-400" />
                <span>Speed: <strong className="text-white font-mono">{hoveredCluster.velocity_kmh.toFixed(1)} km/h</strong></span>
              </div>
              <div className="flex items-center gap-1.5">
                <Navigation className="w-3.5 h-3.5 text-zinc-400" />
                <span>Heading: <strong className="text-white font-mono">{hoveredCluster.heading_deg}°</strong></span>
              </div>
            </div>

            {hoveredCluster.history_trajectory && (
              <div className="pt-2 border-t border-white/10 text-xs">
                <div className="flex items-center gap-1 text-cyan-400 font-semibold mb-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>Historical Movement:</span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-zinc-400 overflow-x-auto">
                  {hoveredCluster.history_trajectory.map((pt, i) => (
                    <span key={i} className="px-1.5 py-0.5 rounded bg-white/5 border border-white/5 whitespace-nowrap">
                      {pt.time_offset_min}m ({pt.dbz} dBZ)
                    </span>
                  ))}
                  <span className="px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold whitespace-nowrap">
                    Now
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Station Hover Tooltip */}
        {hoveredStation && !hoveredCluster && (
          <div className="absolute top-4 left-4 z-20 p-3 rounded-xl bg-zinc-900/90 border border-white/10 shadow-xl backdrop-blur-md text-xs text-zinc-200">
            <p className="font-bold text-white mb-1">{hoveredStation.name} ({hoveredStation.code})</p>
            <p className="text-zinc-400">Lat: {hoveredStation.center_lat.toFixed(4)}, Lng: {hoveredStation.center_lng.toFixed(4)}</p>
            <p className="text-zinc-400">Radius: {hoveredStation.radius_km} km | Latency: {hoveredStation.latency_minutes}m</p>
          </div>
        )}
      </div>
    </div>
  );
}
