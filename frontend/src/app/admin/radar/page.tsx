"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/ui/Header";
import { RadarCloudMap, RadarStation, CloudCluster } from "@/components/map/RadarCloudMap";
import { Radio, RefreshCw, CheckCircle2, AlertTriangle, XCircle, Clock, ExternalLink, Filter } from "lucide-react";

const DEMO_CLUSTERS: CloudCluster[] = [
  {
    id: "cluster-kkn-storm",
    label: "Khon Kaen Core Cell",
    cx: 440,
    cy: 280,
    radius: 32,
    intensity_dbz: 52.0,
    velocity_kmh: 28.5,
    heading_deg: 80,
    eta_min: 15,
    history_trajectory: [
      { time_offset_min: -20, cx: 370, cy: 300, dbz: 44.0 },
      { time_offset_min: -15, cx: 390, cy: 295, dbz: 48.0 },
      { time_offset_min: -10, cx: 410, cy: 290, dbz: 50.0 },
      { time_offset_min: -5, cx: 425, cy: 285, dbz: 51.5 },
    ],
  },
  {
    id: "cluster-skn-band",
    label: "Sakon Nakhon Rain Band",
    cx: 530,
    cy: 210,
    radius: 26,
    intensity_dbz: 38.0,
    velocity_kmh: 22.0,
    heading_deg: 110,
    eta_min: 25,
    history_trajectory: [
      { time_offset_min: -15, cx: 490, cy: 195, dbz: 35.0 },
      { time_offset_min: -10, cx: 505, cy: 200, dbz: 36.5 },
      { time_offset_min: -5, cx: 518, cy: 205, dbz: 37.0 },
    ],
  },
  {
    id: "cluster-south-cell",
    label: "Korat Inbound Cell",
    cx: 350,
    cy: 390,
    radius: 22,
    intensity_dbz: 42.5,
    velocity_kmh: 19.0,
    heading_deg: 65,
    eta_min: 35,
    history_trajectory: [
      { time_offset_min: -10, cx: 320, cy: 405, dbz: 39.0 },
      { time_offset_min: -5, cx: 335, cy: 398, dbz: 41.0 },
    ],
  },
];

