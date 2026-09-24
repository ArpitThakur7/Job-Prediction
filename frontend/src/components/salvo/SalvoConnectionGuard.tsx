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
        <div className="w-10 h-10 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
        <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300">Connecting to Salvo Engine...</span>
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
          className="p-5 rounded-2xl border border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-950/20 backdrop-blur-xl shadow-lg mb-6"
        >
          <div className="flex items-start gap-4">
            {/* Pulsing offline indicator */}
            <div className="relative shrink-0 mt-1">
              <span className="block w-3 h-3 rounded-full bg-red-500" />
              <span className="block absolute inset-0 w-3 h-3 rounded-full bg-red-500 animate-ping opacity-50" />
            </div>

            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-bold text-red-700 dark:text-red-400 mb-1 font-mono">
                Salvo Engine Offline
              </h3>
              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed mb-3">
                The companion engine at <code className="px-1.5 py-0.5 rounded bg-white dark:bg-black/40 border border-slate-300 dark:border-white/10 text-red-700 dark:text-red-300 font-bold">http://127.0.0.1:4173</code> is
                not responding. Job discovery, tailoring, and assisted apply require the local engine process.
              </p>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-slate-600 dark:text-slate-400 uppercase font-bold tracking-wider">Start with:</span>
                  <code className="px-3 py-1.5 rounded-xl bg-slate-900 text-white dark:bg-black/60 border border-slate-700 dark:border-white/10 text-xs font-mono font-bold select-all">
                    cd engine && node server.mjs
                  </code>
                  <button
                    onClick={handleCopyCommand}
                    className="px-2.5 py-1.5 rounded-xl text-[10px] font-mono font-bold bg-white dark:bg-white/10 border border-slate-300 dark:border-white/10 text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/20 transition-all shadow-sm"
                  >
                    {copied ? "✓ Copied!" : "📋 Copy"}
                  </button>
                </div>

                <button
                  onClick={() => {
                    setChecking(true);
                    checkHealth();
                  }}
                  className="px-3 py-1.5 rounded-xl text-xs font-mono font-bold border border-red-300 dark:border-red-500/30 text-red-700 dark:text-red-300 bg-white dark:bg-transparent hover:bg-red-100 dark:hover:bg-red-500/10 transition-colors shadow-sm"
                >
                  🔄 Retry Connection
                </button>
              </div>

              <p className="text-[11px] text-slate-600 dark:text-slate-400 font-mono mt-3">
                Or use the unified launcher: <code className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-black/30 font-bold text-slate-800 dark:text-slate-300">run.bat</code> (starts backend + engine + frontend together)
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
