"use client";

import React from "react";
import Link from "next/link";
import Card3DTilt from "@/components/3d/Card3DTilt";
import ScoreOrb3D from "./ScoreOrb3D";
import { SalvoJob } from "@/lib/salvoClient";
import { useApp } from "@/context/AppContext";

interface JobCard3DProps {
  job: SalvoJob;
  onTailorClick?: (job: SalvoJob) => void;
}

export const JobCard3D: React.FC<JobCard3DProps> = ({ job, onTailorClick }) => {
  const { currentThemeColors } = useApp();
  const score = job.combinedScore ?? (job.score ? Math.round((job.score / 5) * 100) : 75);
  const relevance = job.relevanceScore ?? score;
  const prediction = job.predictionScore ?? score;

  const getSourceBadgeColor = (src?: string) => {
    switch ((src || "").toLowerCase()) {
      case "greenhouse":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "ashby":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      case "lever":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "unstop":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "remoteok":
        return "bg-red-500/10 text-red-400 border-red-500/30";
      default:
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/30";
    }
  };

  return (
    <Card3DTilt maxDegree={8} scaleOnHover={1.02} className="h-full">
      <div
        className="flex flex-col justify-between h-full p-5 rounded-2xl border backdrop-blur-xl transition-all duration-300 relative group overflow-hidden shadow-lg"
        style={{
          backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)",
          borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)",
        }}
      >
        {/* Top Header: Company, Source, Score Orb */}
        <div>
          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border uppercase tracking-wider ${getSourceBadgeColor(job.source || job.ats)}`}>
                  via {job.source || job.ats || "web"}
                </span>
                {job.isInternship && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border bg-amber-500/10 text-amber-400 border-amber-500/20">
                    🌱 Early Career
                  </span>
                )}
                {job.verdict && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border bg-cyan-500/10 text-cyan-300 border-cyan-500/20">
                    {job.verdict}
                  </span>
                )}
              </div>
              <h3 className="font-bold text-base text-slate-100 group-hover:text-cyan-400 transition-colors line-clamp-1">
                {job.title}
              </h3>
              <p className="text-xs text-slate-400 font-medium line-clamp-1">{job.company}</p>
            </div>
            <ScoreOrb3D score={score} size={64} label="FIT" />
          </div>

          {/* Location & Tags */}
          <div className="flex items-center gap-2 text-xs text-slate-400 font-mono mb-4">
            <span className="line-clamp-1">📍 {job.location || "Remote / Unstated"}</span>
          </div>

          {/* Dual Score Signal Breakdown */}
          <div className="grid grid-cols-2 gap-2 p-2.5 rounded-xl bg-black/20 border border-white/5 font-mono text-[11px] mb-4">
            <div>
              <span className="text-slate-400 text-[9px] block">Deterministic Fit</span>
              <span className="font-bold text-emerald-400">{relevance}%</span>
            </div>
            <div>
              <span className="text-slate-400 text-[9px] block">ML Match Prob</span>
              <span className="font-bold text-cyan-400">{prediction}%</span>
            </div>
          </div>

          {/* Explainable Reasons */}
          {job.reasons && job.reasons.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-4">
              {job.reasons.slice(0, 3).map((r, i) => (
                <span
                  key={i}
                  className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-white/5 border border-white/10 text-slate-300"
                >
                  ✓ {r}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-3 border-t border-white/10 gap-2 mt-2">
          <Link
            href={`/jobs/${encodeURIComponent(job.url)}`}
            className="text-xs font-mono text-cyan-400 hover:text-cyan-300 underline underline-offset-4"
          >
            Details & Score →
          </Link>
          <div className="flex items-center gap-2">
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 rounded-lg text-xs font-mono border border-white/10 text-slate-300 hover:bg-white/10 transition-colors"
            >
              Open ATS ↗
            </a>
            <button
              onClick={() => onTailorClick ? onTailorClick(job) : null}
              className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-cyan-500 hover:bg-cyan-400 text-black shadow-md hover:shadow-cyan-500/30 transition-all"
            >
              Tailor & Prep
            </button>
          </div>
        </div>
      </div>
    </Card3DTilt>
  );
};

export default JobCard3D;
