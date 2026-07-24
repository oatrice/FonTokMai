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
  glow?: boolean;
  intensity?: "light" | "medium" | "heavy";
}

export const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  (
    {
      className,
      glowColor = "blue",
      interactive = false,
      glow = false,
      intensity = "medium",
      children,
      ...props
    },
    ref
  ) => {
    const intensityClasses = {
      light: "bg-zinc-900/40 backdrop-blur-sm border-white/5",
      medium: "bg-zinc-900/60 backdrop-blur-md border-white/10 shadow-xl",
      heavy: "bg-zinc-950/80 backdrop-blur-xl border-white/15 shadow-2xl",
    };

    const glowStyles = {
      blue: "hover:shadow-[0_0_25px_rgba(59,130,246,0.25)] hover:border-blue-500/40",
      cyan: "hover:shadow-[0_0_25px_rgba(6,182,212,0.25)] hover:border-cyan-500/40",
      emerald: "hover:shadow-[0_0_25px_rgba(16,185,129,0.25)] hover:border-emerald-500/40",
      amber: "hover:shadow-[0_0_25px_rgba(245,158,11,0.25)] hover:border-amber-500/40",
      rose: "hover:shadow-[0_0_25px_rgba(244,63,94,0.25)] hover:border-rose-500/40",
      purple: "hover:shadow-[0_0_25px_rgba(168,85,247,0.25)] hover:border-purple-500/40",
    };

    return (
      <div
        ref={ref}
        className={cn(
          "rounded-2xl transition-all duration-300 relative overflow-hidden",
          intensityClasses[intensity],
          glow && "hover:border-cyan-500/30 hover:shadow-cyan-500/10 hover:shadow-2xl",
          interactive && "cursor-pointer hover:-translate-y-1 hover:bg-slate-900/80",
          interactive && glowStyles[glowColor],
          className
        )}
        {...props}
      >
        <div className="pointer-events-none absolute -top-24 -left-24 h-48 w-48 rounded-full bg-white/5 blur-2xl" />
        {children}
      </div>
    );
  }
);
GlassCard.displayName = "GlassCard";
