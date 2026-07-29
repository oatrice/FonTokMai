"use client";

import { useState } from "react";
import { GlassNavbar } from "@/components/GlassNavbar";
import { FinancialDashboard } from "@/components/FinancialDashboard";

export default function Home() {
  const [isDonationModalOpen, setIsDonationModalOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col selection:bg-cyan-500/30 selection:text-cyan-200">
      <GlassNavbar onOpenDonation={() => setIsDonationModalOpen(true)} />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <FinancialDashboard 
          isDonationModalOpen={isDonationModalOpen}
          onOpenDonationModal={() => setIsDonationModalOpen(true)}
          onCloseDonationModal={() => setIsDonationModalOpen(false)}
        />
      </main>
      <footer className="border-t border-white/10 py-6 text-center text-xs text-slate-500 backdrop-blur-md bg-slate-950/40">
        FonMaYang System &copy; 2026. Translucent Glassmorphism Design System.
      </footer>
    </div>
  );
}
