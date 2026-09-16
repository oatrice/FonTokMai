"use client";

import { useState } from "react";
import useSWR from "swr";
import { GlassNavbar } from "@/components/GlassNavbar";
import {
  AlertTriangle,
  CheckCircle2,
  TrendingDown,
  Calendar,
  BarChart3,
  TrendingUp,
  Coins,
} from "lucide-react";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

function SkeletonPulse({ className = "h-8 w-20" }: { className?: string }) {
  return <span className={`inline-block bg-slate-700/60 animate-pulse rounded-lg align-middle ${className}`} />;
}

// Authentic Thai Baht (฿) Icon to replace DollarSign
function BahtIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center justify-center font-bold select-none leading-none ${className}`}
      aria-label="บาท (THB)"
    >
      ฿
    </span>
  );
}

type TimeframeView = "daily" | "monthly" | "yearly" | "cost";

interface ChartBarItem {
  key: string;
  label: string;
  total: number;
  true_alarm: number;
  false_alarm: number;
  // Optional breakdown for cost
  gcp_cost?: number;
  ext_cost?: number;
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

  const { data: yearlyCostData, isLoading: yearlyCostLoading } = useSWR(
    `/api/v1/metrics/cost/yearly?year=${selectedYear}`,
    fetcher
  );

  // Prepare chart items based on selected timeframe
  let chartItems: ChartBarItem[] = [];
  let chartLoading = false;

  const monthNames = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."];

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
    chartItems = rawList.map((m: { month: string; total: number; true_alarm: number; false_alarm: number }, idx: number) => ({
      key: m.month,
      label: monthNames[idx] || m.month.slice(5),
      total: m.total,
      true_alarm: m.true_alarm,
      false_alarm: m.false_alarm,
    }));
  } else if (activeTab === "yearly") {
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
  } else if (activeTab === "cost") {
    // Cost breakdown across 12 months for selectedYear
    chartLoading = yearlyCostLoading;
    const rawCostList = yearlyCostData?.monthly_cost_breakdown || [];
    chartItems = rawCostList.map((c: { month: string; total_cost_thb: number; gcp_cost_thb: number; external_cost_thb: number }, idx: number) => ({
      key: c.month,
      label: monthNames[idx] || c.month.slice(5),
      total: c.total_cost_thb,
      true_alarm: c.gcp_cost_thb, // reusing true_alarm as GCP segment
      false_alarm: c.external_cost_thb, // reusing false_alarm as External segment
      gcp_cost: c.gcp_cost_thb,
      ext_cost: c.external_cost_thb,
    }));
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
              <BahtIcon className="w-4 h-4 text-amber-400 text-sm" />
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
              <BahtIcon className="w-4 h-4 text-cyan-400 text-sm" />
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
              <BahtIcon className="w-4 h-4 text-indigo-400 text-sm" />
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

        {/* 📈 Graphical Alert Breakdown & Accuracy Trends (Daily / Monthly / Yearly / Cost) */}
        <div
          data-testid={`chart-${activeTab}`}
          className="p-6 rounded-2xl bg-slate-900/60 backdrop-blur-xl border border-white/10 shadow-2xl space-y-6"
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                {activeTab === "cost" ? <Coins className="w-5 h-5" /> : <BarChart3 className="w-5 h-5" />}
              </div>
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  {activeTab === "cost" ? "กราฟโครงสร้างต้นทุนและค่าใช้จ่าย" : "แนวโน้มการแจ้งเตือนและการเตือนลวง"}
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-normal border border-white/10">
                    {activeTab === "daily" && `รายวัน (เดือน ${selectedMonth})`}
                    {activeTab === "monthly" && `รายเดือน (ปี ${selectedYear})`}
                    {activeTab === "yearly" && `ภาพรวมรายปี`}
                    {activeTab === "cost" && `ต้นทุนรายเดือน (ปี ${selectedYear})`}
                  </span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  {activeTab === "cost"
                    ? "เปรียบเทียบค่าบริการ GCP Infrastructure กับค่าบริการภายนอก (Radar APIs & Proxy Pool)"
                    : "เปรียบเทียบการเตือนจริง (True Alarm) กับการเตือนลวง (False Alarm)"}
                </p>
              </div>
            </div>

            {/* Timeframe View Toggles */}
            <div className="flex flex-wrap items-center p-1 bg-slate-950/60 border border-white/10 rounded-xl gap-1">
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
              <button
                type="button"
                onClick={() => setActiveTab("cost")}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
                  activeTab === "cost"
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Coins className="w-3.5 h-3.5" />
                ต้นทุนค่าใช้จ่าย (Cost)
              </button>
            </div>
          </div>

          {/* Chart Legend & Hover Indicator */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-white/5 text-xs">
            {activeTab === "cost" ? (
              <div className="flex items-center gap-4 text-slate-300">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-sm bg-cyan-400 shadow-sm shadow-cyan-400/30" />
                  <span>Google Cloud Platform (Run + DB)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-sm bg-purple-400 shadow-sm shadow-purple-400/30" />
                  <span>External Services (Radar APIs + Proxy)</span>
                </div>
              </div>
            ) : (
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
            )}

            {hoveredItem ? (
              <div className="text-slate-300 bg-slate-800/80 px-3 py-1 rounded-lg border border-white/10 flex items-center gap-3">
                <span className="font-semibold text-white">{hoveredItem.key}</span>
                {activeTab === "cost" ? (
                  <>
                    <span className="text-cyan-400">GCP: ฿{(hoveredItem.gcp_cost ?? 0).toFixed(2)}</span>
                    <span className="text-purple-400">External: ฿{(hoveredItem.ext_cost ?? 0).toFixed(2)}</span>
                    <span className="text-amber-300 font-bold">รวม: ฿{hoveredItem.total.toFixed(2)}</span>
                  </>
                ) : (
                  <>
                    <span className="text-emerald-400">จริง: {hoveredItem.true_alarm}</span>
                    <span className="text-rose-400">ลวง: {hoveredItem.false_alarm}</span>
                    <span className="text-slate-400">รวม: {hoveredItem.total}</span>
                  </>
                )}
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
                <span>ไม่มีข้อมูลในช่วงเวลานี้</span>
              </div>
            ) : (
              chartItems.map((item) => {
                const heightPct = item.total > 0 ? Math.max((item.total / maxBarTotal) * 100, 6) : 2;
                const seg1Pct = item.total > 0 ? (item.true_alarm / item.total) * 100 : 0;
                const seg2Pct = item.total > 0 ? (item.false_alarm / item.total) * 100 : 0;

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
                      ) : activeTab === "cost" ? (
                        <>
                          {/* GCP Cost segment (cyan) */}
                          <div
                            style={{ height: `${seg1Pct}%` }}
                            className="w-full bg-cyan-500/80 group-hover:bg-cyan-400 transition-colors"
                          />
                          {/* External Cost segment (purple) */}
                          <div
                            style={{ height: `${seg2Pct}%` }}
                            className="w-full bg-purple-500/80 group-hover:bg-purple-400 transition-colors"
                          />
                        </>
                      ) : (
                        <>
                          {/* True Alarm segment (emerald) */}
                          <div
                            style={{ height: `${seg1Pct}%` }}
                            className="w-full bg-emerald-500/80 group-hover:bg-emerald-400 transition-colors"
                          />
                          {/* False Alarm segment (rose) */}
                          <div
                            style={{ height: `${seg2Pct}%` }}
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
              <BahtIcon className="w-5 h-5 text-cyan-400 text-base" />
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
