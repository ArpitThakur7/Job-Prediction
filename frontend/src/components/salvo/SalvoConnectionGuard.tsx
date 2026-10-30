"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { salvoClient, EngineHealth } from "@/lib/salvoClient";

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
        <div className="w-9 h-9 border-[3px] rounded-full animate-spin" style={{ borderColor: "var(--theme-badge-bg)", borderTopColor: "var(--theme-primary)" }} />
        <span className="text-sm" style={{ color: "var(--theme-text-muted)" }}>Connecting to the Salvo engine…</span>
      </div>
    );
  }

  // Offline: block or degrade
  if (!isOnline) {
    if (dismissed) {
      return <>{children}</>;
    }

    const banner = (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          className="glass rounded-[22px] px-5 py-3.5 mb-6 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm"
          role="status"
        >
          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: "var(--fit-mid)" }} />
          <p className="flex-1 min-w-[16rem]">
            <strong className="font-semibold">Showing your last saved scan.</strong>{" "}
            <span style={{ color: "var(--theme-text-muted)" }}>
              Start the Salvo engine to scan for new jobs: <code className="px-1.5 py-0.5 rounded-md bg-black/5 dark:bg-white/10 text-[13px]">cd engine && node server.mjs</code>, or run <code className="px-1.5 py-0.5 rounded-md bg-black/5 dark:bg-white/10 text-[13px]">run.bat</code> to start everything.
            </span>
          </p>
          <div className="flex items-center gap-1">
            <button onClick={handleCopyCommand} className="px-3 py-1.5 rounded-xl font-semibold hover:bg-black/5 dark:hover:bg-white/10">
              {copied ? "Copied" : "Copy command"}
            </button>
            <button
              onClick={() => {
                setChecking(true);
                checkHealth();
              }}
              className="px-3 py-1.5 rounded-xl font-semibold hover:bg-black/5 dark:hover:bg-white/10"
              style={{ color: "var(--theme-primary)" }}
            >
              Try again
            </button>
            <button
              onClick={() => setDismissed(true)}
              className="px-2.5 py-1.5 rounded-xl hover:bg-black/5 dark:hover:bg-white/10"
              aria-label="Dismiss"
              title="Dismiss"
            >
              ✕
            </button>
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
