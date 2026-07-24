import React from "react";
import { Header } from "@/components/ui/Header";
import { RunwayCounter } from "@/components/dashboard/RunwayCounter";
import { BudgetJars } from "@/components/dashboard/BudgetJars";
import { MilestonesSection } from "@/components/dashboard/MilestonesSection";
import { GCPCostBreakdown } from "@/components/dashboard/GCPCostBreakdown";

export const metadata = {
  title: "Dashboard - FonMaYang Runway Engine",
  description: "Live Server Runway Counter, Transparent Budget Jars, GCP Infrastructure Costs, and Milestone Progress for FonMaYang.",
};

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-black text-zinc-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-12 space-y-8">
        {/* Top Hero Heading */}
        <div className="space-y-2">
          <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white">
            System Dashboard
          </h1>
          <p className="text-zinc-400 text-sm md:text-base max-w-2xl">
            Real-time financial transparency, server runway engine countdown, and infrastructure cost transparency.
          </p>
        </div>

        {/* Runway Counter Full Width */}
        <RunwayCounter />

        {/* 3-Column / Grid Layout for Financial & Infrastructure Stats */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <BudgetJars />
          <GCPCostBreakdown />
        </div>

        {/* Milestones Progress */}
        <MilestonesSection />
      </main>

      <footer className="border-t border-white/10 py-6 text-center text-xs text-zinc-600">
        FonMaYang Transparent Open Financial Engine © 2026. Built with Next.js 14 & Dark Glassmorphism.
      </footer>
    </div>
  );
}
