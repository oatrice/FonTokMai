import Link from "next/link";
import { Activity, ShieldCheck, Flame, Layers } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-xl bg-black/40 border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold shadow-lg shadow-cyan-500/20">
            ⛈️
          </div>
          <div>
            <span className="font-extrabold text-lg text-white tracking-tight">FonMaYang</span>
            <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">v0.2.0</span>
          </div>
        </Link>
        <nav className="flex items-center gap-6 text-sm">
          <Link href="/dashboard" className="text-cyan-400 font-medium flex items-center gap-1.5 hover:text-cyan-300 transition-colors">
            <Activity className="w-4 h-4" />
            Dashboard
          </Link>
          <a href="https://t.me/FonMaYangBot" target="_blank" rel="noreferrer" className="text-zinc-400 hover:text-white transition-colors flex items-center gap-1.5">
            <Flame className="w-4 h-4 text-amber-400" />
            Telegram Bot
          </a>
        </nav>
      </div>
    </header>
  );
}
