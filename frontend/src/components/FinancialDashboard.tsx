"use client";

import React, { useState } from "react";
import { 
  ShieldCheck, 
  Flame, 
  Server, 
  Code, 
  Zap, 
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

export function FinancialDashboard() {
  const [invincibleMode, setInvincibleMode] = useState(false);

  // Mock data representing financial status and budget jars
  const runwayDays = 142;
  const dailyBurn = 620; // THB/day
  const currentBalance = 92000.00; // THB

  const budgetJars = [
    {
      id: "infra",
      name: "Infrastructure Jar",
      icon: Server,
      current: 43500,
      target: 52500,
      hp: 83,
      status: "Healthy",
      color: "cyan" as const,
    },
    {
      id: "salary",
      name: "Developer Salary Jar",
      icon: Code,
      current: 34300,
      target: 70000,
      hp: 49,
      status: "Warning",
      color: "amber" as const,
    },
    {
      id: "api",
      name: "API & Data Services",
      icon: Zap,
      current: 13900,
      target: 17500,
      hp: 79,
      status: "Healthy",
      color: "emerald" as const,
    },
  ];

  return (
    <div className="space-y-8 py-6">
      {/* Hero Runway Stats */}
      <section id="overview" className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <GlassCard variant="accent" glowColor="blue" className="p-6">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-400">Financial Runway</span>
            <GlassBadge variant="cyan" dot>Live Math</GlassBadge>
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
            <span className="text-5xl font-black tracking-tight text-white">{currentBalance.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
          </div>
          <div className="mt-3 w-full bg-slate-800/80 rounded-full h-2 overflow-hidden border border-white/5">
            <div className="bg-gradient-to-r from-emerald-500 to-cyan-400 h-full rounded-full w-[72%]" />
          </div>
        </GlassCard>

        <GlassCard variant="default" glowColor="purple" className="p-6">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-400">Resiliency Status</span>
            <GlassBadge variant={invincibleMode ? "purple" : "emerald"} dot>
              {invincibleMode ? "OVERDRIVE" : "NORMAL"}
            </GlassBadge>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <div className={`p-3 rounded-2xl ${invincibleMode ? 'bg-purple-500/20 text-purple-300' : 'bg-emerald-500/20 text-emerald-300'}`}>
              <ShieldCheck className="h-7 w-7" />
            </div>
            <div>
              <div className="text-lg font-bold text-white">Circuit Breaker Active</div>
              <div className="text-xs text-slate-400">All financial safety gates nominal</div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between">
            <span className="text-xs text-slate-400">Emergency Invincible Mode</span>
            <button
              onClick={() => setInvincibleMode(!invincibleMode)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${invincibleMode ? 'bg-purple-600' : 'bg-slate-700'}`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${invincibleMode ? 'translate-x-6' : 'translate-x-1'}`} />
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
          <GlassButton variant="outline" size="sm">
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Sync Jars</span>
          </GlassButton>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {budgetJars.map((jar) => {
            const Icon = jar.icon;
            return (
              <GlassCard key={jar.id} variant="default" glowColor={jar.color} interactive className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-slate-800/80 border border-white/10 text-cyan-400">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white text-base">{jar.name}</h3>
                      <span className="text-xs text-slate-400">HP: {jar.hp}%</span>
                    </div>
                  </div>
                  <GlassBadge variant={jar.color}>{jar.status}</GlassBadge>
                </div>

                <div className="mt-6 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Balance</span>
                    <span className="font-bold text-white">฿{jar.current.toLocaleString()} / ฿{jar.target.toLocaleString()}</span>
                  </div>
                  <div className="w-full bg-slate-950/80 rounded-full h-2.5 p-0.5 border border-white/10">
                    <div 
                      className={`h-full rounded-full transition-all duration-500 ${
                        jar.hp < 50 ? 'bg-amber-500' : 'bg-gradient-to-r from-cyan-500 to-blue-500'
                      }`}
                      style={{ width: `${(jar.current / jar.target) * 100}%` }}
                    />
                  </div>
                </div>
              </GlassCard>
            );
          })}
        </div>
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
            <GlassButton variant="primary" size="md" className="w-full justify-center">
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
    </div>
  );
}
