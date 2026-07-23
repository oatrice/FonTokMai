"use client";

import React, { useState } from "react";
import { 
  CloudRain, 
  Wallet, 
  ShieldAlert, 
  Activity, 
  Menu, 
  X, 
  ChevronRight, 
  HeartHandshake,
  BarChart3,
  Cpu
} from "lucide-react";
import Link from "next/link";
import { GlassButton } from "./ui/GlassButton";
import { GlassBadge } from "./ui/GlassBadge";

export function GlassNavbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-xl bg-slate-950/70 border-b border-white/10 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-400 p-0.5 shadow-lg shadow-cyan-500/20">
              <div className="h-full w-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <CloudRain className="h-5 w-5 text-cyan-400" />
              </div>
            </div>
            <div>
              <span className="text-lg font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-cyan-400 bg-clip-text text-transparent">
                FonMaYang
              </span>
              <div className="flex items-center gap-1.5">
                <GlassBadge variant="cyan" dot className="py-0 px-1.5 text-[10px]">
                  LIVE RUNWAY
                </GlassBadge>
              </div>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            <Link href="/dashboard" className="px-3.5 py-2 text-sm font-semibold text-cyan-400 hover:text-cyan-300 rounded-xl hover:bg-cyan-500/10 transition-all flex items-center gap-1.5">
              <Activity className="h-4 w-4" />
              <span>Dashboard</span>
            </Link>
            <a href="#overview" className="px-3.5 py-2 text-sm font-medium text-slate-300 hover:text-white rounded-xl hover:bg-white/5 transition-all">
              Overview
            </a>
            <a href="#jars" className="px-3.5 py-2 text-sm font-medium text-slate-300 hover:text-white rounded-xl hover:bg-white/5 transition-all">
              Budget Jars
            </a>
            <a href="#runway" className="px-3.5 py-2 text-sm font-medium text-slate-300 hover:text-white rounded-xl hover:bg-white/5 transition-all">
              Runway Math
            </a>
            <a href="#resiliency" className="px-3.5 py-2 text-sm font-medium text-slate-300 hover:text-white rounded-xl hover:bg-white/5 transition-all">
              Resiliency & Breaker
            </a>
          </nav>

          {/* Action Buttons */}
          <div className="hidden md:flex items-center gap-3">
            <Link href="/dashboard">
              <GlassButton variant="secondary" size="sm">
                <Activity className="h-4 w-4 text-cyan-400" />
                <span>Live Dashboard</span>
              </GlassButton>
            </Link>
            <GlassButton variant="primary" size="sm">
              <HeartHandshake className="h-4 w-4" />
              <span>Donate</span>
            </GlassButton>
          </div>

          {/* Mobile Menu Toggle */}
          <div className="md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-xl bg-slate-900/60 border border-white/10 text-slate-300 hover:text-white"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu Panel */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-white/10 space-y-2 animate-in fade-in slide-in-from-top-2">
            <a href="#overview" className="block px-4 py-2.5 text-sm font-medium text-slate-200 hover:bg-white/5 rounded-xl">
              Overview
            </a>
            <a href="#jars" className="block px-4 py-2.5 text-sm font-medium text-slate-200 hover:bg-white/5 rounded-xl">
              Budget Jars
            </a>
            <a href="#runway" className="block px-4 py-2.5 text-sm font-medium text-slate-200 hover:bg-white/5 rounded-xl">
              Runway Math
            </a>
            <div className="pt-2 flex flex-col gap-2">
              <GlassButton variant="primary" size="md" className="w-full justify-center">
                <HeartHandshake className="h-4 w-4" />
                <span>Donate & Extend Runway</span>
              </GlassButton>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
