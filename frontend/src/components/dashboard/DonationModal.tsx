import React, { useState } from "react";
import { X, Heart, Loader2, Lock } from "lucide-react";
import { GlassCard } from "../ui/GlassCard";
import { GlassButton } from "../ui/GlassButton";

interface DonationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function DonationModal({ isOpen, onClose }: DonationModalProps) {
  const [amount, setAmount] = useState<number | "">("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const presetAmounts = [50, 100, 300, 500];

  const handleProceed = async () => {
    if (!amount || amount < 10) {
      setError("Please enter a valid amount (minimum 10 THB)");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch(
        process.env.NEXT_PUBLIC_API_URL 
          ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1/donations/create-stripe-session`
          : "/api/v1/donations/create-stripe-session",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            amount_thb: Number(amount),
            client_reference_id: "web-direct",
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to create checkout session");
      }

      const data = await response.json();
      if (data.url) {
        window.location.href = data.url;
      } else {
        throw new Error("No URL returned from server");
      }
    } catch (err: any) {
      console.error("Donation error:", err);
      setError("Failed to connect to payment gateway. Please try again.");
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-md animate-in slide-in-from-bottom-4 duration-300">
        <GlassCard variant="glow" glowColor="cyan" className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Heart className="h-5 w-5 text-cyan-400" />
              Contribute to Milestone
            </h2>
            <button
              onClick={onClose}
              className="p-2 rounded-full text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Select Amount (THB)
              </label>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {presetAmounts.map((preset) => (
                  <button
                    key={preset}
                    onClick={() => setAmount(preset)}
                    className={`py-2 px-3 rounded-lg border font-medium transition-all ${
                      amount === preset
                        ? "bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-[0_0_15px_rgba(34,211,238,0.2)]"
                        : "bg-slate-800/50 border-white/10 text-slate-300 hover:border-white/30 hover:bg-slate-800"
                    }`}
                  >
                    ฿{preset}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Custom Amount
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">฿</span>
                <input
                  type="number"
                  min="10"
                  step="1"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value ? Number(e.target.value) : "")}
                  className="w-full bg-slate-900/80 border border-white/10 rounded-lg py-2.5 pl-8 pr-4 text-white focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/50 transition-all placeholder:text-slate-600"
                  placeholder="Enter custom amount"
                />
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            <div className="pt-2">
              <GlassButton
                variant="primary"
                className="w-full justify-center py-3 text-base"
                onClick={handleProceed}
                disabled={isSubmitting || !amount}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <span>Proceed to Payment</span>
                  </>
                )}
              </GlassButton>
              <p className="mt-4 text-center text-xs text-slate-500 flex items-center justify-center gap-1">
                <Lock className="h-3 w-3 inline" />
                Payments processed securely by Stripe
              </p>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
