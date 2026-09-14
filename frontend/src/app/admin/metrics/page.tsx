"use client";

import { useState } from "react";
import useSWR from "swr";
import { GlassNavbar } from "@/components/GlassNavbar";
import { AlertTriangle, CheckCircle2, TrendingDown, DollarSign, Calendar } from "lucide-react";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

function SkeletonPulse({ className = "h-8 w-20" }: { className?: string }) {
  return <span className={`inline-block bg-slate-700/60 animate-pulse rounded-lg align-middle ${className}`} />;
}

export default function AdminMetricsPage() {
  const currentMonth = new Date().toISOString().slice(0, 7);
  const [selectedMonth, setSelectedMonth] = useState(currentMonth);

  const { data: metricsData, isLoading: metricsLoading } = useSWR(
    `/api/v1/metrics/monthly?month=${selectedMonth}`,
    fetcher
  );

  const { data: costData, isLoading: costLoading } = useSWR(
    `/api/v1/metrics/cost?month=${selectedMonth}`,
    fetcher
  );

  return (
    <div className="min-h-screen flex flex-col selection:bg-cyan-500/30 selection:text-cyan-200">
      <GlassNavbar onOpenDonation={() => {}} />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Header with Month Selector */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-6 rounded-2xl bg-slate-900/60 backdrop-blur-xl border border-white/10 shadow-2xl">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-wide flex items-center gap-3">
              📊 Alert Accuracy & Unit Economics
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              ภาพรวมสถิติความแม่นยำของการเตือนฝน และต้นทุนค่าใช้จ่ายเฉลี่ยต่อการแจ้งเตือน
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Calendar className="w-5 h-5 text-cyan-400" />
            <input
              type="month"
              aria-label="เลือกเดือนสำหรับดูสถิติ"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="bg-slate-800/80 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
          </div>
        </div>

        {/* Summary Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Proactive Alerts */}
          <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-lg border border-white/10 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs uppercase tracking-wider font-semibold">Proactive Alerts</span>
              <Calendar className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="mt-4">
              <span className="text-3xl font-extrabold text-white">
                {costLoading ? <SkeletonPulse /> : costData?.proactive_count ?? 0}
              </span>
              <span className="text-xs text-slate-400 ml-2">ครั้ง</span>
            </div>
          </div>

          {/* On-Demand Queries */}
          <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-lg border border-white/10 flex flex-col justify-between">
            <div className="flex items-center justify-between text-emerald-400">
              <span className="text-xs uppercase tracking-wider font-semibold">On-Demand Queries</span>
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <div className="mt-4">
              <span className="text-3xl font-extrabold text-emerald-400">
                {costLoading ? <SkeletonPulse /> : costData?.ondemand_count ?? 0}
              </span>
              <span className="text-xs text-slate-400 ml-2">
                ครั้ง
              </span>
            </div>
          </div>

          {/* Cost per Proactive Alert */}
          <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-lg border border-white/10 flex flex-col justify-between">
            <div className="flex items-center justify-between text-amber-400">
              <span className="text-xs uppercase tracking-wider font-semibold">Cost / Proactive Alert</span>
              <DollarSign className="w-4 h-4" />
            </div>
            <div className="mt-4">
              <span className="text-3xl font-extrabold text-amber-400">
                {costLoading ? <SkeletonPulse /> : `฿${costData?.cost_per_proactive_alert?.toFixed(2) ?? "0.00"}`}
              </span>
              <span className="text-xs text-slate-400 ml-2">
                ต่อครั้ง
              </span>
            </div>
          </div>

          {/* Cost per On-Demand Query */}
          <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-lg border border-white/10 flex flex-col justify-between">
            <div className="flex items-center justify-between text-cyan-400">
              <span className="text-xs uppercase tracking-wider font-semibold">Cost / On-Demand Query</span>
              <DollarSign className="w-4 h-4" />
            </div>
            <div className="mt-4">
              <span className="text-3xl font-extrabold text-cyan-400">
                {costLoading ? <SkeletonPulse /> : `฿${costData?.cost_per_ondemand_query?.toFixed(2) ?? "0.00"}`}
              </span>
              <span className="text-xs text-slate-400 ml-2">ต่อครั้ง</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Active Users (MAU) */}
          <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-lg border border-white/10 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs uppercase tracking-wider font-semibold">Active Users (MAU)</span>
              <Calendar className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="mt-4">
              <span className="text-3xl font-extrabold text-white">
                {costLoading ? <SkeletonPulse /> : costData?.mau_count ?? 0}
              </span>
              <span className="text-xs text-slate-400 ml-2">คน</span>
            </div>
          </div>

          {/* Blended Cost per User */}
          <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-lg border border-white/10 flex flex-col justify-between">
            <div className="flex items-center justify-between text-indigo-400">
              <span className="text-xs uppercase tracking-wider font-semibold">Blended Cost / User</span>
              <DollarSign className="w-4 h-4" />
            </div>
            <div className="mt-4">
              <span className="text-3xl font-extrabold text-indigo-400">
                {costLoading ? <SkeletonPulse /> : `฿${costData?.blended_cost_per_active_user?.toFixed(2) ?? "0.00"}`}
              </span>
              <span className="text-xs text-slate-400 ml-2">ต่อคน</span>
            </div>
          </div>

          {/* False Alarms Rate */}
          <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-lg border border-white/10 flex flex-col justify-between">
            <div className="flex items-center justify-between text-amber-500">
              <span className="text-xs uppercase tracking-wider font-semibold">False Alarms Rate</span>
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div className="mt-4">
              <span className="text-3xl font-extrabold text-amber-500">
                {metricsLoading ? <SkeletonPulse /> : `${metricsData?.false_alarm_rate_pct ?? 0}%`}
              </span>
              <span className="text-xs text-slate-400 ml-2">
                ({metricsData?.false_alarms_total ?? 0} ครั้ง)
              </span>
            </div>
          </div>
        </div>

        {/* Cost Breakdown & Verification Details */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* False Alarm Verification Breakdown */}
          <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-xl border border-white/10 space-y-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-amber-400" />
              ที่มาของการตรวจพบ False Alarm
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/40 border border-white/5">
                <span className="text-sm text-slate-300">รายงานโดยผู้ใช้ (กดปุ่ม ❌ ใน Telegram)</span>
                <span className="text-base font-bold text-amber-300">{metricsData?.false_alarms_user ?? 0} ครั้ง</span>
              </div>
              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/40 border border-white/5">
                <span className="text-sm text-slate-300">ระบบตรวจสอบอัตโนมัติ (Auto-Verify +30m)</span>
                <span className="text-base font-bold text-amber-300">{metricsData?.false_alarms_auto ?? 0} ครั้ง</span>
              </div>
            </div>
          </div>

          {/* Monthly Cost Breakdown */}
          <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-xl border border-white/10 space-y-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-cyan-400" />
              โครงสร้างต้นทุนเดือน {selectedMonth}
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/40 border border-white/5">
                <span className="text-sm text-slate-300">☁️ Google Cloud Platform (Run + DB)</span>
                <span className="text-base font-bold text-white">฿{costData?.gcp_cost_thb?.toFixed(2) ?? "0.00"}</span>
              </div>
              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/40 border border-white/5">
                <span className="text-sm text-slate-300">🌐 External Services (Radar APIs + Proxy Pool)</span>
                <span className="text-base font-bold text-white">฿{costData?.external_cost_thb?.toFixed(2) ?? "0.00"}</span>
              </div>
              <div className="flex items-center justify-between p-4 rounded-xl bg-cyan-950/40 border border-cyan-500/30">
                <span className="text-sm font-semibold text-cyan-200">💵 รวมต้นทุนทั้งหมด</span>
                <span className="text-lg font-extrabold text-cyan-300">฿{costData?.total_cost_thb?.toFixed(2) ?? "0.00"}</span>
              </div>
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
