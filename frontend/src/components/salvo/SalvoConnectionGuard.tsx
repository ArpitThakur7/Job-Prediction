"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { salvoClient, EngineHealth } from "@/lib/salvoClient";
import { useApp } from "@/context/AppContext";

interface SalvoConnectionGuardProps {
  children: React.ReactNode;
  /** If true, shows children even when engine is offline (with a warning banner). Default: true */
  degradedMode?: boolean;
}

/**
 * Wraps Salvo-dependent pages with an engine health check.
 * Shows a premium diagnostic banner if the engine is unreachable,
 * and periodically polls to detect reconnection.
 */
export const SalvoConnectionGuard: React.FC<SalvoConnectionGuardProps> = ({
  children,
  degradedMode = true,
}) => {
  const { currentThemeColors } = useApp();
  const [health, setHealth] = useState<EngineHealth | null>(null);
  const [checking, setChecking] = useState(true);
  const [dismissed, setDismissed] = useState(false);
  const [copied, setCopied] = useState(false);

  const checkHealth = useCallback(async () => {
    const h = await salvoClient.getHealth();
    setHealth(h);
    setChecking(false);
  }, []);

  // Initial check + periodic polling when offline
  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000); // poll every 10s
    return () => clearInterval(interval);
  }, [checkHealth]);

  // Auto-dismiss banner when engine comes online
  useEffect(() => {
    if (health?.status === "online") setDismissed(false); // reset for next offline
  }, [health?.status]);

  const isOnline = health?.status === "online";

  const handleCopyCommand = async () => {
    try {
      await navigator.clipboard.writeText("cd engine && node server.mjs");
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  // Show initial loading state
  if (checking) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <div className="w-10 h-10 border-4 border-cyan-500/20 border-t-cyan-400 rounded-full animate-spin" />
        <span className="text-xs font-mono text-slate-400">Connecting to Salvo Engine...</span>
      </div>
    );
  }

  // Offline: block or degrade
  if (!isOnline) {
    const banner = (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="p-5 rounded-2xl border backdrop-blur-xl shadow-xl mb-6"
          style={{
            backgroundColor: "rgba(127, 29, 29, 0.15)",
            borderColor: "rgba(239, 68, 68, 0.3)",
          }}
        >
          <div className="flex items-start gap-4">
            {/* Pulsing offline indicator */}
            <div className="relative shrink-0 mt-1">
              <span className="block w-3 h-3 rounded-full bg-red-500" />
              <span className="block absolute inset-0 w-3 h-3 rounded-full bg-red-500 animate-ping opacity-50" />
            </div>

            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-bold text-red-400 mb-1 font-mono">
                Salvo Engine Offline
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-3">
                The companion engine at <code className="px-1.5 py-0.5 rounded bg-black/40 border border-white/10 text-red-300">http://127.0.0.1:4173</code> is
                not responding. Job discovery, tailoring, and assisted apply require the local engine process.
              </p>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">Start with:</span>
                  <code className="px-3 py-1.5 rounded-lg bg-black/50 border border-white/10 text-xs font-mono text-slate-200 select-all">
                    cd engine && node server.mjs
                  </code>
                  <button
                    onClick={handleCopyCommand}
                    className="px-2.5 py-1.5 rounded-lg text-[10px] font-mono font-bold bg-white/10 border border-white/10 text-slate-300 hover:bg-white/20 transition-all"
                  >
                    {copied ? "Copied!" : "📋 Copy"}
                  </button>
                </div>

                <button
                  onClick={() => {
                    setChecking(true);
                    checkHealth();
                  }}
                  className="px-3 py-1.5 rounded-lg text-xs font-mono border border-red-500/30 text-red-300 hover:bg-red-500/10 transition-colors"
                >
                  🔄 Retry
                </button>
              </div>

              <p className="text-[10px] text-slate-500 font-mono mt-3">
                Or use the unified launcher: <code className="px-1 py-0.5 rounded bg-black/30 text-slate-400">run.bat</code> (starts backend + engine + frontend together)
              </p>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>
    );

    if (!degradedMode) {
      return (
        <div className="space-y-6">
          {banner}
          <div
            className="p-12 rounded-3xl border border-dashed border-white/10 text-center backdrop-blur-md"
            style={{ backgroundColor: "rgba(15, 23, 42, 0.4)" }}
          >
            <span className="text-3xl block mb-3">🔌</span>
            <h3 className="text-lg font-bold text-slate-200 mb-2">Engine Required</h3>
            <p className="text-xs text-slate-400 font-mono max-w-md mx-auto">
              This page requires a running Salvo engine. Start the engine and this page will automatically reconnect.
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-0">
        {!dismissed && banner}
        {children}
      </div>
    );
  }

  return <>{children}</>;
};

export default SalvoConnectionGuard;
