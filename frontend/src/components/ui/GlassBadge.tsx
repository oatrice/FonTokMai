import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface GlassBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "cyan" | "success" | "warning" | "danger" | "blue" | "emerald" | "amber" | "rose" | "purple" | "slate";
  dot?: boolean;
}

export function GlassBadge({
  children,
  variant = "default",
  dot = false,
  className,
  ...props
}: GlassBadgeProps) {
  const variantStyles = {
    default: "bg-white/5 text-zinc-300 border-white/10",
    cyan: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
    success: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
    warning: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    danger: "bg-rose-500/15 text-rose-300 border-rose-500/30",
    blue: "bg-blue-500/15 text-blue-300 border-blue-500/30",
    emerald: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
    amber: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    rose: "bg-rose-500/15 text-rose-300 border-rose-500/30",
    purple: "bg-purple-500/15 text-purple-300 border-purple-500/30",
    slate: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  };

  return (
    <span
      className={twMerge(
        clsx(
          "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border backdrop-blur-md shadow-sm",
          variantStyles[variant],
          className
        )
      )}
      {...props}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />}
      {children}
    </span>
  );
}
