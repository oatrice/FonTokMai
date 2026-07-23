import React from "react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "subtle" | "glow" | "accent";
  glowColor?: "blue" | "cyan" | "emerald" | "amber" | "rose" | "purple";
  interactive?: boolean;
}

export const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({ className, variant = "default", glowColor = "blue", interactive = false, children, ...props }, ref) => {
    const glowStyles = {
      blue: "hover:shadow-[0_0_25px_rgba(59,130,246,0.25)] hover:border-blue-500/40",
      cyan: "hover:shadow-[0_0_25px_rgba(6,182,212,0.25)] hover:border-cyan-500/40",
      emerald: "hover:shadow-[0_0_25px_rgba(16,185,129,0.25)] hover:border-emerald-500/40",
      amber: "hover:shadow-[0_0_25px_rgba(245,158,11,0.25)] hover:border-amber-500/40",
      rose: "hover:shadow-[0_0_25px_rgba(244,63,94,0.25)] hover:border-rose-500/40",
      purple: "hover:shadow-[0_0_25px_rgba(168,85,247,0.25)] hover:border-purple-500/40",
    };

    const variantStyles = {
      default: "bg-slate-900/65 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/40",
      subtle: "bg-slate-950/40 backdrop-blur-md border border-white/5 shadow-lg",
      glow: "bg-slate-900/70 backdrop-blur-2xl border border-white/15 shadow-2xl",
      accent: "bg-gradient-to-br from-slate-900/80 via-slate-900/60 to-slate-950/90 backdrop-blur-xl border border-blue-500/20 shadow-2xl",
    };

    return (
      <div
        ref={ref}
        className={cn(
          "rounded-2xl transition-all duration-300 relative overflow-hidden",
          variantStyles[variant],
          interactive && "cursor-pointer hover:-translate-y-1 hover:bg-slate-900/80",
          interactive && glowStyles[glowColor],
          className
        )}
        {...props}
      >
        {/* Subtle glass reflection highlight */}
        <div className="pointer-events-none absolute -top-24 -left-24 h-48 w-48 rounded-full bg-white/5 blur-2xl" />
        {children}
      </div>
    );
  }
);
GlassCard.displayName = "GlassCard";
