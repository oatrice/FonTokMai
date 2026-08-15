import React, { useState, useEffect, useRef } from "react";
import * as d3geo from "d3-geo";
import { Radio, Navigation, Clock, Activity, CloudRain, Zap, Layers, MapPin } from "lucide-react";

export interface TrajectoryPoint {
  time_offset_min: number; // e.g. -15, -10, -5
  cx?: number;
  cy?: number;
  lat?: number;
  lng?: number;
  dbz: number;
}

export interface CloudCluster {
  id: string;
  label: string;
  cx?: number;
  cy?: number;
  lat?: number;
  lng?: number;
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

interface ProvincePath {
  id: string;
  nameTh: string;
  nameEn: string;
  d: string;
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
  const [showCoverageCircles, setShowCoverageCircles] = useState<boolean>(false);
  const [showStationCenters, setShowStationCenters] = useState<boolean>(true);
  const [showCloudClusters, setShowCloudClusters] = useState<boolean>(true);
  const [showDbzLabels, setShowDbzLabels] = useState<boolean>(true);
  const [provincePaths, setProvincePaths] = useState<ProvincePath[]>([]);
  const projectionRef = useRef<d3geo.GeoProjection | null>(null);

  const svgWidth = 520;
  const svgHeight = 780;

  // Load Thailand province GeoJSON and match d3geo Mercator projection with Coverage Map
  useEffect(() => {
    import("@/data/thailand_provinces.json").then((module) => {
      const geojson = module.default as GeoJSON.FeatureCollection;
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
    });
  }, []);

