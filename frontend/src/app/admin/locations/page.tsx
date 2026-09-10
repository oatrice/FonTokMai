"use client";

import { useState } from "react";
import useSWR from "swr";
import { GlassNavbar } from "@/components/GlassNavbar";
import { MapPin, Bell, Clock, ShieldAlert, Moon } from "lucide-react";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

interface LocationItem {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  presence_policy: string;
  presence_answer_ttl_minutes: number;
  is_snoozed: boolean;
  snooze_until?: string | null;
}

export default function AdminLocationsPage() {
  const { data: locations, mutate } = useSWR<LocationItem[]>("/api/locations", fetcher);
  const [selectedLoc, setSelectedLoc] = useState<LocationItem | null>(null);

  return (
    <div className="min-h-screen flex flex-col selection:bg-cyan-500/30 selection:text-cyan-200">
      <GlassNavbar onOpenDonation={() => {}} />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Header */}
        <div className="p-6 rounded-2xl bg-slate-900/60 backdrop-blur-xl border border-white/10 shadow-2xl">
          <h1 className="text-2xl font-bold text-white tracking-wide flex items-center gap-3">
            📍 Location Presence Policy & Schedule Settings
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            กำหนดโหมดการแจ้งเตือนเตือนทันที/ถามก่อน, ตารางเวลาที่ผู้ใช้อยู่ประจำ และตั้งค่าเวลาจำคำตอบ (TTL Countdown)
          </p>
        </div>

        {/* Locations Table */}
        <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-xl border border-white/10 overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="text-xs uppercase bg-slate-800/60 text-slate-400">
              <tr>
                <th className="px-4 py-3">Location Name</th>
                <th className="px-4 py-3">Coordinates</th>
                <th className="px-4 py-3">Presence Policy</th>
                <th className="px-4 py-3">Countdown TTL</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {locations && locations.length > 0 ? (
                locations.map((loc) => (
                  <tr key={loc.id} className="hover:bg-slate-800/30 transition">
                    <td className="px-4 py-4 font-semibold text-white flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-cyan-400" />
                      {loc.name}
                    </td>
                    <td className="px-4 py-4 text-slate-400">
                      {loc.latitude.toFixed(4)}, {loc.longitude.toFixed(4)}
                    </td>
                    <td className="px-4 py-4">
                      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">
                        {loc.presence_policy || "always_ask"}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-slate-300">
                      {loc.presence_answer_ttl_minutes || 120} นาที
                    </td>
                    <td className="px-4 py-4">
                      {loc.is_snoozed ? (
                        <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-amber-950/60 text-amber-300 border border-amber-500/30">
                          🔕 Snoozed
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
                          🟢 Active
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-slate-500">
                    ยังไม่มีพิกัดที่บันทึกไว้ในระบบ
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

      </main>
    </div>
  );
}
