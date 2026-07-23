"use client";

import React, { useEffect, useState, useRef } from "react";
import useSWR from "swr";
import { GlassCard } from "@/components/ui/GlassCard";
import { GlassBadge } from "@/components/ui/GlassBadge";
import { Clock, Zap } from "lucide-react";

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

export function RunwayCounter() {
  const { data, error, isLoading } = useSWR<RunwayData>("/api/runway", fetcher, {
    refreshInterval: 15000,
    revalidateOnFocus: true,
  });

  // Fallback initial state
  const fallbackData: RunwayData = {
    days_remaining: 42,
    hours_remaining: 18,
    seconds_remaining: 3693600,
    burn_rate_per_day: 120,
    total_balance_thb: 5140,
    circuit_breaker_active: false,
    emergency_overdrive: false,
  };

  const runway = data || fallbackData;
  const targetEndTimeRef = useRef<number | null>(null);
  const [secondsRemaining, setSecondsRemaining] = useState<number>(runway.seconds_remaining);

  // When new SWR data arrives, update the target end timestamp
  useEffect(() => {
    if (data?.seconds_remaining !== undefined) {
      targetEndTimeRef.current = Date.now() + data.seconds_remaining * 1000;
      setSecondsRemaining(data.seconds_remaining);
    } else if (targetEndTimeRef.current === null) {
      targetEndTimeRef.current = Date.now() + fallbackData.seconds_remaining * 1000;
    }
  }, [data]);

  // Smooth countdown ticker (1s interval) using target end time for zero drift
  useEffect(() => {
    const timer = setInterval(() => {
      if (targetEndTimeRef.current !== null) {
        const diffInSeconds = Math.max(0, Math.floor((targetEndTimeRef.current - Date.now()) / 1000));
        setSecondsRemaining(diffInSeconds);
      } else {
        setSecondsRemaining((prev) => Math.max(0, prev - 1));
      }
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const days = Math.floor(secondsRemaining / (3600 * 24));
  const hours = Math.floor((secondsRemaining % (3600 * 24)) / 3600);
  const minutes = Math.floor((secondsRemaining % 3600) / 60);
  const seconds = secondsRemaining % 60;

  return (
    <GlassCard glow className="p-6 md:p-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-bold text-white tracking-tight">Live Runway Engine</h2>
            <GlassBadge variant={runway.emergency_overdrive ? "danger" : "cyan"}>
              {runway.emergency_overdrive ? "OVERDRIVE MODE" : "HEALTHY"}
            </GlassBadge>
            {runway.circuit_breaker_active && (
              <GlassBadge variant="danger">
                CIRCUIT BREAKER ACTIVE
              </GlassBadge>
            )}
            {isLoading && <span className="text-xs text-cyan-400 animate-pulse font-mono">Syncing...</span>}
          </div>
          <p className="text-sm text-zinc-400">
            Real-time server lifespan based on current donation balance & API consumption.
          </p>
        </div>
        <div className="text-right">
          <span className="text-xs text-zinc-500 block">Total Balance</span>
          <span className="text-2xl font-extrabold text-cyan-400">
            ฿{runway.total_balance_thb.toLocaleString()} THB
          </span>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3 md:gap-4 my-6 text-center">
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
      </div>

      <div className="flex items-center justify-between text-xs text-zinc-400 pt-4 border-t border-white/10">
        <div className="flex items-center gap-1.5">
          <Zap className="w-4 h-4 text-amber-400" />
          <span>Burn Rate: <strong className="text-zinc-200">฿{runway.burn_rate_per_day}/day</strong></span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="w-4 h-4 text-cyan-400" />
          <span>SWR Smart Polling: 15s</span>
        </div>
      </div>
    </GlassCard>
  );
}
