"use client";

import React, { useState } from "react";
import useSWR from "swr";
import { 
  ShieldCheck, 
  Flame, 
  Server, 
  CloudRain,
  Activity, 
  ArrowUpRight, 
  CheckCircle2, 
  AlertTriangle,
  Lock,
  Heart,
  Sparkles,
  RefreshCw
} from "lucide-react";
import { GlassCard } from "./ui/GlassCard";
import { GlassButton } from "./ui/GlassButton";
import { GlassBadge } from "./ui/GlassBadge";
import { Leaderboard } from "./dashboard/Leaderboard";
import { DonationModal } from "./dashboard/DonationModal";
import { TokenRecoveryModal } from "./dashboard/TokenRecoveryModal";

interface FinancialDashboardProps {
  isDonationModalOpen?: boolean;
  onOpenDonationModal?: () => void;
  onCloseDonationModal?: () => void;
}

interface BudgetJar {
  name: string;
  percentage: number;
  allocated_thb: number;
  description: string;
  color?: string;
}

interface RunwayData {
  days_remaining: number;
  hours_remaining: number;
  seconds_remaining: number;
  burn_rate_per_day: number;
  total_balance_thb: number;
  circuit_breaker_active: boolean;
  emergency_overdrive: boolean;
  budget_jars?: BudgetJar[];
  target_exhaustion_time?: number;
  server_time?: number;
}

const fetcher = (url: string) => fetch(url).then((res) => res.json());

const formatThb = (value: number) =>
  value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

const jarIconMap: Record<string, typeof Server> = {
  "Cloud Run Infrastructure": Server,
  "TMD Radar & Weather APIs": CloudRain,
  "Emergency Reserve Jar": ShieldCheck,
};

const jarGradients: Record<string, string> = {
  "Cloud Run Infrastructure": "linear-gradient(to right, #2563eb, #0284c7)",
  "TMD Radar & Weather APIs": "linear-gradient(to right, #0284c7, #0d9488)",
  "Emergency Reserve Jar": "linear-gradient(to right, #059669, #10b981)",
};

const jarGlows: Record<string, string> = {
  "Cloud Run Infrastructure": "rgba(37,99,235,0.4)",
  "TMD Radar & Weather APIs": "rgba(2,132,199,0.4)",
  "Emergency Reserve Jar": "rgba(16,185,129,0.4)",
};

const defaultJars: BudgetJar[] = [
  {
    name: "Cloud Run Infrastructure",
    percentage: 50,
    allocated_thb: 2570,
    color: "from-blue-600 to-sky-600",
    description: "Backend API instances & async workers",
  },
  {
    name: "TMD Radar & Weather APIs",
    percentage: 30,
    allocated_thb: 1542,
    color: "from-sky-600 to-teal-600",
    description: "Radar image processing & storage",
  },
  {
    name: "Emergency Reserve Jar",
    percentage: 20,
    allocated_thb: 1028,
    color: "from-emerald-600 to-teal-500",
    description: "Locked buffer for unexpected spikes",
  },
];

