"use client";

import React, { useState } from "react";
import { 
  CloudRain, 
  Wallet, 
  ShieldAlert, 
  Activity, 
  Menu, 
  X, 
  HeartHandshake,
  BarChart3,
  Radio,
  MapPin,
  Compass,
  Flame
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { GlassButton } from "./ui/GlassButton";
import { GlassBadge } from "./ui/GlassBadge";

interface GlassNavbarProps {
  onOpenDonation?: () => void;
}

export function GlassNavbar({ onOpenDonation }: GlassNavbarProps = {}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const isDashboardActive = pathname === "/dashboard";
  const isRadarActive = pathname === "/admin/radar";
  const isLocationsActive = pathname === "/admin/locations";
  const isMetricsActive = pathname === "/admin/metrics";

  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-md transform-gpu bg-slate-950/70 border-b border-white/10 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-400 p-0.5 shadow-lg shadow-cyan-500/20 group-hover:scale-105 transition-transform">
              <div className="h-full w-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <CloudRain className="h-5 w-5 text-cyan-400" />
              </div>
            </div>
            <div>
              <span className="text-lg font-extrabold tracking-tight text-white ">
                FonMaYang
              </span>
              <div className="flex items-center gap-1.5">
                <GlassBadge variant="cyan" dot className="py-0 px-1.5 text-[10px]">
                  LIVE RUNWAY
                </GlassBadge>
              </div>
            </div>
          </Link>


          <nav className="hidden md:flex items-center gap-2" aria-label="Main Navigation">
            {/* Primary Surfaces Group */}
            <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-900/50 border border-white/5">
              <Link 
                href="/dashboard" 
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
                  isDashboardActive 
                    ? "text-sky-300 bg-sky-500/20 border border-sky-500/30 shadow-sm" 
                    : "text-slate-300 hover:text-white hover:bg-white/5"
                }`}
              >
                <Activity className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Dashboard</span>
              </Link>
              <Link 
                href="/admin/radar" 
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
                  isRadarActive
                    ? "text-sky-300 bg-sky-500/20 border border-sky-500/30 shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-white/5"
                }`}
              >
                <Radio className={`h-3.5 w-3.5 ${isRadarActive ? "text-sky-400" : "text-slate-400"}`} aria-hidden="true" />
                <span>Radar</span>
              </Link>
              <Link 
                href="/admin/locations" 
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
                  isLocationsActive
                    ? "text-sky-300 bg-sky-500/20 border border-sky-500/30 shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-white/5"
                }`}
              >
                <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Locations</span>
              </Link>
              <Link 
                href="/admin/metrics" 
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
                  isMetricsActive
                    ? "text-sky-300 bg-sky-500/20 border border-sky-500/30 shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-white/5"
                }`}
              >
                <BarChart3 className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Metrics</span>
              </Link>
            </div>

            {/* Quick Section Anchors Group */}
            <div className="flex items-center gap-0.5 px-1 py-1 rounded-xl bg-slate-900/30 border border-white/5">
              <Link href="/#overview" className="px-2.5 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 rounded-lg hover:bg-white/5 transition-all flex items-center gap-1">
                <Compass className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
                <span>Overview</span>
              </Link>
              <Link href="/#jars" className="px-2.5 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 rounded-lg hover:bg-white/5 transition-all flex items-center gap-1">
                <Wallet className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
                <span>Jars</span>
              </Link>
              <Link href="/#runway" className="px-2.5 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 rounded-lg hover:bg-white/5 transition-all flex items-center gap-1">
                <Flame className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
                <span>Runway</span>
              </Link>
              <Link href="/#resiliency" className="px-2.5 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 rounded-lg hover:bg-white/5 transition-all flex items-center gap-1">
                <ShieldAlert className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
                <span>Resiliency</span>
              </Link>
            </div>
          </nav>


          {/* Action Buttons */}
          <div className="hidden md:flex items-center gap-3">
            <GlassButton variant="primary" size="sm" onClick={onOpenDonation}>
              <HeartHandshake className="h-4 w-4" aria-hidden="true" />
              <span>Donate</span>
            </GlassButton>
          </div>

          {/* Mobile Menu Toggle */}
          <div className="md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              className="p-2 rounded-xl bg-slate-900/60 border border-white/10 text-slate-300 hover:text-white"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" aria-hidden="true" /> : <Menu className="h-6 w-6" aria-hidden="true" />}
            </button>
          </div>
        </div>


        {/* Mobile Menu Panel */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-white/10 space-y-2 animate-in fade-in slide-in-from-top-2">
            <Link 
              href="/dashboard"
              onClick={() => setMobileMenuOpen(false)}
              className={`flex items-center gap-2.5 px-4 py-2.5 text-sm font-semibold rounded-xl ${
                isDashboardActive ? "text-cyan-400 bg-cyan-500/10 border border-cyan-500/20" : "text-slate-200 hover:bg-white/5"
              }`}
            >
              <Activity className="h-4 w-4" aria-hidden="true" />
              <span>System Dashboard</span>
            </Link>
            <Link 
              href="/admin/radar"
              onClick={() => setMobileMenuOpen(false)}
              className={`flex items-center gap-2.5 px-4 py-2.5 text-sm font-semibold rounded-xl ${
                isRadarActive ? "text-cyan-400 bg-cyan-500/10 border border-cyan-500/20" : "text-slate-200 hover:bg-white/5"
              }`}
            >
              <Radio className="h-4 w-4" aria-hidden="true" />
              <span>Radar Coverage Map</span>
            </Link>
            <Link 
              href="/admin/locations"
              onClick={() => setMobileMenuOpen(false)}
              className={`flex items-center gap-2.5 px-4 py-2.5 text-sm font-semibold rounded-xl ${
                isLocationsActive ? "text-cyan-400 bg-cyan-500/10 border border-cyan-500/20" : "text-slate-200 hover:bg-white/5"
              }`}
            >
              <MapPin className="h-4 w-4" aria-hidden="true" />
              <span>Locations Admin</span>
            </Link>
            <Link 
              href="/admin/metrics"
              onClick={() => setMobileMenuOpen(false)}
              className={`flex items-center gap-2.5 px-4 py-2.5 text-sm font-semibold rounded-xl ${
                isMetricsActive ? "text-cyan-400 bg-cyan-500/10 border border-cyan-500/20" : "text-slate-200 hover:bg-white/5"
              }`}
            >
              <BarChart3 className="h-4 w-4" aria-hidden="true" />
              <span>Metrics Admin</span>
            </Link>
            <div className="border-t border-white/5 my-1" />
            <Link href="/#overview" onClick={() => setMobileMenuOpen(false)} className="flex items-center gap-2.5 px-4 py-2.5 text-sm font-medium text-slate-200 hover:bg-white/5 rounded-xl">
              <Compass className="h-4 w-4" aria-hidden="true" />
              <span>Overview</span>
            </Link>
            <Link href="/#jars" onClick={() => setMobileMenuOpen(false)} className="flex items-center gap-2.5 px-4 py-2.5 text-sm font-medium text-slate-200 hover:bg-white/5 rounded-xl">
              <Wallet className="h-4 w-4" aria-hidden="true" />
              <span>Jars</span>
            </Link>
            <Link href="/#runway" onClick={() => setMobileMenuOpen(false)} className="flex items-center gap-2.5 px-4 py-2.5 text-sm font-medium text-slate-200 hover:bg-white/5 rounded-xl">
              <Flame className="h-4 w-4" aria-hidden="true" />
              <span>Runway</span>
            </Link>
            <Link href="/#resiliency" onClick={() => setMobileMenuOpen(false)} className="flex items-center gap-2.5 px-4 py-2.5 text-sm font-medium text-slate-200 hover:bg-white/5 rounded-xl">
              <ShieldAlert className="h-4 w-4" aria-hidden="true" />
              <span>Resiliency</span>
            </Link>
            <div className="pt-2 flex flex-col gap-2">
              <GlassButton variant="primary" size="md" className="w-full justify-center" onClick={() => { setMobileMenuOpen(false); onOpenDonation?.(); }}>
                <HeartHandshake className="h-4 w-4" aria-hidden="true" />
                <span>Donate & Extend Runway</span>
              </GlassButton>
            </div>
          </div>
        )}

      </div>
    </header>
  );
}
