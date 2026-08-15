import React, { useState, useEffect, useRef, useMemo } from "react";
import * as d3geo from "d3-geo";
import { Radio, Navigation, Clock, Activity, CloudRain, Zap, Layers, MapPin, X } from "lucide-react";

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
  sub_clusters?: CloudCluster[]; // Hierarchical nested cells revealed upon zoom-in / de-cluster
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
  const [pinnedCluster, setPinnedCluster] = useState<CloudCluster | null>(null);
  const [hoveredStation, setHoveredStation] = useState<RadarStation | null>(null);
  const [showCoverageCircles, setShowCoverageCircles] = useState<boolean>(false);
  const [showStationCenters, setShowStationCenters] = useState<boolean>(true);
  const [showCloudClusters, setShowCloudClusters] = useState<boolean>(true);
  const [showDbzLabels, setShowDbzLabels] = useState<boolean>(true);
  const [enableClustering, setEnableClustering] = useState<boolean>(true);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [provincePaths, setProvincePaths] = useState<ProvincePath[]>([]);
  const projectionRef = useRef<d3geo.GeoProjection | null>(null);

  const svgWidth = 520;
  const svgHeight = 780;

  // Manual Zoom Controls (Google Maps style up to 12x Ultra Deep District Zoom)
  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(12, Number((prev < 3 ? prev + 0.5 : prev + 1.0).toFixed(1))));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => {
      const step = prev <= 3 ? 0.5 : 1.0;
      const next = Math.max(1, Number((prev - step).toFixed(1)));
      if (next === 1) setPanOffset({ x: 0, y: 0 });
      return next;
    });
  };

  const handleResetZoom = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  // Mouse Drag Panning Handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;
    setDragStart({ x: e.clientX, y: e.clientY });
    setPanOffset((prev) => ({
      x: prev.x + dx,
      y: prev.y + dy,
    }));
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Mouse Wheel Zoom Support (Seamless zoom in/out with scroll wheel)
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      handleZoomIn();
    } else if (e.deltaY > 0) {
      handleZoomOut();
    }
  };

  // Focus zoom into a specific cloud cluster zone smoothly (District scale 3.5x)
  const handleFocusCluster = (cluster: CloudCluster) => {
    const pos = cluster.lat !== undefined && cluster.lng !== undefined
      ? projectLatLng(cluster.lat, cluster.lng)
      : { x: cluster.cx ?? svgWidth / 2, y: cluster.cy ?? svgHeight / 2 };
    
    setZoomLevel(3.5);
    setPanOffset({
      x: (svgWidth / 2) - pos.x,
      y: (svgHeight / 2) - pos.y,
    });
  };

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

  const projectLatLng = (lat?: number, lng?: number): { x: number; y: number } => {
    if (lat === undefined || lng === undefined) return { x: svgWidth / 2, y: svgHeight / 2 };
    if (projectionRef.current) {
      const coords = projectionRef.current([lng, lat]);
      if (coords) return { x: coords[0], y: coords[1] };
    }
    const minLat = 5.5, maxLat = 20.5;
    const minLng = 97.0, maxLng = 106.0;
    const x = ((lng - minLng) / (maxLng - minLng)) * svgWidth;
    const y = ((maxLat - lat) / (maxLat - minLat)) * svgHeight;
    return { x, y };
  };

  // Compute viewBox based on manual Google Maps-style zoomLevel & panOffset
  const currentViewBox = useMemo(() => {
    const currentW = svgWidth / zoomLevel;
    const currentH = svgHeight / zoomLevel;
    const centerX = (svgWidth / 2) - (panOffset.x / zoomLevel);
    const centerY = (svgHeight / 2) - (panOffset.y / zoomLevel);

    const minX = Math.max(-50, Math.min(svgWidth - currentW + 50, centerX - currentW / 2));
    const minY = Math.max(-50, Math.min(svgHeight - currentH + 50, centerY - currentH / 2));

    return `${minX} ${minY} ${currentW} ${currentH}`;
  }, [zoomLevel, panOffset]);

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

            {/* Toggle Dynamic Clustering / Spiderfy */}
            <button
              onClick={() => setEnableClustering(!enableClustering)}
              className={`px-2.5 py-1 rounded-lg border text-[11px] font-medium transition-all ${
                enableClustering
                  ? "bg-purple-500/20 text-purple-300 border-purple-500/40 font-semibold"
                  : "bg-white/5 text-zinc-500 border-white/5 hover:text-zinc-300"
              }`}
              title="สลับโหมดรวมกลุ่มฝน (Zoom < 2.0x = รวมกลุ่ม, Zoom ≥ 2.0x = แตกตัว)"
            >
              {enableClustering
                ? zoomLevel >= 2.0
                  ? "🔮 De-clustered [แตกตัว]"
                  : "🔮 Clustered [รวมกลุ่ม]"
                : "🔮 Clustering [OFF]"}
            </button>

            {/* Toggle Coverage Rings */}
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
      <div className="relative w-full aspect-[4/3] max-h-[600px] bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] overflow-hidden">
        {/* Google Maps Style Floating Zoom Controls */}
        <div className="absolute top-4 left-4 z-20 flex flex-col gap-1 bg-zinc-900/90 p-1 rounded-xl border border-white/10 shadow-2xl backdrop-blur-md">
          <button
            onClick={handleZoomIn}
            title="Zoom In (+)"
            aria-label="Zoom In"
            className="w-8 h-8 flex items-center justify-center rounded-lg text-zinc-300 hover:text-white hover:bg-white/10 transition-colors text-base font-bold"
          >
            +
          </button>
          <div className="w-full h-[1px] bg-white/10" />
          <button
            onClick={handleZoomOut}
            title="Zoom Out (-)"
            aria-label="Zoom Out"
            className="w-8 h-8 flex items-center justify-center rounded-lg text-zinc-300 hover:text-white hover:bg-white/10 transition-colors text-base font-bold"
          >
            -
          </button>
          {zoomLevel > 1 && (
            <>
              <div className="w-full h-[1px] bg-white/10" />
              <button
                onClick={handleResetZoom}
                title="Reset View (1x)"
                aria-label="Reset View"
                className="w-8 h-8 flex items-center justify-center rounded-lg text-[10px] font-bold text-cyan-400 hover:text-cyan-300 hover:bg-white/10 transition-colors"
              >
                {zoomLevel}x
              </button>
            </>
          )}
        </div>

        {/* Quick Focus Shortcuts on Active Cloud Clusters */}
        {clusters.length > 0 && (
          <div className="absolute top-4 right-4 z-20 flex items-center gap-1.5 bg-zinc-900/90 p-1.5 rounded-xl border border-white/10 shadow-2xl backdrop-blur-md text-xs">
            <span className="text-[11px] font-semibold text-zinc-400 px-1">🔍 ซูมกลุ่มฝน:</span>
            {clusters.map((c) => (
              <button
                key={c.id}
                onClick={() => handleFocusCluster(c)}
                className="px-2 py-1 rounded-lg bg-white/5 hover:bg-cyan-500/20 text-zinc-300 hover:text-cyan-300 border border-white/5 text-[11px] font-medium transition-colors"
              >
                {c.label.split(" ")[0]} ({c.intensity_dbz.toFixed(0)})
              </button>
            ))}
          </div>
        )}

        <svg
          viewBox={currentViewBox}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
          className={`w-full h-full select-none transition-all duration-200 ease-out ${
            isDragging ? "cursor-grabbing" : zoomLevel > 1 ? "cursor-grab" : "cursor-default"
          }`}
          role="img"
          aria-label="Radar Coverage Map"
        >
          <defs>
            {/* Telegram-style Multi-Layer Neon Glow Filter */}
            <filter id="neonGlowRed" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur1" />
              <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur2" />
              <feMerge>
                <feMergeNode in="blur1" />
                <feMergeNode in="blur2" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            <filter id="neonGlowPurple" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="3.5" result="blur1" />
              <feGaussianBlur in="SourceGraphic" stdDeviation="1.8" result="blur2" />
              <feMerge>
                <feMergeNode in="blur1" />
                <feMergeNode in="blur2" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Grid Radial Overlay */}
            <radialGradient id="radarScanGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
            </radialGradient>
            {/* Arrow Marker for Heading */}
            <marker id="arrow" viewBox="0 0 12 12" refX="10" refY="6" markerWidth="8" markerHeight="8" orient="auto">
              <path d="M 0 1 L 11 6 L 0 11 L 3 6 z" fill="#38bdf8" stroke="#ffffff" strokeWidth="0.8" />
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
              strokeWidth={zoomLevel >= 3 ? "0.4" : "0.8"}
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

          {/* Hierarchical Clustering / Spiderfy Expansion (De-clustering at zoomLevel >= 2.0) */}
          {(() => {
            // Determine active visible clusters: Flatten sub_clusters when zoomLevel >= 2.0 and clustering enabled
            const isDeClustered = enableClustering && zoomLevel >= 2.0;

            const visibleClusters: CloudCluster[] = [];
            const spiderfyConnectors: { parentPos: { x: number; y: number }; childPos: { x: number; y: number }; childId: string }[] = [];

            clusters.forEach((parent) => {
              if (isDeClustered && parent.sub_clusters && parent.sub_clusters.length > 0) {
                const parentPos = parent.lat !== undefined && parent.lng !== undefined
                  ? projectLatLng(parent.lat, parent.lng)
                  : { x: parent.cx ?? 0, y: parent.cy ?? 0 };

                parent.sub_clusters.forEach((sub) => {
                  visibleClusters.push(sub);
                  const childPos = sub.lat !== undefined && sub.lng !== undefined
                    ? projectLatLng(sub.lat, sub.lng)
                    : { x: sub.cx ?? 0, y: sub.cy ?? 0 };
                  spiderfyConnectors.push({ parentPos, childPos, childId: sub.id });
                });
              } else {
                visibleClusters.push(parent);
              }
            });

            return (
              <>
                {/* Spiderfy Connector Lines (Showing parent origin to sub-cell breakdown) */}
                {isDeClustered && spiderfyConnectors.map((conn) => (
                  <line
                    key={`spider-${conn.childId}`}
                    x1={conn.parentPos.x}
                    y1={conn.parentPos.y}
                    x2={conn.childPos.x}
                    y2={conn.childPos.y}
                    stroke="rgba(168, 85, 247, 0.4)"
                    strokeWidth="1.5"
                    strokeDasharray="3 3"
                    className="pointer-events-none"
                  />
                ))}

                {/* Render Visible Cloud Clusters (Parent or De-clustered Sub-cells) */}
                {visibleClusters.map((cluster) => {
                  const isHovered = hoveredCluster?.id === cluster.id;
                  const isPinned = pinnedCluster?.id === cluster.id;
                  const isActive = isHovered || isPinned;
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

                  const isChildCell = cluster.id.startsWith("sub-");

                  return (
                    <g
                      key={cluster.id}
                      data-testid={`cloud-cluster-${cluster.id}`}
                      className="cursor-pointer"
                      onClick={() => setPinnedCluster(isPinned ? null : cluster)}
                      onMouseEnter={() => setHoveredCluster(cluster)}
                      onMouseLeave={() => setHoveredCluster(null)}
                    >
                      {/* Telegram-style Multi-Pass Neon Glow Contour & Organic Body */}
                      {showCloudClusters && (() => {
                        const r = cluster.radius * 0.85;
                        const contourColor = isPinned ? "#38bdf8" : isChildCell ? "#c084fc" : dbzColor;
                        
                        // Generate organic natural cloud contour polygon (8-vertex perturbation)
                        const vertices = 8;
                        const polyPts: string[] = [];
                        for (let i = 0; i < vertices; i++) {
                          const angle = (i / vertices) * Math.PI * 2;
                          // Perturb radius slightly by 10-15% based on vertex index for realistic cloud contour shape
                          const noiseFactor = 1 + Math.sin(i * 2.5 + (cluster.id.charCodeAt(cluster.id.length - 1) % 5)) * 0.12;
                          const vx = clusterPos.x + Math.cos(angle) * (r * noiseFactor);
                          const vy = clusterPos.y + Math.sin(angle) * (r * noiseFactor);
                          polyPts.push(`${vx.toFixed(1)},${vy.toFixed(1)}`);
                        }
                        const polyPathD = `M ${polyPts.join(" L ")} Z`;

                        return (
                          <g className="transition-all duration-300">
                            {/* Layer 1: Semi-transparent Fill (alpha 40%) */}
                            <path
                              d={polyPathD}
                              fill={contourColor}
                              fillOpacity={isActive ? 0.45 : 0.30}
                              className="transition-all duration-300"
                            />

                            {/* Layer 2: Multi-Pass Neon Glow Border (Gaussian Glow) */}
                            <path
                              d={polyPathD}
                              fill="none"
                              stroke={contourColor}
                              strokeWidth={isActive ? 5.5 : 3.5}
                              strokeOpacity={0.65}
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              filter={isChildCell ? "url(#neonGlowPurple)" : "url(#neonGlowRed)"}
                            />

                            {/* Layer 3: Sharp Inner Border Core */}
                            <path
                              d={polyPathD}
                              fill="none"
                              stroke={isPinned ? "#ffffff" : isChildCell ? "#f3e8ff" : "#ffffff"}
                              strokeWidth={isActive ? 1.8 : 1.2}
                              strokeOpacity={0.95}
                              strokeLinejoin="round"
                            />
                          </g>
                        );
                      })()}

                      {/* Direct Crisp dBZ Number (Dark bold text with crisp white outline) */}
                      {showDbzLabels && (
                        <text
                          x={clusterPos.x}
                          y={clusterPos.y + 3.5}
                          textAnchor="middle"
                          fill="#090d16"
                          fontSize={isChildCell ? "9.5" : "11.5"}
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

                      {/* Cluster Label for Sub-cells when zoomed in */}
                      {isChildCell && showDbzLabels && (
                        <text
                          x={clusterPos.x}
                          y={clusterPos.y - cluster.radius - 2}
                          textAnchor="middle"
                          fill="#e9d5ff"
                          fontSize="8"
                          fontWeight="600"
                          className="pointer-events-none select-none drop-shadow-sm"
                        >
                          {cluster.label.split(" ")[0]}
                        </text>
                      )}

                      {/* Historical Trajectory Vectors & Waypoints */}
                      {isActive && (
                        <g data-testid={`trajectory-path-${cluster.id}`} className="pointer-events-none">
                          {trajectoryPoints.length > 0 && (
                            <>
                              {/* Path line connecting curved historical coordinates to current position */}
                              <path
                                d={`M ${trajectoryPoints.map((p) => `${p.x},${p.y}`).join(" L ")} L ${clusterPos.x},${clusterPos.y}`}
                                fill="none"
                                stroke={isChildCell ? "#c084fc" : "#06b6d4"}
                                strokeWidth="2.5"
                                strokeDasharray="5 3"
                                strokeLinecap="round"
                                className="filter drop-shadow-[0_0_8px_rgba(192,132,252,0.8)]"
                              />

                              {/* Historical frame waypoints with Dynamic Orthogonal Offset */}
                              {trajectoryPoints.map((pt, idx) => {
                                const prevPt = idx > 0 ? trajectoryPoints[idx - 1] : pt;
                                const nextPt = idx < trajectoryPoints.length - 1 ? trajectoryPoints[idx + 1] : clusterPos;
                                
                                const dx = nextPt.x - prevPt.x || 1;
                                const dy = nextPt.y - prevPt.y || 0;
                                const len = Math.hypot(dx, dy) || 1;
                                
                                const side = idx % 2 === 0 ? -1 : 1;
                                const nx = (-dy / len) * side;
                                const ny = (dx / len) * side;

                                const offsetDist = 18;
                                const badgeCenterX = pt.x + nx * offsetDist;
                                const badgeCenterY = pt.y + ny * offsetDist;

                                return (
                                  <g key={idx}>
                                    <circle
                                      cx={pt.x}
                                      cy={pt.y}
                                      r={3.8}
                                      fill={isChildCell ? "#d8b4fe" : "#22d3ee"}
                                      stroke="#020617"
                                      strokeWidth="1.8"
                                    />
                                    <line
                                      x1={pt.x}
                                      y1={pt.y}
                                      x2={badgeCenterX}
                                      y2={badgeCenterY}
                                      stroke="rgba(192, 132, 252, 0.5)"
                                      strokeWidth="1"
                                      strokeDasharray="2 2"
                                    />
                                    <rect
                                      x={badgeCenterX - 13}
                                      y={badgeCenterY - 6.5}
                                      width={26}
                                      height={13}
                                      rx={3}
                                      fill="#090d16"
                                      stroke={isChildCell ? "#c084fc" : "#38bdf8"}
                                      strokeWidth={1.1}
                                    />
                                    <text
                                      x={badgeCenterX}
                                      y={badgeCenterY + 3.2}
                                      textAnchor="middle"
                                      fill={isChildCell ? "#d8b4fe" : "#38bdf8"}
                                      fontSize="8"
                                      fontWeight="bold"
                                      className="select-none pointer-events-none"
                                    >
                                      {pt.time_offset_min}m
                                    </text>
                                  </g>
                                );
                              })}
                            </>
                          )}

                          {/* Velocity & Heading Vector Arrow (Always rendered on active/hover) */}
                          {(() => {
                            const heading = cluster.heading_deg ?? 90;
                            const rad = (heading - 90) * (Math.PI / 180);
                            const startX = clusterPos.x + Math.cos(rad) * (cluster.radius * 0.95);
                            const startY = clusterPos.y + Math.sin(rad) * (cluster.radius * 0.95);
                            const arrowLength = isChildCell ? 32 : 45;
                            const targetX = clusterPos.x + Math.cos(rad) * arrowLength;
                            const targetY = clusterPos.y + Math.sin(rad) * arrowLength;
                            return (
                              <line
                                x1={startX}
                                y1={startY}
                                x2={targetX}
                                y2={targetY}
                                stroke={isChildCell ? "#c084fc" : "#38bdf8"}
                                strokeWidth={isChildCell ? "2.2" : "2.8"}
                                markerEnd="url(#arrow)"
                              />
                            );
                          })()}
                        </g>
                      )}
                    </g>
                  );
                })}
              </>
            );
          })()}
        </svg>

        {/* Hover / Pinned Trajectory Floating Card (Issue #188) */}
        {(() => {
          const displayCluster = pinnedCluster || hoveredCluster;
          if (!displayCluster) return null;

          return (
            <div
              data-testid="trajectory-preview-card"
              className="absolute bottom-4 right-4 z-20 max-w-sm w-full p-4 rounded-xl bg-zinc-900/95 border border-cyan-500/40 shadow-2xl backdrop-blur-md text-white animate-in fade-in zoom-in-95 duration-150"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <CloudRain className="w-4 h-4 text-cyan-400" />
                  <span className="font-bold text-sm tracking-tight">{displayCluster.label}</span>
                  {pinnedCluster && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 font-medium">
                      📌 ปักหมุด
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 font-mono">
                    {displayCluster.intensity_dbz} dBZ
                  </span>
                  {pinnedCluster && (
                    <button
                      onClick={() => setPinnedCluster(null)}
                      title="ปิดหน้าต่าง (Close)"
                      aria-label="Close Preview"
                      className="p-1 rounded-lg hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs text-zinc-300 mb-3">
                <div className="flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Speed: <strong className="text-white font-mono">{displayCluster.velocity_kmh.toFixed(1)} km/h</strong></span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Navigation className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Heading: <strong className="text-white font-mono">{displayCluster.heading_deg}°</strong></span>
                </div>
              </div>

              {displayCluster.history_trajectory && (
                <div className="pt-2 border-t border-white/10 text-xs">
                  <div className="flex items-center gap-1 text-cyan-400 font-semibold mb-1">
                    <Clock className="w-3.5 h-3.5" />
                    <span>Historical Movement:</span>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-zinc-400 overflow-x-auto">
                    {displayCluster.history_trajectory.map((pt, i) => (
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
          );
        })()}

        {/* Station Hover Tooltip */}
        {hoveredStation && !hoveredCluster && !pinnedCluster && (
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