export default function AdminRadarPage() {
  const [stations, setStations] = useState<RadarStation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedStation, setSelectedStation] = useState<RadarStation | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const fetchStations = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/radar");
      if (res.ok) {
        const data = await res.json();
        setStations(data.stations || []);
      }
    } catch (e) {
      console.error("Failed to fetch radar station statuses:", e);
    } finally {
      setLoading(false);
      setLastRefreshed(new Date());
    }
  }, []);

  useEffect(() => {
    fetchStations();
  }, [fetchStations]);

  const filteredStations = stations.filter((st) => {
    if (filterStatus === "all") return true;
    return st.status === filterStatus;
  });

  const onlineCount = stations.filter((s) => s.status === "online").length;
  const delayedCount = stations.filter((s) => s.status === "delayed").length;
  const offlineCount = stations.filter((s) => s.status === "offline").length;
  const avgLatency = stations.length > 0
    ? (stations.reduce((acc, s) => acc + (s.latency_minutes || 0), 0) / stations.length).toFixed(1)
    : "0.0";

  return (
    <div className="min-h-screen bg-black text-zinc-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-10 space-y-8">
        {/* Header & Controls */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-400 mb-1">
              <Radio className="w-4 h-4 animate-pulse" />
              <span>Admin Operations</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white">
              Radar Station Monitoring
            </h1>
            <p className="text-zinc-400 text-sm mt-1">
              Real-time station frame ingest latency, online/offline status, and cloud cluster movement trajectories.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchStations}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-semibold text-zinc-200 hover:text-white transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-cyan-400" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-zinc-900/60 border border-white/10 backdrop-blur-md">
            <div className="text-xs text-zinc-400 font-medium">Total Stations</div>
            <div className="text-2xl font-bold text-white mt-1">{stations.length}</div>
            <div className="text-[11px] text-zinc-500 mt-0.5">Configured nationwide</div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-900/60 border border-emerald-500/20 backdrop-blur-md">
            <div className="text-xs text-emerald-400 font-medium flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Active Online</span>
            </div>
            <div className="text-2xl font-bold text-white mt-1">{onlineCount}</div>
            <div className="text-[11px] text-emerald-500/80 mt-0.5">&lt; 30m frame latency</div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-900/60 border border-amber-500/20 backdrop-blur-md">
            <div className="text-xs text-amber-400 font-medium flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Delayed Ingest</span>
            </div>
            <div className="text-2xl font-bold text-white mt-1">{delayedCount}</div>
            <div className="text-[11px] text-amber-500/80 mt-0.5">30-60m frame latency</div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-900/60 border border-cyan-500/20 backdrop-blur-md">
            <div className="text-xs text-cyan-400 font-medium flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              <span>Average Latency</span>
            </div>
            <div className="text-2xl font-bold text-white mt-1">{avgLatency} <span className="text-sm font-normal text-zinc-400">min</span></div>
            <div className="text-[11px] text-zinc-500 mt-0.5">Updated {lastRefreshed.toLocaleTimeString()}</div>
          </div>
        </div>

        {/* Interactive Map Visualizer */}
        <RadarCloudMap
          stations={stations}
          clusters={DEMO_CLUSTERS}
          selectedStationCode={selectedStation?.code}
          onSelectStation={(st) => setSelectedStation(st)}
        />

        {/* Station List Table & Filter Section */}
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-bold text-white">Radar Stations Directory</h2>

            {/* Filter Tabs */}
            <div className="flex items-center gap-1 p-1 rounded-xl bg-zinc-900/80 border border-white/10 text-xs">
              {(["all", "online", "delayed", "offline"] as const).map((status) => (
                <button
                  key={status}
                  onClick={() => setFilterStatus(status)}
                  className={`px-3 py-1.5 rounded-lg capitalize transition-all ${
                    filterStatus === status
                      ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30"
                      : "text-zinc-400 hover:text-white"
                  }`}
                >
                  {status}
                </button>
              ))}
            </div>
          </div>

          {/* Table Container */}
          <div className="rounded-2xl border border-white/10 overflow-hidden bg-zinc-950/60 backdrop-blur-md">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-zinc-300">
                <thead className="bg-white/[0.03] border-b border-white/10 text-zinc-400 uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="px-4 py-3">Station</th>
                    <th className="px-4 py-3">Code</th>
                    <th className="px-4 py-3">Coordinates</th>
                    <th className="px-4 py-3">Coverage</th>
                    <th className="px-4 py-3">Latency</th>
                    <th className="px-4 py-3">Last Updated</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {filteredStations.map((st) => (
                    <tr
                      key={st.code}
                      onClick={() => setSelectedStation(st)}
                      className={`cursor-pointer hover:bg-white/[0.04] transition-colors ${
                        selectedStation?.code === st.code ? "bg-cyan-500/[0.08]" : ""
                      }`}
                    >
                      <td className="px-4 py-3 font-semibold text-white">{st.name}</td>
                      <td className="px-4 py-3 font-mono text-cyan-400">{st.code}</td>
                      <td className="px-4 py-3 text-zinc-400">{st.center_lat.toFixed(2)}°N, {st.center_lng.toFixed(2)}°E</td>
                      <td className="px-4 py-3 text-zinc-300">{st.radius_km} km</td>
                      <td className="px-4 py-3 font-mono font-bold text-white">{st.latency_minutes}m</td>
                      <td className="px-4 py-3 text-zinc-400">{new Date(st.last_frame_timestamp).toLocaleTimeString()}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-semibold text-[11px] ${
                            st.status === "online"
                              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                              : st.status === "delayed"
                              ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                              : "bg-red-500/20 text-red-400 border border-red-500/30"
                          }`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${st.status === "online" ? "bg-emerald-400" : st.status === "delayed" ? "bg-amber-400" : "bg-red-400"}`} />
                          {st.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {st.loop_url && (
                          <a
                            href={st.loop_url}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 hover:underline"
                          >
                            <span>Loop</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                  {filteredStations.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-zinc-500">
                        No radar stations found matching selected status filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-white/10 py-6 text-center text-xs text-zinc-600">
        FonMaYang Radar Ingest & Spatial Analysis Engine © 2026.
      </footer>
    </div>
  );
}
