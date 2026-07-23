import React from "react";
import { cn } from "./GlassCard";

export interface GlassButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const GlassButton = React.forwardRef<HTMLButtonElement, GlassButtonProps>(
  ({ className, variant = "primary", size = "md", isLoading = false, children, disabled, ...props }, ref) => {
    const sizeStyles = {
      sm: "px-3 py-1.5 text-xs rounded-lg gap-1.5",
      md: "px-4 py-2.5 text-sm rounded-xl gap-2",
      lg: "px-6 py-3.5 text-base rounded-2xl gap-2.5",
    };

    const variantStyles = {
      primary: "bg-blue-600/80 hover:bg-blue-500/90 text-white backdrop-blur-md border border-blue-400/30 shadow-lg shadow-blue-500/20 hover:shadow-blue-500/40 hover:-translate-y-0.5 active:translate-y-0",
      secondary: "bg-slate-800/60 hover:bg-slate-700/80 text-slate-100 backdrop-blur-md border border-white/10 shadow-md hover:border-white/20 hover:-translate-y-0.5 active:translate-y-0",
      outline: "bg-transparent hover:bg-white/10 text-slate-200 backdrop-blur-sm border border-white/20 hover:border-white/40 shadow-sm",
      danger: "bg-rose-600/75 hover:bg-rose-500/90 text-white backdrop-blur-md border border-rose-400/30 shadow-lg shadow-rose-500/20 hover:shadow-rose-500/40 hover:-translate-y-0.5 active:translate-y-0",
      ghost: "bg-transparent hover:bg-white/5 text-slate-300 hover:text-white border border-transparent",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          "inline-flex items-center justify-center font-medium transition-all duration-200 select-none disabled:opacity-50 disabled:pointer-events-none disabled:transform-none",
          sizeStyles[size],
          variantStyles[variant],
          className
        )}
        {...props}
      >
        {isLoading ? (
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent mr-2" />
        ) : null}
        {children}
      </button>
    );
  }
);
GlassButton.displayName = "GlassButton";
