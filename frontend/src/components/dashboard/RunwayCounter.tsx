"use client";

import React, { useEffect, useState, useRef } from "react";
import useSWR from "swr";
import { GlassCard } from "@/components/ui/GlassCard";
import { GlassBadge } from "@/components/ui/GlassBadge";
import { Clock, Zap, Hash, AlignLeft, Minimize2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface BudgetJarData {
  name: string;
  percentage: number;
  allocated_thb: number;
  description: string;
}

interface RunwayData {
  days_remaining: number;
  hours_remaining: number;
  seconds_remaining: number;
  burn_rate_per_day: number;
  total_balance_thb: number;
  circuit_breaker_active: boolean;
  emergency_overdrive: boolean;
  budget_jars?: BudgetJarData[];
}

const fetcher = (url: string) => fetch(url).then((res) => res.json());

type ViewMode = "numeric" | "storytelling" | "compact";

const formatThb = (value: number) =>
  value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

export function RunwayCounter() {
  const { data, error, isLoading } = useSWR<RunwayData>("/api/runway", fetcher, {
    refreshInterval: 15000,
    revalidateOnFocus: true,
  });

  const runway = data;
  const targetEndTimeRef = useRef<number | null>(null);
  const [secondsRemaining, setSecondsRemaining] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("numeric");
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    const saved = localStorage.getItem("runwayViewMode") as ViewMode;
    if (saved === "numeric" || saved === "storytelling" || saved === "compact") {
      setViewMode(saved);
    }
  }, []);

  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    localStorage.setItem("runwayViewMode", mode);
  };

  useEffect(() => {
    if (data?.seconds_remaining !== undefined) {
      targetEndTimeRef.current = Date.now() + data.seconds_remaining * 1000;
    }
  }, [data]);

  useEffect(() => {
    const timer = setInterval(() => {
      if (targetEndTimeRef.current !== null) {
        const diffInSeconds = Math.max(0, Math.floor((targetEndTimeRef.current - Date.now()) / 1000));
        setSecondsRemaining(diffInSeconds);
      }
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const days = secondsRemaining !== null ? Math.floor(secondsRemaining / (3600 * 24)) : null;
  const hours = secondsRemaining !== null ? Math.floor((secondsRemaining % (3600 * 24)) / 3600) : null;
  const minutes = secondsRemaining !== null ? Math.floor((secondsRemaining % 3600) / 60) : null;
  const seconds = secondsRemaining !== null ? secondsRemaining % 60 : null;

  const renderContent = () => {
    if (days === null || hours === null || minutes === null || seconds === null) {
      return (
        <div className="h-32 w-full rounded-xl bg-slate-800/80 animate-pulse my-6" />
      );
    }

    const effectiveViewMode = isClient ? viewMode : "numeric";

    if (effectiveViewMode === "numeric") {
      return (
        <motion.div
          key="numeric"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="grid grid-cols-4 gap-3 md:gap-4 my-6 text-center"
        >
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 md:p-4 backdrop-blur-md">
            <span className="text-3xl md:text-5xl font-black text-white font-mono">{days}</span>
            <span className="text-xs text-zinc-400 block mt-1 uppercase font-semibold">Days</span>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 md:p-4 backdrop-blur-md">
            <span className="text-3xl md:text-5xl font-black text-white font-mono">
              {String(hours).padStart(2, "0")}
            </span>
            <span className="text-xs text-zinc-400 block mt-1 uppercase font-semibold">Hours</span>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 md:p-4 backdrop-blur-md">
            <span className="text-3xl md:text-5xl font-black text-white font-mono">
              {String(minutes).padStart(2, "0")}
            </span>
            <span className="text-xs text-zinc-400 block mt-1 uppercase font-semibold">Mins</span>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 md:p-4 backdrop-blur-md">
            <span className="text-3xl md:text-5xl font-black text-cyan-400 font-mono animate-pulse">
              {String(seconds).padStart(2, "0")}
            </span>
            <span className="text-xs text-zinc-400 block mt-1 uppercase font-semibold">Secs</span>
          </div>
        </motion.div>
      );
    }

    if (effectiveViewMode === "storytelling") {
      return (
        <motion.div
          key="storytelling"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="bg-white/5 border border-white/10 rounded-xl p-6 md:p-8 backdrop-blur-md my-6"
        >
          <p className="text-lg md:text-xl text-zinc-300 leading-relaxed font-medium">
            Based on current reserves, our systems can remain fully operational for{" "}
            <span className="text-white font-bold">{days} days</span>,{" "}
            <span className="text-white font-bold">{hours} hours</span>, and{" "}
            <span className="text-white font-bold">{minutes} minutes</span>. 
            At a burn rate of <span className="text-cyan-400">฿{runway ? formatThb(runway.burn_rate_per_day) : "0.00"}/day</span>, 
            the final shutdown will occur in exactly{" "}
            <span className="font-mono text-cyan-400 font-bold">{String(seconds).padStart(2, '0')}</span> seconds.
          </p>
        </motion.div>
      );
    }

    if (effectiveViewMode === "compact") {
      return (
        <motion.div
          key="compact"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="flex justify-center my-6"
        >
          <div className="bg-white/5 border border-white/10 rounded-full px-6 py-4 md:px-8 backdrop-blur-md flex items-center gap-4">
            <Clock className="h-6 w-6 text-cyan-400 animate-pulse hidden md:block" />
            <span className="text-3xl md:text-4xl font-black text-white font-mono tracking-wider">
              {days}d {String(hours).padStart(2, "0")}h {String(minutes).padStart(2, "0")}m <span className="text-cyan-400">{String(seconds).padStart(2, "0")}s</span>
            </span>
          </div>
        </motion.div>
      );
    }
  };

  return (
    <GlassCard glow className="p-6 md:p-8">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <h2 className="text-xl font-bold text-white tracking-tight">Live Runway Engine</h2>
            {runway && (
              <GlassBadge variant={runway.emergency_overdrive ? "danger" : "cyan"}>
                {runway.emergency_overdrive ? "Extended Lifespan Mode / โหมดต่ออายุระบบฉุกเฉิน" : "HEALTHY"}
              </GlassBadge>
            )}
            {runway?.circuit_breaker_active && (
              <GlassBadge variant="danger">
                Cached Weather Data Mode / ใช้ข้อมูลพยากรณ์สำรอง
              </GlassBadge>
            )}
            {isLoading && <span className="text-xs text-cyan-400 animate-pulse font-mono">Syncing...</span>}
          </div>
          <p className="text-sm text-zinc-400 max-w-lg">
            Real-time server lifespan based on current donation balance & API consumption.
          </p>
        </div>
        <div className="flex flex-col md:items-end gap-3">
          <div className="text-left md:text-right">
            <span className="text-xs text-zinc-500 block mb-1">Total Balance</span>
            {isLoading || !runway ? (
              <div className="h-8 w-36 rounded-lg bg-slate-800/80 animate-pulse md:ml-auto" />
            ) : (
              <span className="text-2xl font-extrabold text-cyan-400">
                ฿{runway.total_balance_thb.toLocaleString()} THB
              </span>
            )}
          </div>
          
          {isClient && (
            <div className="flex items-center bg-slate-900/50 rounded-lg p-1 border border-white/5 w-fit">
              <button
                onClick={() => handleViewModeChange("numeric")}
                className={`p-1.5 rounded-md transition-colors ${viewMode === "numeric" ? "bg-cyan-500/20 text-cyan-400" : "text-zinc-500 hover:text-zinc-300"}`}
                title="Numeric View"
              >
                <Hash className="h-4 w-4" />
              </button>
              <button
                onClick={() => handleViewModeChange("storytelling")}
                className={`p-1.5 rounded-md transition-colors ${viewMode === "storytelling" ? "bg-cyan-500/20 text-cyan-400" : "text-zinc-500 hover:text-zinc-300"}`}
                title="Storytelling View"
              >
                <AlignLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => handleViewModeChange("compact")}
                className={`p-1.5 rounded-md transition-colors ${viewMode === "compact" ? "bg-cyan-500/20 text-cyan-400" : "text-zinc-500 hover:text-zinc-300"}`}
                title="Compact View"
              >
                <Minimize2 className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>

      <AnimatePresence mode="wait">
        {renderContent()}
      </AnimatePresence>

      <div className="flex items-center justify-between text-xs text-zinc-400 pt-4 border-t border-white/10">
        <div className="flex items-center gap-1.5">
          <Zap className="w-4 h-4 text-amber-400" />
          <span>Burn Rate: <strong className="text-zinc-200">{runway ? `฿${formatThb(runway.burn_rate_per_day)}/day` : "Syncing..."}</strong></span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="w-4 h-4 text-cyan-400" />
          <span>SWR Smart Polling: 15s</span>
        </div>
      </div>
    </GlassCard>
  );
}
