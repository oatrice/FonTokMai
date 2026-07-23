import React from "react";
import { cn } from "./GlassCard";

export interface GlassBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "blue" | "cyan" | "emerald" | "amber" | "rose" | "purple" | "slate";
  dot?: boolean;
}

export const GlassBadge = React.forwardRef<HTMLSpanElement, GlassBadgeProps>(
  ({ className, variant = "blue", dot = false, children, ...props }, ref) => {
    const variantStyles = {
      blue: "bg-blue-500/15 text-blue-300 border-blue-500/30",
      cyan: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
      emerald: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
      amber: "bg-amber-500/15 text-amber-300 border-amber-500/30",
      rose: "bg-rose-500/15 text-rose-300 border-rose-500/30",
      purple: "bg-purple-500/15 text-purple-300 border-purple-500/30",
      slate: "bg-slate-500/15 text-slate-300 border-slate-500/30",
    };

    const dotBgStyles = {
      blue: "bg-blue-400",
      cyan: "bg-cyan-400",
      emerald: "bg-emerald-400",
      amber: "bg-amber-400",
      rose: "bg-rose-400",
      purple: "bg-purple-400",
      slate: "bg-slate-400",
    };

    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full backdrop-blur-md border shadow-sm",
          variantStyles[variant],
          className
        )}
        {...props}
      >
        {dot && <span className={cn("h-1.5 w-1.5 rounded-full animate-pulse", dotBgStyles[variant])} />}
        {children}
      </span>
    );
  }
);
GlassBadge.displayName = "GlassBadge";