export function FinancialDashboard({
  isDonationModalOpen: externalIsOpen,
  onOpenDonationModal,
  onCloseDonationModal,
}: FinancialDashboardProps = {}) {
  const [invincibleMode, setInvincibleMode] = useState(false);
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const [isRecoveryModalOpen, setRecoveryModalOpen] = useState(false);

  const isModalOpen = externalIsOpen ?? internalIsOpen;
  const handleOpenModal = onOpenDonationModal ?? (() => setInternalIsOpen(true));
  const handleCloseModal = onCloseDonationModal ?? (() => setInternalIsOpen(false));

  const { data, isLoading, mutate } = useSWR<RunwayData>("/api/runway", fetcher, {
    refreshInterval: 15000,
    revalidateOnFocus: true,
  });

  const runwayDays = data?.days_remaining;
  const dailyBurn = data?.burn_rate_per_day;
  const currentBalance = data?.total_balance_thb;
  const circuitBreaker = data?.circuit_breaker_active ?? false;
  const overdrive = invincibleMode || (data?.emergency_overdrive ?? false);
  const budgetJars = data?.budget_jars;

  return (
    <div className="space-y-8 py-6">
      {/* Hero Runway Stats */}
      <section id="overview" className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <GlassCard variant="accent" glowColor="blue" className="p-6">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">Financial Runway</span>
            <GlassBadge variant="blue" dot>
              {isLoading ? "Syncing..." : "Live Math"}
            </GlassBadge>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            {isLoading || runwayDays === undefined ? (
              <div className="h-12 w-28 rounded-lg bg-slate-800/80 animate-pulse my-1" />
            ) : (
              <>
                <span className="text-5xl font-black tracking-tight text-white font-mono tabular-nums">{runwayDays}</span>
                <span className="text-xl font-bold text-sky-400">Days</span>
              </>
            )}
          </div>
          <p className="mt-2 text-xs text-slate-400">
            {isLoading || dailyBurn === undefined ? (
              <span className="inline-block h-3 w-40 rounded bg-slate-800/80 animate-pulse mt-1" />
            ) : (
              <>Operating cost: <span className="text-slate-200 font-semibold font-mono tabular-nums">฿{formatThb(dailyBurn)}/day</span></>
            )}
          </p>
        </GlassCard>

        <GlassCard variant="default" glowColor="emerald" className="p-6">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">Total Reserve Vault</span>
            <GlassBadge variant="emerald">Anonymous Audit</GlassBadge>
          </div>
          <div className="mt-4 flex items-baseline gap-1">
            <span className="text-xl font-semibold text-emerald-400 font-mono">฿</span>
            {isLoading || currentBalance === undefined ? (
              <div className="h-12 w-44 rounded-lg bg-slate-800/80 animate-pulse my-1" />
            ) : (
              <span className="text-5xl font-black tracking-tight text-white font-mono tabular-nums">
                {currentBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            )}
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Community-funded operational runway for Isan Doppler radar
          </p>
        </GlassCard>

        <GlassCard variant="default" glowColor={overdrive ? "amber" : "blue"} className="p-6">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">Resiliency Status</span>
            <GlassBadge variant={overdrive ? "amber" : "emerald"} dot>
              {overdrive ? "Extended Lifespan Active" : "Normal Operation"}
            </GlassBadge>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <div className={`p-3 rounded-2xl border ${overdrive ? 'bg-amber-500/15 text-amber-300 border-amber-500/30' : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'}`}>
              <ShieldCheck className="h-7 w-7" />
            </div>
            <div>
              <div className="text-base sm:text-lg font-bold text-white">
                {circuitBreaker ? "Fallback Weather Cache" : "All Systems Operational"}
              </div>
              <div className="text-xs text-slate-400">
                {circuitBreaker ? "Using cached forecast to preserve quota" : "All radar pipelines and gates nominal"}
              </div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-medium text-slate-300">Extended Lifespan Mode</span>
              <span className="text-[11px] text-slate-400">Throttles background sync to conserve reserves</span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={overdrive}
              aria-label="Toggle Extended Lifespan Mode"
              onClick={() => setInvincibleMode(!invincibleMode)}
              onKeyDown={(e) => {
                if (e.key === " " || e.key === "Enter") {
                  e.preventDefault();
                  setInvincibleMode(!invincibleMode);
                }
              }}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border border-white/15 transition-colors focus:outline-none focus:ring-2 focus:ring-sky-400 focus:ring-offset-2 focus:ring-offset-slate-950 ${
                overdrive ? 'bg-amber-500' : 'bg-slate-800'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-md transition-transform duration-200 ease-in-out ${
                  overdrive ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </GlassCard>
      </section>

      {/* Budget Jars Section */}
      <section id="jars" className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Flame className="h-5 w-5 text-sky-400" />
              Budget Jars Allocation
            </h2>
            <p className="text-xs text-slate-400">Dynamic operational cost distribution across core infrastructure</p>
          </div>
          <GlassButton variant="outline" size="sm" onClick={() => mutate()}>
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Sync Jars</span>
          </GlassButton>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {isLoading || !budgetJars ? (
            <>
              {[1, 2, 3].map((i) => (
                <GlassCard key={i} variant="default" glowColor="blue" className="p-6 space-y-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-slate-800/80 animate-pulse" />
                      <div className="space-y-1">
                        <div className="h-4 w-32 rounded bg-slate-800/80 animate-pulse" />
                        <div className="h-3 w-24 rounded bg-slate-800/80 animate-pulse" />
                      </div>
                    </div>
                    <div className="h-5 w-10 rounded-full bg-slate-800/80 animate-pulse" />
                  </div>
                  <div className="space-y-2 pt-2">
                    <div className="h-4 w-full rounded bg-slate-800/80 animate-pulse" />
                    <div className="h-2.5 w-full rounded-full bg-slate-800/80 animate-pulse" />
                  </div>
                </GlassCard>
              ))}
            </>
          ) : (
            budgetJars.map((jar) => {
              const Icon = jarIconMap[jar.name] || Server;
              const badgeVariant = jar.percentage >= 40 ? "blue" : jar.percentage >= 25 ? "cyan" : "emerald";
              return (
                <GlassCard key={jar.name} variant="default" glowColor="blue" interactive className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 text-sky-400">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-white text-lg">{jar.name}</h3>
                        <span className="text-xs text-slate-400">{jar.description}</span>
                      </div>
                    </div>
                    <GlassBadge variant={badgeVariant} className="font-mono tabular-nums">{jar.percentage}%</GlassBadge>
                  </div>

                  <div className="mt-5 pt-3 border-t border-white/10 flex items-center justify-between text-sm">
                    <span className="text-slate-400 text-xs uppercase tracking-wider">Allocated Share</span>
                    <span className="font-bold text-white text-base font-mono tabular-nums">฿{jar.allocated_thb.toLocaleString()}</span>
                  </div>
                </GlassCard>
              );
            })
          )}
        </div>
      </section>

      {/* Arcade Leaderboard Section */}
      <section id="arcade" className="space-y-4">
        <Leaderboard />
      </section>

      {/* Gamified Milestone & Recovery Callout */}
      <section id="resiliency" className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <GlassCard variant="glow" glowColor="blue" className="p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-sky-400" />
            <h3 className="text-lg font-bold text-white">Community Infrastructure Goal</h3>
          </div>
          <p className="text-sm text-slate-300">
            Next Milestone: <span className="font-semibold text-sky-300">Radar Satellite Refactor (฿105,000)</span>. 
            Once target threshold is reached, additional high-res processing workers are deployed automatically.
          </p>
          <div className="pt-2">
            <GlassButton 
              variant="primary" 
              size="md" 
              className="w-full justify-center"
              onClick={handleOpenModal}
            >
              <Heart className="h-4 w-4" />
              <span>Contribute to Milestone</span>
            </GlassButton>
          </div>
        </GlassCard>

        <GlassCard variant="subtle" className="p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Lock className="h-5 w-5 text-emerald-400" />
            <h3 className="text-lg font-bold text-white">Anonymous Contributor Recovery</h3>
          </div>
          <p className="text-sm text-slate-300">
            Lost your <code className="text-sky-300 bg-sky-950/60 px-1.5 py-0.5 rounded border border-sky-800/50">Fon-XXXX-XXXX</code> access token?
            Use 3-point verification (Transaction Hash, Timestamp, Amount) with zero private data storage.
          </p>
          <div className="pt-2">
            <GlassButton 
              variant="outline" 
              size="md" 
              className="w-full justify-center"
              onClick={() => setRecoveryModalOpen(true)}
            >
              <span>Start Token Recovery</span>
            </GlassButton>
          </div>
        </GlassCard>
      </section>

      <DonationModal 
        isOpen={isModalOpen} 
        onClose={handleCloseModal} 
      />
      
      <TokenRecoveryModal
        isOpen={isRecoveryModalOpen}
        onClose={() => setRecoveryModalOpen(false)}
      />
    </div>
  );
}
