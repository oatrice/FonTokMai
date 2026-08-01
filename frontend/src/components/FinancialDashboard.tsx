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

export function FinancialDashboard({
  isDonationModalOpen: externalIsOpen,
  onOpenDonationModal,
  onCloseDonationModal,
}: FinancialDashboardProps = {}) {
  const [invincibleMode, setInvincibleMode] = useState(false);
  const [internalIsOpen, setInternalIsOpen] = useState(false);

  const isModalOpen = externalIsOpen ?? internalIsOpen;
  const handleOpenModal = onOpenDonationModal ?? (() => setInternalIsOpen(true));
  const handleCloseModal = onCloseDonationModal ?? (() => setInternalIsOpen(false));

  const { data, isLoading, mutate } = useSWR<RunwayData>("/api/runway", fetcher, {
    refreshInterval: 15000,
    revalidateOnFocus: true,
  });

  const runwayDays = data?.days_remaining ?? 42;
  const dailyBurn = data?.burn_rate_per_day ?? 120;
  const currentBalance = data?.total_balance_thb ?? 5140;
  const circuitBreaker = data?.circuit_breaker_active ?? false;
  const overdrive = invincibleMode || (data?.emergency_overdrive ?? false);
  const budgetJars = data?.budget_jars || defaultJars;

  return (
    <div className="space-y-8 py-6">
      {/* Hero Runway Stats */}
      <section id="overview" className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <GlassCard variant="accent" glowColor="blue" className="p-6">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-400">Financial Runway</span>
            <GlassBadge variant="cyan" dot>
              {isLoading ? "Syncing..." : "Live Math"}
            </GlassBadge>
          </div>
          <div className="mt-4 flex items-baseline gap-3">
            <span className="text-5xl font-black tracking-tight text-white">{runwayDays}</span>
            <span className="text-xl font-bold text-cyan-400">Days</span>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Based on active GCP/AWS burn rate of <span className="text-slate-200 font-semibold">฿{dailyBurn}/day</span>
          </p>
        </GlassCard>

        <GlassCard variant="default" glowColor="emerald" className="p-6">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-400">Total Reserve Vault</span>
            <GlassBadge variant="emerald">Zero-PII Tracked</GlassBadge>
          </div>
          <div className="mt-4 flex items-baseline gap-1">
            <span className="text-xl font-semibold text-emerald-400">฿</span>
            <span className="text-5xl font-black tracking-tight text-white">
              {currentBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <div className="mt-3 w-full bg-slate-800/80 rounded-full h-2 overflow-hidden border border-white/5">
            <div className="bg-gradient-to-r from-emerald-500 to-cyan-400 h-full rounded-full w-[72%]" />
          </div>
        </GlassCard>

        <GlassCard variant="default" glowColor="purple" className="p-6">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-400">Resiliency Status</span>
            <GlassBadge variant={overdrive ? "purple" : "emerald"} dot>
              {overdrive ? "OVERDRIVE" : "NORMAL"}
            </GlassBadge>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <div className={`p-3 rounded-2xl ${overdrive ? 'bg-purple-500/20 text-purple-300' : 'bg-emerald-500/20 text-emerald-300'}`}>
              <ShieldCheck className="h-7 w-7" />
            </div>
            <div>
              <div className="text-lg font-bold text-white">
                {circuitBreaker ? "Circuit Breaker Active" : "All Systems Operational"}
              </div>
              <div className="text-xs text-slate-400">All financial safety gates nominal</div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between">
            <span className="text-xs text-slate-400">Emergency Invincible Mode</span>
            <button
              onClick={() => setInvincibleMode(!invincibleMode)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${overdrive ? 'bg-purple-600' : 'bg-slate-700'}`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${overdrive ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>
        </GlassCard>
      </section>

      {/* Budget Jars Section */}
      <section id="jars" className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Flame className="h-5 w-5 text-amber-400" />
              Budget Jars State Machine
            </h2>
            <p className="text-xs text-slate-400">Real-time HP decay and split strategy allocation</p>
          </div>
          <GlassButton variant="outline" size="sm" onClick={() => mutate()}>
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Sync Jars</span>
          </GlassButton>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {budgetJars.map((jar) => {
            const Icon = jarIconMap[jar.name] || Server;
            const badgeVariant = jar.percentage >= 40 ? "cyan" : jar.percentage >= 25 ? "purple" : "emerald";
            return (
              <GlassCard key={jar.name} variant="default" glowColor="cyan" interactive className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-slate-800/80 border border-white/10 text-cyan-400">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white text-base">{jar.name}</h3>
                      <span className="text-xs text-slate-400">{jar.description}</span>
                    </div>
                  </div>
                  <GlassBadge variant={badgeVariant}>{jar.percentage}%</GlassBadge>
                </div>

                <div className="mt-6 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Allocated Balance</span>
                    <span className="font-bold text-white">฿{jar.allocated_thb.toLocaleString()}</span>
                  </div>
                  <div className="w-full bg-slate-950/80 rounded-full h-2.5 p-0.5 border border-white/10">
                    <div 
                      className={`h-full rounded-full transition-all duration-500 bg-gradient-to-r ${
                        jar.color || 'from-cyan-500 to-blue-500'
                      }`}
                      style={{ width: `${jar.percentage}%` }}
                    />
                  </div>
                </div>
              </GlassCard>
            );
          })}
        </div>
      </section>

      {/* Arcade Leaderboard Section */}
      <section id="arcade" className="space-y-4">
        <Leaderboard />
      </section>

      {/* Gamified Milestone & Recovery Callout */}
      <section id="resiliency" className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <GlassCard variant="glow" glowColor="cyan" className="p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-cyan-400" />
            <h3 className="text-lg font-bold text-white">Gamified Milestone Lock</h3>
          </div>
          <p className="text-sm text-slate-300">
            Next Milestone: <span className="font-semibold text-cyan-300">Radar Satellite Refactor (฿105,000)</span>. 
            Once target HP is unlocked, additional high-res processing workers are deployed automatically.
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
            <h3 className="text-lg font-bold text-white">Zero-PII Donor Recovery</h3>
          </div>
          <p className="text-sm text-slate-300">
            Lost your <code className="text-cyan-300 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800/50">Fon-XXXX-XXXX</code> access token?
            Use 3-point recovery (Transaction Hash, Timestamp, Amount) with 0 private data leakage.
          </p>
          <div className="pt-2">
            <GlassButton variant="outline" size="md" className="w-full justify-center">
              <span>Start Token Recovery</span>
            </GlassButton>
          </div>
        </GlassCard>
      </section>

      <DonationModal 
        isOpen={isModalOpen} 
        onClose={handleCloseModal} 
      />
    </div>
  );
}

