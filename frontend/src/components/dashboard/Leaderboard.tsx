"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import { useEventStream } from "../../hooks/useEventStream";
import { Trophy, Flame, Minus } from "lucide-react";
import { GlassCard } from "../ui/GlassCard";

export function Leaderboard() {
  const { leaderboardData, connectionState } = useEventStream();

  return (
    <GlassCard variant="glow" glowColor="purple" className="p-6 relative overflow-hidden h-full">
      {/* Retro Arcade Grid Background Overlay */}
      <div className="absolute inset-0 opacity-10 pointer-events-none" style={{
        backgroundImage: "linear-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px)",
        backgroundSize: "20px 20px"
      }}></div>

      <div className="flex items-center justify-between mb-6 relative z-10">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-purple-500/20 text-purple-300 border border-purple-500/30 shadow-[0_0_15px_rgba(168,85,247,0.4)]">
            <Trophy className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-widest uppercase" style={{ textShadow: "0 0 10px rgba(168,85,247,0.8)" }}>
              Top Operators
            </h2>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-purple-300">Live Arcade Standings</span>
              <div className="flex items-center gap-1.5">
                <span className="relative flex h-2 w-2">
                  {connectionState === "connected" && (
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  )}
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${connectionState === "connected" ? "bg-emerald-500" : connectionState === "connecting" ? "bg-amber-500" : "bg-red-500"}`}></span>
                </span>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider">{connectionState}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-3 relative z-10">
        {leaderboardData.length === 0 && connectionState === "connected" && (
          <div className="text-center py-8 text-slate-400 text-sm animate-pulse">Awaiting challengers...</div>
        )}
        <AnimatePresence>
          {leaderboardData.map((player, index) => (
            <motion.div
              key={player.token}
              layout
              initial={{ opacity: 0, x: -20, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 20, scale: 0.95 }}
              transition={{ duration: 0.3, type: "spring", bounce: 0.4 }}
              className={`flex items-center justify-between p-3 rounded-xl border backdrop-blur-md transition-all hover:bg-white/10 group ${
                index === 0 
                  ? "bg-gradient-to-r from-amber-500/10 to-transparent border-amber-500/30 shadow-[inset_0_0_20px_rgba(245,158,11,0.1)]" 
                  : index === 1
                  ? "bg-gradient-to-r from-slate-300/10 to-transparent border-slate-300/20"
                  : index === 2
                  ? "bg-gradient-to-r from-orange-600/10 to-transparent border-orange-600/20"
                  : "bg-slate-800/40 border-white/5"
              }`}
            >
              <div className="flex items-center gap-4">
                <div className={`w-8 text-center font-black text-xl italic ${
                  index === 0 ? "text-amber-400 drop-shadow-[0_0_8px_rgba(245,158,11,0.8)]" :
                  index === 1 ? "text-slate-300" :
                  index === 2 ? "text-orange-500" : "text-slate-500"
                }`}>
                  #{index + 1}
                </div>
                
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <Image 
                      src={`https://api.dicebear.com/7.x/bottts/svg?seed=${player.token}`} 
                      alt={player.pseudonym} 
                      width={40}
                      height={40}
                      className="w-10 h-10 rounded-lg bg-slate-900 border border-white/10 group-hover:border-purple-400/50 transition-colors"
                    />
                    {player.badge === "Ecosystem Guardian" && (
                      <div className="absolute -top-2 -right-2 bg-rose-500 text-white text-[9px] font-black px-1.5 py-0.5 rounded shadow-[0_0_10px_rgba(243,24,64,0.8)] animate-pulse flex items-center">
                        <Flame className="w-2.5 h-2.5 mr-0.5" />
                        Guardian
                      </div>
                    )}
                  </div>
                  <div>
                    <div className="font-bold text-slate-200 group-hover:text-white transition-colors">{player.pseudonym}</div>
                    <div className="text-xs text-slate-400 font-mono opacity-80">{player.token.substring(0, 8)}</div>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="flex flex-col items-end">
                  <div className="text-lg font-black tracking-tight text-white flex items-center gap-1.5" style={{ textShadow: "0 0 10px rgba(255,255,255,0.3)" }}>
                    {player.total_amount.toLocaleString()}
                    <span className="text-[10px] text-cyan-400 uppercase tracking-widest font-normal">THB</span>
                  </div>
                </div>
                <div className="w-6 flex justify-center">
                  <Minus className="w-4 h-4 text-slate-500" />
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </GlassCard>
  );
}
