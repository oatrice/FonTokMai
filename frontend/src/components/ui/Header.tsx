import Link from "next/link";
import { Activity, Flame, ChevronRight } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-xl bg-black/40 border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Breadcrumb Header */}
        <div className="flex items-center gap-2 text-sm">
          <Link href="/" className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors group">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-xs font-bold shadow-md shadow-cyan-500/20 group-hover:scale-105 transition-transform">
              ⛈️
            </div>
            <span className="font-bold text-white tracking-tight">FonMaYang</span>
          </Link>

          <ChevronRight className="w-4 h-4 text-zinc-600 shrink-0" />

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-medium text-xs">
            <Activity className="w-3.5 h-3.5" />
            <span>System Dashboard</span>
          </div>

          <span className="hidden sm:inline-block ml-1 text-xs px-2 py-0.5 rounded-full bg-white/5 text-zinc-400 border border-white/10">
            v0.2.0
          </span>
        </div>

        {/* Action Links */}
        <nav className="flex items-center gap-4 text-sm">
          <a
            href="https://t.me/FonMaYangBot"
            target="_blank"
            rel="noreferrer"
            className="text-zinc-400 hover:text-white transition-colors flex items-center gap-1.5 text-xs sm:text-sm bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-lg border border-white/10"
          >
            <Flame className="w-4 h-4 text-amber-400" />
            <span>Telegram Bot</span>
          </a>
        </nav>
      </div>
    </header>
  );
}
