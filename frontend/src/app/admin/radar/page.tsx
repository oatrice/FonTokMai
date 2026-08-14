"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/ui/Header";
import { RadarCloudMap, RadarStation, CloudCluster } from "@/components/map/RadarCloudMap";
import { Radio, RefreshCw, CheckCircle2, AlertTriangle, XCircle, Clock, ExternalLink, Filter, Sliders, Activity } from "lucide-react";
import { CalibrationView } from "./CalibrationView";

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
  const [activeTab, setActiveTab] = useState<"status" | "calibrate">("status");
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

  const onlineCount = stations.filter((st) => st.status === "online").length;
  const delayedCount = stations.filter((st) => st.status === "delayed").length;
  const offlineCount = stations.filter((st) => st.status === "offline").length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 pb-16">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        {/* Navigation Tabs Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6 mb-8">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <Radio className="w-8 h-8 text-sky-400 animate-pulse" />
              TMD Radar Administration & Live Operations
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              ระบบตรวจสอบความพร้อมและบริหารจัดการสถานีเรดาร์ตรวจอากาศทั่วประเทศ 13 สถานี
            </p>
          </div>

          <div className="flex items-center gap-2 bg-slate-900/80 p-1.5 rounded-xl border border-slate-800 self-start sm:self-auto">
            <button
              onClick={() => setActiveTab("status")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === "status"
                  ? "bg-sky-500 text-white shadow-lg shadow-sky-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <Activity className="w-4 h-4" />
              Radar Status Map (Live)
            </button>
            <button
              onClick={() => setActiveTab("calibrate")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === "calibrate"
                  ? "bg-sky-500 text-white shadow-lg shadow-sky-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <Sliders className="w-4 h-4" />
              Auto-Calibration & DB Seeding
            </button>
          </div>
        </div>

        {/* Tab 1: Live Status & Cloud Map */}
        {activeTab === "status" && (
          <div>
            {/* Top KPI Cards & Refresh Action */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
              <div className="bg-slate-900/60 backdrop-blur border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Total Stations
                </span>
                <div className="text-3xl font-extrabold text-white mt-2">{stations.length}</div>
              </div>

              <div className="bg-emerald-950/20 border border-emerald-800/40 rounded-2xl p-4 flex flex-col justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Online
                </span>
                <div className="text-3xl font-extrabold text-emerald-300 mt-2">{onlineCount}</div>
              </div>

              <div className="bg-amber-950/20 border border-amber-800/40 rounded-2xl p-4 flex flex-col justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" /> Delayed
                </span>
                <div className="text-3xl font-extrabold text-amber-300 mt-2">{delayedCount}</div>
              </div>

              <div className="bg-rose-950/20 border border-rose-800/40 rounded-2xl p-4 flex flex-col justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
                  <XCircle className="w-3.5 h-3.5" /> Offline
                </span>
                <div className="text-3xl font-extrabold text-rose-300 mt-2">{offlineCount}</div>
              </div>
            </div>

            {/* Filter and Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 rounded-2xl p-3.5 mb-6">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-400 ml-1" />
                <span className="text-xs font-semibold text-slate-400 mr-2">Filter:</span>
                {["all", "online", "delayed", "offline"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setFilterStatus(st)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium uppercase tracking-wider transition-all ${
                      filterStatus === st
                        ? "bg-slate-700 text-white shadow-sm"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-500 hidden sm:inline flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Updated {lastRefreshed.toLocaleTimeString()}
                </span>
                <button
                  onClick={fetchStations}
                  disabled={loading}
                  className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium px-3.5 py-2 rounded-xl border border-slate-700 transition"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-sky-400" : ""}`} />
                  Refresh
                </button>
              </div>
            </div>

            {/* Main Interactive Map & Details Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              {/* Thailand Radar Map */}
              <div className="lg:col-span-8 bg-slate-900/70 border border-slate-800/80 rounded-3xl p-6 shadow-2xl backdrop-blur relative">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
                    Thailand Real-Time Radar Coverage & Cloud Tracking
                  </h2>
                  <span className="text-xs text-slate-400 bg-slate-800/80 px-2.5 py-1 rounded-full border border-slate-700/50">
                    Hover cloud cluster to inspect trajectory
                  </span>
                </div>

                <RadarCloudMap
                  stations={filteredStations}
                  clusters={DEMO_CLUSTERS}
                  selectedStation={selectedStation}
                  onSelectStation={(st) => setSelectedStation(st)}
                />
              </div>

              {/* Station Detail List / Cards */}
              <div className="lg:col-span-4 space-y-4">
                <h3 className="text-base font-bold text-slate-300 px-1 flex items-center justify-between">
                  <span>Active Stations ({filteredStations.length})</span>
                  {selectedStation && (
                    <button
                      onClick={() => setSelectedStation(null)}
                      className="text-xs text-sky-400 hover:underline"
                    >
                      Clear Selection
                    </button>
                  )}
                </h3>

                <div className="space-y-3 max-h-[640px] overflow-y-auto pr-1">
                  {filteredStations.map((st) => {
                    const isSelected = selectedStation?.code === st.code;
                    return (
                      <div
                        key={st.code}
                        onClick={() => setSelectedStation(st)}
                        className={`cursor-pointer rounded-2xl p-4 border transition-all ${
                          isSelected
                            ? "bg-slate-800/90 border-sky-500/80 shadow-lg shadow-sky-500/10 ring-1 ring-sky-500/50"
                            : "bg-slate-900/50 border-slate-800/80 hover:bg-slate-800/50 hover:border-slate-700"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div>
                            <h4 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                              {st.name}
                              <span className="text-[10px] font-mono uppercase bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
                                {st.code}
                              </span>
                            </h4>
                            <p className="text-xs text-slate-400 mt-0.5">
                              {st.center_lat.toFixed(4)}°N, {st.center_lng.toFixed(4)}°E (Radius {st.radius_km}km)
                            </p>
                          </div>

                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                              st.status === "online"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                                : st.status === "delayed"
                                ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                                : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                            }`}
                          >
                            {st.status}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/60 mt-3">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3 text-slate-500" /> Latency: {st.latency_minutes}m
                          </span>
                          <div className="flex items-center gap-3">
                            <a
                              href={st.image_url}
                              target="_blank"
                              rel="noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="text-sky-400 hover:text-sky-300 flex items-center gap-0.5 text-[11px]"
                            >
                              Frame <ExternalLink className="w-3 h-3" />
                            </a>
                            <a
                              href={st.loop_url}
                              target="_blank"
                              rel="noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="text-sky-400 hover:text-sky-300 flex items-center gap-0.5 text-[11px]"
                            >
                              TMD Loop <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Calibration & Seeding View */}
        {activeTab === "calibrate" && (
          <div className="mt-2">
            <CalibrationView />
          </div>
        )}
      </main>
    </div>
  );
}
