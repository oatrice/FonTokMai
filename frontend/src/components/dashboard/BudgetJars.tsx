"use client";

import React from "react";
import useSWR from "swr";
import { GlassCard } from "@/components/ui/GlassCard";
import { GlassBadge } from "@/components/ui/GlassBadge";
import { Server, CloudRain, ShieldCheck } from "lucide-react";

interface BudgetJar {
  name: string;
  percentage: number;
  allocated_thb: number;
  description: string;
  color?: string;
}

interface RunwayData {
  budget_jars?: BudgetJar[];
}

const fetcher = (url: string) => fetch(url).then((res) => res.json());

const jarIconMap: Record<string, typeof Server> = {
  "Cloud Run Infrastructure": Server,
  "TMD Radar & Weather APIs": CloudRain,
  "Emergency Reserve Jar": ShieldCheck,
};

const defaultJars: BudgetJar[] = [
  {
    name: "Cloud Run Infrastructure",
    percentage: 50,
    allocated_thb: 2570,
    color: "from-blue-500 to-cyan-500",
    description: "Backend API instances & async workers",
  },
  {
    name: "TMD Radar & Weather APIs",
    percentage: 30,
    allocated_thb: 1542,
    color: "from-purple-500 to-indigo-500",
    description: "Radar image processing & storage",
  },
  {
    name: "Emergency Reserve Jar",
    percentage: 20,
    allocated_thb: 1028,
    color: "from-emerald-500 to-teal-500",
    description: "Locked buffer for unexpected spikes",
  },
];

export function BudgetJars() {
  const { data } = useSWR<RunwayData>("/api/runway", fetcher, {
    refreshInterval: 15000,
    revalidateOnFocus: true,
  });

  const jars = data?.budget_jars || defaultJars;

  return (
    <GlassCard className="p-6 md:p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight">Transparent Budget Jars</h3>
          <p className="text-xs text-zinc-400">Strict automated fund allocation algorithm</p>
        </div>
        <GlassBadge variant="cyan">{jars.length} Jars Active</GlassBadge>
      </div>

      <div className="space-y-5">
        {jars.map((jar) => {
          const Icon = jarIconMap[jar.name] || Server;
          const colorClass = jar.color || "from-cyan-500 to-blue-500";
          return (
            <div key={jar.name} className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-white/5 border border-white/10 text-cyan-400">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-semibold text-white block">{jar.name}</span>
                    <span className="text-xs text-zinc-400">{jar.description}</span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="font-bold text-white block">฿{jar.allocated_thb.toLocaleString()}</span>
                  <span className="text-xs text-zinc-400">{jar.percentage}%</span>
                </div>
              </div>

              {/* Custom Progress Bar */}
              <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden p-0.5 border border-white/5">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${colorClass} transition-all duration-500`}
                  style={{ width: `${jar.percentage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}
