"use client";

import { useState } from "react";
import useSWR from "swr";
import { GlassNavbar } from "@/components/GlassNavbar";
import {
  AlertTriangle,
  CheckCircle2,
  TrendingDown,
  DollarSign,
  Calendar,
  BarChart3,
  TrendingUp,
} from "lucide-react";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

function SkeletonPulse({ className = "h-8 w-20" }: { className?: string }) {
  return <span className={`inline-block bg-slate-700/60 animate-pulse rounded-lg align-middle ${className}`} />;
}

type TimeframeView = "daily" | "monthly" | "yearly";

interface ChartBarItem {
  key: string;
  label: string;
  total: number;
  true_alarm: number;
  false_alarm: number;
}

export default function AdminMetricsPage() {
  const currentMonth = new Date().toISOString().slice(0, 7);
  const currentYear = new Date().getFullYear().toString();
  const [selectedMonth, setSelectedMonth] = useState(currentMonth);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [activeTab, setActiveTab] = useState<TimeframeView>("daily");
  const [hoveredItem, setHoveredItem] = useState<ChartBarItem | null>(null);

  const { data: metricsData, isLoading: metricsLoading } = useSWR(
    `/api/v1/metrics/monthly?month=${selectedMonth}`,
    fetcher
  );

  const { data: yearlyData, isLoading: yearlyLoading } = useSWR(
    `/api/v1/metrics/yearly?year=${selectedYear}`,
    fetcher
  );

  const { data: costData, isLoading: costLoading } = useSWR(
    `/api/v1/metrics/cost?month=${selectedMonth}`,
    fetcher
  );

  // Prepare chart items based on selected timeframe
  let chartItems: ChartBarItem[] = [];
  let chartLoading = false;

  if (activeTab === "daily") {
    chartLoading = metricsLoading;
    const rawList = metricsData?.daily_breakdown || [];
    chartItems = rawList.map((d: { date: string; total: number; true_alarm: number; false_alarm: number }) => ({
      key: d.date,
      label: d.date.slice(8), // day 'DD'
      total: d.total,
      true_alarm: d.true_alarm,
      false_alarm: d.false_alarm,
    }));
  } else if (activeTab === "monthly") {
    chartLoading = yearlyLoading;
    const rawList = yearlyData?.monthly_breakdown || [];
    const monthNames = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."];
    chartItems = rawList.map((m: { month: string; total: number; true_alarm: number; false_alarm: number }, idx: number) => ({
      key: m.month,
      label: monthNames[idx] || m.month.slice(5),
      total: m.total,
      true_alarm: m.true_alarm,
      false_alarm: m.false_alarm,
    }));
  } else {
    // Yearly: 3-year trend overview
    chartLoading = yearlyLoading;
    const curY = Number(selectedYear);
    chartItems = [
      {
        key: `${curY - 2}`,
        label: `${curY - 2}`,
        total: 0,
        true_alarm: 0,
        false_alarm: 0,
      },
      {
        key: `${curY - 1}`,
        label: `${curY - 1}`,
        total: 0,
        true_alarm: 0,
        false_alarm: 0,
      },
      {
        key: `${curY}`,
        label: `${curY}`,
        total: yearlyData?.total_alerts || 0,
        true_alarm: yearlyData?.true_alarms || 0,
        false_alarm: yearlyData?.false_alarms_total || 0,
      },
    ];
  }

  const maxBarTotal = Math.max(...chartItems.map((c) => c.total), 1);

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
              onChange={(e) => {
                setSelectedMonth(e.target.value);
                if (e.target.value) {
                  setSelectedYear(e.target.value.slice(0, 4));
                }
              }}
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

        {/* 📈 Graphical Alert Breakdown & Accuracy Trends (Daily / Monthly / Yearly) */}
        <div
          data-testid={`chart-${activeTab}`}
          className="p-6 rounded-2xl bg-slate-900/60 backdrop-blur-xl border border-white/10 shadow-2xl space-y-6"
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                <BarChart3 className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  แนวโน้มการแจ้งเตือนและการเตือนลวง
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-normal border border-white/10">
                    {activeTab === "daily" && `รายวัน (เดือน ${selectedMonth})`}
                    {activeTab === "monthly" && `รายเดือน (ปี ${selectedYear})`}
                    {activeTab === "yearly" && `ภาพรวมรายปี`}
                  </span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  เปรียบเทียบการเตือนจริง (True Alarm) กับการเตือนลวง (False Alarm)
                </p>
              </div>
            </div>

            {/* Timeframe View Toggles */}
            <div className="flex items-center p-1 bg-slate-950/60 border border-white/10 rounded-xl">
              <button
                type="button"
                onClick={() => setActiveTab("daily")}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  activeTab === "daily"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                รายวัน (Daily)
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("monthly")}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  activeTab === "monthly"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                รายเดือน (Monthly)
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("yearly")}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  activeTab === "yearly"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                รายปี (Yearly)
              </button>
            </div>
          </div>

          {/* Chart Legend & Hover Indicator */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-white/5 text-xs">
            <div className="flex items-center gap-4 text-slate-300">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-emerald-400 shadow-sm shadow-emerald-400/30" />
                <span>เตือนจริง (True Alarm)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-rose-400 shadow-sm shadow-rose-400/30" />
                <span>เตือนลวง (False Alarm)</span>
              </div>
            </div>

            {hoveredItem ? (
              <div className="text-slate-300 bg-slate-800/80 px-3 py-1 rounded-lg border border-white/10 flex items-center gap-3">
                <span className="font-semibold text-white">{hoveredItem.key}</span>
                <span className="text-emerald-400">จริง: {hoveredItem.true_alarm}</span>
                <span className="text-rose-400">ลวง: {hoveredItem.false_alarm}</span>
                <span className="text-slate-400">รวม: {hoveredItem.total}</span>
              </div>
            ) : (
              <span className="text-slate-500 italic">เอาเมาส์ชี้ที่แท่งกราฟเพื่อดูรายละเอียด</span>
            )}
          </div>

          {/* Interactive Bar Chart */}
          <div className="relative h-64 w-full pt-4 flex items-end gap-1.5 sm:gap-3 overflow-x-auto pb-4">
            {chartLoading ? (
              <div className="w-full h-full flex items-center justify-center">
                <SkeletonPulse className="h-32 w-full" />
              </div>
            ) : chartItems.length === 0 ? (
              <div className="w-full h-full flex flex-col items-center justify-center text-slate-500 gap-2">
                <BarChart3 className="w-8 h-8 opacity-40" />
                <span>ไม่มีข้อมูลการแจ้งเตือนในช่วงเวลานี้</span>
              </div>
            ) : (
              chartItems.map((item) => {
                const heightPct = item.total > 0 ? Math.max((item.total / maxBarTotal) * 100, 6) : 2;
                const truePct = item.total > 0 ? (item.true_alarm / item.total) * 100 : 0;
                const falsePct = item.total > 0 ? (item.false_alarm / item.total) * 100 : 0;

                return (
                  <div
                    key={item.key}
                    onMouseEnter={() => setHoveredItem(item)}
                    onMouseLeave={() => setHoveredItem(null)}
                    className="flex-1 min-w-[20px] max-w-[48px] h-full flex flex-col justify-end items-center group cursor-pointer"
                  >
                    {/* Bar Stack */}
                    <div
                      style={{ height: `${heightPct}%` }}
                      className="w-full rounded-t-md overflow-hidden flex flex-col-reverse bg-slate-800/60 border border-white/5 group-hover:border-cyan-400/50 transition-all shadow-lg"
                    >
                      {item.total === 0 ? (
                        <div className="w-full h-full bg-slate-800/30" />
                      ) : (
                        <>
                          {/* True Alarm segment (emerald) */}
                          <div
                            style={{ height: `${truePct}%` }}
                            className="w-full bg-emerald-500/80 group-hover:bg-emerald-400 transition-colors"
                          />
                          {/* False Alarm segment (rose) */}
                          <div
                            style={{ height: `${falsePct}%` }}
                            className="w-full bg-rose-500/80 group-hover:bg-rose-400 transition-colors"
                          />
                        </>
                      )}
                    </div>

                    {/* X-axis Label */}
                    <span className="text-[10px] text-slate-400 mt-2 truncate w-full text-center group-hover:text-cyan-300 font-medium transition-colors">
                      {item.label}
                    </span>
                  </div>
                );
              })
            )}
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
