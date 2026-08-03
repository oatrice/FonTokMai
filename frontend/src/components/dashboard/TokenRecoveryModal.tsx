import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Lock, Key, AlertCircle, CheckCircle2, Copy, Check } from "lucide-react";

interface TokenRecoveryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function TokenRecoveryModal({ isOpen, onClose }: TokenRecoveryModalProps) {
  const [txHash, setTxHash] = useState("");
  const [timestamp, setTimestamp] = useState("");
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recoveredToken, setRecoveredToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!recoveredToken) return;
    await navigator.clipboard.writeText(recoveredToken);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/auth/recover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transaction_id: txHash,
          timestamp: timestamp,
          amount: parseFloat(amount),
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Recovery failed. Invalid details.");
      }

      setRecoveredToken(data.token);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    // Reset state on close
    setTxHash("");
    setTimestamp("");
    setAmount("");
    setError(null);
    setRecoveredToken(null);
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="w-full max-w-md bg-slate-900/90 border border-white/10 shadow-2xl rounded-2xl pointer-events-auto overflow-hidden backdrop-blur-xl"
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-2 text-white">
                    <Lock className="w-5 h-5 text-emerald-400" />
                    <h2 className="text-xl font-bold tracking-tight">Zero-PII Token Recovery</h2>
                  </div>
                  <button
                    onClick={handleClose}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
                    aria-label="Close"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {!recoveredToken ? (
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <p className="text-sm text-slate-300 mb-4">
                      Enter the exact details from your original donation transaction to securely recover your 30-day access token.
                    </p>

                    {error && (
                      <div className="flex items-start gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
                        <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                        <span>{error}</span>
                      </div>
                    )}

                    <div className="space-y-1">
                      <label htmlFor="txHash" className="text-xs font-medium text-slate-400">
                        Transaction Hash
                      </label>
                      <input
                        id="txHash"
                        type="text"
                        required
                        value={txHash}
                        onChange={(e) => setTxHash(e.target.value)}
                        className="w-full bg-slate-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                        placeholder="e.g. 0x123abc..."
                      />
                    </div>

                    <div className="space-y-1">
                      <label htmlFor="timestamp" className="text-xs font-medium text-slate-400">
                        Timestamp (Unix or ISO)
                      </label>
                      <input
                        id="timestamp"
                        type="text"
                        required
                        value={timestamp}
                        onChange={(e) => setTimestamp(e.target.value)}
                        className="w-full bg-slate-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                        placeholder="e.g. 1690000000"
                      />
                    </div>

                    <div className="space-y-1">
                      <label htmlFor="amount" className="text-xs font-medium text-slate-400">
                        Amount (THB)
                      </label>
                      <input
                        id="amount"
                        type="number"
                        step="any"
                        required
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        className="w-full bg-slate-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                        placeholder="e.g. 500"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full mt-2 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? (
                        "Recovering..."
                      ) : (
                        <>
                          <Key className="w-4 h-4" />
                          Recover Token
                        </>
                      )}
                    </button>
                  </form>
                ) : (
                  <div className="py-6 text-center space-y-4">
                    <div className="mx-auto w-12 h-12 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mb-4">
                      <CheckCircle2 className="w-6 h-6" />
                    </div>
                    <h3 className="text-lg font-bold text-white">Recovery Successful</h3>
                    <p className="text-sm text-slate-300">
                      Your recovered access token:
                    </p>
                    <div className="bg-slate-950 border border-white/10 rounded-lg p-4 flex items-center justify-between gap-3">
                      <code className="text-emerald-400 font-mono text-lg font-bold select-all break-all text-left">
                        {recoveredToken}
                      </code>
                      <button
                        onClick={handleCopy}
                        title={copied ? "Copied!" : "Copy token"}
                        className={`shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                          copied
                            ? "bg-emerald-500/20 text-emerald-400"
                            : "bg-white/5 text-slate-400 hover:text-white hover:bg-white/10"
                        }`}
                      >
                        {copied ? (
                          <><Check className="w-3.5 h-3.5" /><span>Copied!</span></>
                        ) : (
                          <><Copy className="w-3.5 h-3.5" /><span>Copy</span></>
                        )}
                      </button>
                    </div>
                    <p className="text-xs text-slate-400 mt-4">
                      Keep this token safe. It is valid for your 30-day sponsor period.
                    </p>
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
