"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { salvoClient, EngineHealth } from "@/lib/salvoClient";
import Card3DTilt from "@/components/3d/Card3DTilt";

/**
 * Dashboard widget showing Salvo engine status, recent scan stats, and quick actions.
 * Gracefully degrades when engine is offline.
 */
export const SalvoDashboardWidget: React.FC = () => {
  const [health, setHealth] = useState<EngineHealth | null>(null);
  const [pipelineStats, setPipelineStats] = useState<{ total: number; scannedAt: string | null } | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      const h = await salvoClient.getHealth();
      setHealth(h);

      if (h.status === "online") {
        try {
          const data = await salvoClient.getJobs({ limit: 1 });
          setPipelineStats({ total: data.total || 0, scannedAt: data.scannedAt || null });
        } catch {}
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const isOnline = health?.status === "online";

  return (
    <Card3DTilt maxDegree={6} scaleOnHover={1.02} className="h-full">
      <div className="glass-panel p-6 flex flex-col justify-between h-full relative overflow-hidden">
        {/* Gradient accent */}
        <div className="absolute top-0 right-0 w-32 h-32 rounded-bl-[100%] opacity-10" style={{ background: isOnline ? "linear-gradient(135deg, #06b6d4, #10b981)" : "linear-gradient(135deg, #ef4444, #f97316)" }} />

        {/* Header */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-mono font-bold text-[#4F46E5] uppercase tracking-widest bg-[#E0E7FF] px-3.5 py-1 rounded-full border border-[#c7d2fe]">
              Salvo Engine
            </span>
            <div className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${isOnline ? "bg-emerald-400 animate-pulse" : "bg-red-500"}`} />
              <span className={`text-[10px] font-mono font-bold ${isOnline ? "text-emerald-600" : "text-red-500"}`}>
                {isOnline ? "ONLINE" : "OFFLINE"}
              </span>
            </div>
          </div>

          <h3 className="text-xl font-bold text-slate-900 font-heading mb-1">
            Zero-Auth Discovery
          </h3>
          <p className="text-xs text-slate-500 leading-relaxed">
            {isOnline
              ? `${health?.providersCount || 8} providers active · ${pipelineStats?.total || 0} scored postings`
              : "Start the companion engine to enable job scanning, tailoring, and assisted apply."
            }
          </p>
        </div>

        {/* Stats Grid */}
        {isOnline && (
          <div className="grid grid-cols-3 gap-2 my-4 font-mono text-center">
            <div className="bg-white p-2.5 rounded-xl border border-[#E0E7FF] shadow-xs">
              <span className="text-slate-400 block text-[9px] uppercase">Providers</span>
              <span className="font-extrabold text-[#4F46E5]">{health?.providersCount || 8}</span>
            </div>
            <div className="bg-white p-2.5 rounded-xl border border-[#E0E7FF] shadow-xs">
              <span className="text-slate-400 block text-[9px] uppercase">In Pipeline</span>
              <span className="font-extrabold text-[#0EA5E9]">{pipelineStats?.total || 0}</span>
            </div>
            <div className="bg-white p-2.5 rounded-xl border border-[#E0E7FF] shadow-xs">
              <span className="text-slate-400 block text-[9px] uppercase">Excel</span>
              <span className="font-extrabold text-[#10B981]">{health?.excelStoreConnected ? "✓" : "—"}</span>
            </div>
          </div>
        )}

        {pipelineStats?.scannedAt && (
          <p className="text-[10px] text-slate-400 font-mono mb-3">
            Last scan: {new Date(pipelineStats.scannedAt).toLocaleString()}
          </p>
        )}

        {/* Action */}
        <div className="flex items-center gap-2 mt-auto pt-3">
          <Link
            href="/jobs"
            className="flex-1 text-center px-4 py-2.5 rounded-xl font-bold text-xs bg-gradient-to-r from-[#4F46E5] to-[#0EA5E9] text-white shadow-md hover:shadow-indigo-500/25 transition-all"
          >
            {isOnline ? "⚡ Open Job Feed" : "🔌 View Engine Status"}
          </Link>
          {isOnline && (
            <Link
              href="/applications"
              className="px-3 py-2.5 rounded-xl text-xs font-bold text-slate-600 bg-white border border-[#E0E7FF] hover:bg-slate-50 transition-colors"
            >
              📊 Tracker
            </Link>
          )}
        </div>
      </div>
    </Card3DTilt>
  );
};

export default SalvoDashboardWidget;
