"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { salvoClient } from "@/lib/salvoClient";
import { useApp } from "@/context/AppContext";

interface ScanModalProps {
  isOpen: boolean;
  onClose: () => void;
  onScanComplete?: () => void;
}

export const ScanModal: React.FC<ScanModalProps> = ({ isOpen, onClose, onScanComplete }) => {
  const { currentThemeColors } = useApp();
  const [mode, setMode] = useState<"global" | "india">("global");
  const [scanning, setScanning] = useState(false);
  const [currentSource, setCurrentSource] = useState("");
  const [progress, setProgress] = useState(0);
  const [totalSources, setTotalSources] = useState(1);
  const [completedCount, setCompletedCount] = useState(0);
  const [foundJobs, setFoundJobs] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [finishedStats, setFinishedStats] = useState<any>(null);

  const startScan = async () => {
    setScanning(true);
    setLogs([]);
    setFinishedStats(null);
    setProgress(0);
    setFoundJobs(0);

    try {
      const res = await salvoClient.startScan(mode);
      if (!res.scanId) throw new Error(res.error || "Failed to initiate scan");

      salvoClient.createScanStream(
        res.scanId,
        (data) => {
          if (data.type === "start") {
            setTotalSources(data.totalSources || 1);
            setLogs((prev) => [...prev, `🚀 Initiated ${data.mode.toUpperCase()} sweep across ${data.totalSources} sources.`]);
          } else if (data.type === "source") {
            setCurrentSource(data.source);
            setCompletedCount(data.completed);
            setProgress(Math.round((data.completed / data.total) * 100));
            setFoundJobs(data.jobsCount);
          } else if (data.type === "filtering") {
            setLogs((prev) => [...prev, `⚡ Triage filter running on ${data.rawCount} raw postings...`]);
          } else if (data.type === "done") {
            setScanning(false);
            setFinishedStats(data.stats);
            setLogs((prev) => [...prev, `✅ Scan complete: ${data.totalJobs} qualified postings merged into tracker!`]);
            if (onScanComplete) onScanComplete();
          } else if (data.type === "error") {
            setScanning(false);
            setLogs((prev) => [...prev, `❌ Error: ${data.error}`]);
          }
        },
        (err) => {
          console.error("SSE stream error", err);
          setScanning(false);
        }
      );
    } catch (err: any) {
      setScanning(false);
      setLogs((prev) => [...prev, `❌ Failed to start scan: ${err.message}`]);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="relative w-full max-w-lg p-6 rounded-2xl border shadow-2xl overflow-hidden"
          style={{
            backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.95)",
            borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.15)",
            color: currentThemeColors.textColor || "#F8FAFC",
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-white/10">
            <div className="flex items-center gap-3">
              <span className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 text-lg border border-cyan-500/20">
                📡
              </span>
              <div>
                <h3 className="font-bold text-lg tracking-tight">Zero-Auth Discovery Radar</h3>
                <p className="text-xs text-slate-400">Scans 130+ tech boards with no login or bot detection risk</p>
              </div>
            </div>
            {!scanning && (
              <button
                onClick={onClose}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
              >
                ✕
              </button>
            )}
          </div>

          {/* Mode Selector */}
          <div className="my-5">
            <label className="block text-xs font-mono font-medium text-slate-400 mb-2">SCAN PIPELINE</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                disabled={scanning}
                onClick={() => setMode("global")}
                className={`flex flex-col items-center p-3 rounded-xl border text-center transition-all ${
                  mode === "global"
                    ? "border-cyan-400 bg-cyan-500/15 shadow-[0_0_15px_rgba(6,182,212,0.2)]"
                    : "border-white/10 bg-white/5 hover:bg-white/10"
                }`}
              >
                <span className="text-base mb-1">🌐</span>
                <span className="font-bold text-xs">Global Remote</span>
                <span className="text-[10px] text-slate-400 mt-0.5">Worldwide tech openings</span>
              </button>
              <button
                type="button"
                disabled={scanning}
                onClick={() => setMode("india")}
                className={`flex flex-col items-center p-3 rounded-xl border text-center transition-all ${
                  mode === "india"
                    ? "border-emerald-400 bg-emerald-500/15 shadow-[0_0_15px_rgba(16,185,129,0.2)]"
                    : "border-white/10 bg-white/5 hover:bg-white/10"
                }`}
              >
                <span className="text-base mb-1">🇮🇳</span>
                <span className="font-bold text-xs">India Regional</span>
                <span className="text-[10px] text-slate-400 mt-0.5">Onsite / Hybrid / Remote</span>
              </button>
            </div>
          </div>

          {/* Active Scanning Status */}
          {scanning && (
            <div className="my-5 p-4 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
              <div className="flex items-center justify-between text-xs font-mono mb-2">
                <span className="text-cyan-400 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                  Probing: {currentSource || "Connecting..."}
                </span>
                <span className="font-bold">{progress}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="flex justify-between items-center mt-3 text-[11px] text-slate-400 font-mono">
                <span>Sources: {completedCount} / {totalSources}</span>
                <span>Scraped: {foundJobs} jobs</span>
              </div>
            </div>
          )}

          {/* Completion Card */}
          {finishedStats && (
            <div className="my-4 p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 text-xs">
              <h4 className="font-bold text-emerald-400 mb-2 flex items-center gap-2">
                <span>🎉</span> Pipeline Updated & Synced to Excel
              </h4>
              <div className="grid grid-cols-3 gap-2 text-center font-mono">
                <div className="p-2 rounded-lg bg-black/30 border border-white/5">
                  <span className="block text-slate-400 text-[10px]">Total Scanned</span>
                  <span className="text-sm font-bold">{finishedStats.total}</span>
                </div>
                <div className="p-2 rounded-lg bg-black/30 border border-white/5">
                  <span className="block text-slate-400 text-[10px]">Filtered Off</span>
                  <span className="text-sm font-bold text-amber-400">
                    {(finishedStats.title || 0) + (finishedStats.location || 0) + (finishedStats.experience || 0)}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-black/30 border border-white/5">
                  <span className="block text-slate-400 text-[10px]">High Fit Kept</span>
                  <span className="text-sm font-bold text-emerald-400">{finishedStats.kept}</span>
                </div>
              </div>
            </div>
          )}

          {/* Log window */}
          {logs.length > 0 && (
            <div className="max-h-28 overflow-y-auto p-2.5 rounded-lg bg-black/40 border border-white/5 font-mono text-[11px] text-slate-300 space-y-1 mb-4">
              {logs.map((log, i) => (
                <div key={i}>{log}</div>
              ))}
            </div>
          )}

          {/* Action Footer */}
          <div className="flex justify-end gap-3 pt-2">
            {!scanning ? (
              <>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-xl text-xs font-mono text-slate-300 border border-white/10 hover:bg-white/5 transition-all"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={startScan}
                  className="px-5 py-2 rounded-xl text-xs font-mono font-bold bg-cyan-500 hover:bg-cyan-400 text-black shadow-[0_0_20px_rgba(6,182,212,0.4)] transition-all"
                >
                  Start Discovery Sweep
                </button>
              </>
            ) : (
              <span className="text-xs text-slate-400 font-mono animate-pulse">Sweep in progress...</span>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default ScanModal;