  const projectLatLng = (lat: number, lng: number) => {
    if (projectionRef.current) {
      const coords = projectionRef.current([lng, lat]);
      if (coords) return { x: coords[0], y: coords[1] };
    }
    const minLat = 5.5, maxLat = 20.5;
    const minLng = 97.0, maxLng = 106.0;
    const x = ((lng - minLng) / (maxLng - minLng)) * svgWidth;
    const y = ((maxLat - lat) / (maxLat - minLat)) * svgHeight;
    return { x: Math.max(30, Math.min(svgWidth - 30, x)), y: Math.max(30, Math.min(svgHeight - 30, y)) };
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
            <h3 className="text-sm font-bold text-white tracking-wide">Interactive Radar Coverage & Cloud Trajectory (Nationwide Zoom-Out)</h3>
            <p className="text-xs text-zinc-400">Hover over cloud clusters to preview historical movement vectors</p>
          </div>
        </div>

        {/* Controls & Legend */}
        <div className="flex flex-wrap items-center gap-3 text-xs">
          {/* Debug UI Toolbar */}
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-zinc-900 border border-white/10">
            <span className="px-2 text-[11px] font-semibold text-cyan-400">UI Debug:</span>
            
            {/* Toggle Station Centers */}
            <button
              onClick={() => setShowStationCenters(!showStationCenters)}
              className={`px-2.5 py-1 rounded-lg border text-[11px] font-medium transition-all ${
                showStationCenters
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-semibold"
                  : "bg-white/5 text-zinc-500 border-white/5 hover:text-zinc-300"
              }`}
            >
              {showStationCenters ? "🎯 ศูนย์กลางเรดาร์ [ON]" : "🎯 ศูนย์กลางเรดาร์ [OFF]"}
            </button>

            {/* Toggle Cloud Clusters */}
            <button
              onClick={() => setShowCloudClusters(!showCloudClusters)}
              className={`px-2.5 py-1 rounded-lg border text-[11px] font-medium transition-all ${
                showCloudClusters
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-semibold"
                  : "bg-white/5 text-zinc-500 border-white/5 hover:text-zinc-300"
              }`}
            >
              {showCloudClusters ? "🌧️ ก้อนเมฆฝน [ON]" : "🌧️ ก้อนเมฆฝน [OFF]"}
            </button>

            {/* Toggle dBZ Labels */}
            <button
              onClick={() => setShowDbzLabels(!showDbzLabels)}
              className={`px-2.5 py-1 rounded-lg border text-[11px] font-medium transition-all ${
                showDbzLabels
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-semibold"
                  : "bg-white/5 text-zinc-500 border-white/5 hover:text-zinc-300"
              }`}
            >
              {showDbzLabels ? "🏷️ ค่า dBZ [ON]" : "🏷️ ค่า dBZ [OFF]"}
            </button>

            {/* Toggle Coverage Circles */}
            <button
              onClick={() => setShowCoverageCircles(!showCoverageCircles)}
              className={`px-2.5 py-1 rounded-lg border text-[11px] font-medium transition-all ${
                showCoverageCircles
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-semibold"
                  : "bg-white/5 text-zinc-500 border-white/5 hover:text-zinc-300"
              }`}
            >
              {showCoverageCircles ? "⭕ วงรัศมี [ON]" : "⭕ วงรัศมี [OFF]"}
            </button>
          </div>

          <div className="flex items-center gap-1.5 text-zinc-300">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
            <span>Online</span>
          </div>
          <div className="flex items-center gap-1.5 text-zinc-300">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span>Delayed</span>
          </div>
          <div className="flex items-center gap-1.5 text-zinc-300">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span>Offline</span>
          </div>
        </div>
      </div>

      {/* SVG Canvas Map */}
      <div className="relative w-full aspect-[4/3] max-h-[600px] bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px]">
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

          {/* Thailand Province Polygon Boundaries — SVG Base Map (Semi-Transparent Green) */}
          {provincePaths.map((prov) => (
            <path
              key={`prov-base-${prov.id}`}
              d={prov.d}
              fill="#059669"
              fillOpacity={0.15}
              stroke="#10b981"
              strokeWidth="0.8"
              strokeOpacity={0.5}
              style={{ fill: "#059669", fillOpacity: 0.15, stroke: "#10b981", strokeOpacity: 0.5 }}
              className="transition-all duration-300 pointer-events-none"
            />
          ))}

          {/* Render Station Coverage Radii & Centers */}
          {stations.map((st) => {
            const pos = projectLatLng(st.center_lat, st.center_lng);
            const statusStyle = getStatusColor(st.status);
            const isSelected = selectedStationCode === st.code;
            const rPx = st.radius_km * 0.45; // Scaled pixel radius for Nationwide zoom-out

            // Smart label offset: Prevent overlap between Tak and Chainat or close stations
            let labelOffsetX = 0;
            let labelOffsetY = 16;
            if (st.code.toLowerCase().includes("tak")) {
              labelOffsetX = -18;
              labelOffsetY = -10;
            } else if (st.code.toLowerCase().includes("chn")) {
              labelOffsetX = 18;
              labelOffsetY = 16;
            }

            return (
              <g key={st.code} className="cursor-pointer" onClick={() => onSelectStation?.(st)} onMouseEnter={() => setHoveredStation(st)} onMouseLeave={() => setHoveredStation(null)}>
                {/* Coverage Outer Ring (Optional Toggle to prevent visual clutter) */}
                {showCoverageCircles && (
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={rPx}
                    fill={statusStyle.stroke}
                    fillOpacity={isSelected ? 0.12 : 0.03}
                    stroke={statusStyle.stroke}
                    strokeWidth={isSelected ? 1.5 : 0.8}
                    strokeDasharray="4 4"
                    className="transition-all duration-300 pointer-events-none"
                  />
                )}
                
                {/* Station Center Marker (Fixed size to eliminate jitter/flickering) */}
                {showStationCenters && (
                  <>
                    <circle
                      data-testid={`station-marker-${st.code}`}
                      cx={pos.x}
                      cy={pos.y}
                      r={isSelected ? 8 : 6}
                      fill={statusStyle.fill}
                      stroke="#ffffff"
                      strokeWidth={1.8}
                      className="transition-colors duration-150"
                    />

                    {/* Station Label */}
                    <text
                      x={pos.x + labelOffsetX}
                      y={pos.y + labelOffsetY}
                      textAnchor="middle"
                      fill="#e2e8f0"
                      fontSize="10"
                      fontWeight="600"
                      className="pointer-events-none drop-shadow-md select-none"
                    >
                      {st.name}
                    </text>
                  </>
                )}
              </g>
            );
          })}

          {/* Render Active Cloud Clusters & Trajectories (Issue #188) */}
          {clusters.map((cluster) => {
            const isHovered = hoveredCluster?.id === cluster.id;
            const dbzColor = getDbzColor(cluster.intensity_dbz);

            const clusterPos = cluster.lat !== undefined && cluster.lng !== undefined
              ? projectLatLng(cluster.lat, cluster.lng)
              : { x: cluster.cx ?? 0, y: cluster.cy ?? 0 };

            const trajectoryPoints = (cluster.history_trajectory || []).map((pt) => {
              const ptPos = pt.lat !== undefined && pt.lng !== undefined
                ? projectLatLng(pt.lat, pt.lng)
                : { x: pt.cx ?? 0, y: pt.cy ?? 0 };
              return { ...pt, x: ptPos.x, y: ptPos.y };
            });

            return (
              <g
                key={cluster.id}
                data-testid={`cloud-cluster-${cluster.id}`}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredCluster(cluster)}
                onMouseLeave={() => setHoveredCluster(null)}
              >
                {/* Historical Trajectory Vectors (Visible when hovered) */}
                {isHovered && trajectoryPoints.length > 0 && (
                  <g data-testid={`trajectory-path-${cluster.id}`}>
                    {/* Path line connecting historical coordinates to current position */}
                    <path
                      d={`M ${trajectoryPoints.map((p) => `${p.x},${p.y}`).join(" L ")} L ${clusterPos.x},${clusterPos.y}`}
                      fill="none"
                      stroke="#06b6d4"
                      strokeWidth="3"
                      strokeDasharray="6 4"
                      strokeLinecap="round"
                      className="filter drop-shadow-[0_0_10px_rgba(6,182,212,0.9)]"
                    />

                    {/* Historical frame waypoints with pill badge background */}
                    {trajectoryPoints.map((pt, idx) => (
                      <g key={idx}>
                        <circle
                          cx={pt.x}
                          cy={pt.y}
                          r={5}
                          fill="#22d3ee"
                          stroke="#020617"
                          strokeWidth="2.5"
                        />
                        {/* Waypoint Text Badge with enhanced offset spacing (y - 28) */}
                        <rect
                          x={pt.x - 18}
                          y={pt.y - 28}
                          width={36}
                          height={15}
                          rx={4}
                          fill="#090d16"
                          stroke="#38bdf8"
                          strokeWidth={1.2}
                        />
                        <text
                          x={pt.x}
                          y={pt.y - 17}
                          textAnchor="middle"
                          fill="#38bdf8"
                          fontSize="9.5"
                          fontWeight="bold"
                          className="select-none pointer-events-none"
                        >
                          {pt.time_offset_min}m
                        </text>
                      </g>
                    ))}

                    {/* Velocity & Heading Vector Arrow (Extended distance and high visibility) */}
                    {(() => {
                      const rad = (cluster.heading_deg - 90) * (Math.PI / 180);
                      const startX = clusterPos.x + Math.cos(rad) * (cluster.radius * 0.95);
                      const startY = clusterPos.y + Math.sin(rad) * (cluster.radius * 0.95);
                      const targetX = clusterPos.x + Math.cos(rad) * 55;
                      const targetY = clusterPos.y + Math.sin(rad) * 55;
                      return (
                        <line
                          x1={startX}
                          y1={startY}
                          x2={targetX}
                          y2={targetY}
                          stroke="#38bdf8"
                          strokeWidth="3"
                          markerEnd="url(#arrow)"
                        />
                      );
                    })()}
                  </g>
                )}

                {/* Cloud Cluster Body (Semi-transparent radar reflection) */}
                {showCloudClusters && (
                  <circle
                    cx={clusterPos.x}
                    cy={clusterPos.y}
                    r={cluster.radius * 0.85}
                    fill={dbzColor}
                    fillOpacity={isHovered ? 0.95 : 0.75}
                    stroke="#ffffff"
                    strokeWidth={isHovered ? 2.5 : 1.5}
                    className="transition-colors duration-150"
                  />
                )}

                {/* Direct Crisp dBZ Number (Dark bold text with crisp white outline) */}
                {showDbzLabels && (
                  <text
                    x={clusterPos.x}
                    y={clusterPos.y + 3.5}
                    textAnchor="middle"
                    fill="#090d16"
                    fontSize="11.5"
                    fontWeight="900"
                    style={{
                      fill: "#090d16",
                      paintOrder: "stroke fill",
                      stroke: "#ffffff",
                      strokeWidth: "2.2px",
                      strokeLinejoin: "round",
                    }}
                    className="pointer-events-none select-none drop-shadow-sm"
                  >
                    {cluster.intensity_dbz.toFixed(0)}
                  </text>
                )}
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
