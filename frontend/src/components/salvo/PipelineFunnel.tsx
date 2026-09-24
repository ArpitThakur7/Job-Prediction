"use client";

import React from "react";
import { motion } from "framer-motion";

export interface FunnelStage {
  key: string;
  label: string;
  emoji: string;
  count: number;
  color: string;
}

interface PipelineFunnelProps {
  stages: FunnelStage[];
  totalTracked: number;
  activeFilter?: string | null;
  onSelectStage?: (stageKey: string | null) => void;
}

export default function PipelineFunnel({
  stages,
  totalTracked,
  activeFilter = null,
  onSelectStage,
}: PipelineFunnelProps) {
  // Max count to normalize stage bar widths/heights
  const maxCount = Math.max(...stages.map((s) => s.count), 1);

  return (
    <div className="p-5 rounded-3xl border border-white/10 bg-slate-900/60 backdrop-blur-xl shadow-xl space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-white/5">
        <div className="flex items-center gap-2">
          <span className="text-base">🌪️</span>
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
            Pipeline Conversion Funnel
          </h3>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
            {totalTracked} TOTAL
          </span>
        </div>

        {activeFilter && (
          <button
            onClick={() => onSelectStage?.(null)}
            className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300 underline underline-offset-2 flex items-center gap-1"
          >
            <span>Reset filter ({activeFilter})</span>
            <span>✕</span>
          </button>
        )}
      </div>

      {/* Funnel Pipeline Visualizer */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-2 pt-1">
        {stages.map((stage, idx) => {
          const isSelected = activeFilter === stage.key;
          const shareOfTotal = totalTracked > 0 ? Math.round((stage.count / totalTracked) * 100) : 0;
          
          // Conversion from previous stage
          const prevStage = idx > 0 ? stages[idx - 1] : null;
          const conversionFromPrev =
            prevStage && prevStage.count > 0
              ? Math.round((stage.count / prevStage.count) * 100)
              : null;

          // Height ratio
          const heightRatio = Math.max(15, Math.round((stage.count / maxCount) * 100));

          return (
            <motion.div
              key={stage.key}
              whileHover={{ y: -3, scale: 1.02 }}
              onClick={() => onSelectStage?.(isSelected ? null : stage.key)}
              className={`p-3.5 rounded-2xl border transition-all cursor-pointer relative overflow-hidden flex flex-col justify-between ${
                isSelected
                  ? "border-cyan-400 bg-cyan-950/40 ring-1 ring-cyan-400 shadow-lg"
                  : "border-white/5 bg-black/30 hover:border-white/20"
              }`}
            >
              {/* Animated fill indicator */}
              <div
                className="absolute bottom-0 left-0 right-0 opacity-20 pointer-events-none transition-all duration-700 ease-out"
                style={{
                  height: `${heightRatio}%`,
                  backgroundColor: stage.color,
                }}
              />

              <div className="flex items-center justify-between text-xs mb-2">
                <span className="text-base">{stage.emoji}</span>
                {conversionFromPrev !== null && (
                  <span
                    className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400 border border-white/5"
                    title={`Conversion rate from ${prevStage?.label || "previous"}`}
                  >
                    {conversionFromPrev}%
                  </span>
                )}
              </div>

              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider block text-slate-400 truncate">
                  {stage.label}
                </span>
                <div className="flex items-baseline gap-1.5 mt-0.5">
                  <span className="text-2xl font-black font-mono" style={{ color: stage.color }}>
                    {stage.count}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    ({shareOfTotal}%)
                  </span>
                </div>
              </div>

              {/* Step indicator bar */}
              <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden mt-3">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${heightRatio}%` }}
                  transition={{ duration: 0.8, delay: idx * 0.1 }}
                  className="h-full rounded-full"
                  style={{ backgroundColor: stage.color }}
                />
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
