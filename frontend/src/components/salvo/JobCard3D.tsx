"use client";

import React from "react";
import Link from "next/link";
import Card3DTilt from "@/components/3d/Card3DTilt";
import ScoreOrb3D from "./ScoreOrb3D";
import { SalvoJob } from "@/lib/salvoClient";

interface JobCard3DProps {
  job: SalvoJob;
  onTailorClick?: (job: SalvoJob) => void;
}

export const JobCard3D: React.FC<JobCard3DProps> = ({ job, onTailorClick }) => {
  const score = job.combinedScore ?? (job.score ? Math.round((job.score / 5) * 100) : 75);
  const relevance = job.relevanceScore ?? score;
  const prediction = job.predictionScore ?? score;

  const getSourceBadgeColor = (src?: string) => {
    switch ((src || "").toLowerCase()) {
      case "greenhouse":
        return "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/30";
      case "ashby":
        return "bg-purple-50 dark:bg-purple-500/10 text-purple-800 dark:text-purple-300 border-purple-300 dark:border-purple-500/30";
      case "lever":
        return "bg-blue-50 dark:bg-blue-500/10 text-blue-800 dark:text-blue-300 border-blue-300 dark:border-blue-500/30";
      case "unstop":
        return "bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-500/30";
      case "remoteok":
        return "bg-rose-50 dark:bg-rose-500/10 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-500/30";
      default:
        return "bg-cyan-50 dark:bg-cyan-500/10 text-cyan-800 dark:text-cyan-300 border-cyan-300 dark:border-cyan-500/30";
    }
  };

  return (
    <Card3DTilt maxDegree={8} scaleOnHover={1.02} className="h-full">
      <div className="flex flex-col justify-between h-full p-6 rounded-3xl border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-slate-900/90 backdrop-blur-xl transition-all duration-300 relative group overflow-hidden shadow-md hover:shadow-xl">
        {/* Top Header: Company, Source, Score Orb */}
        <div>
          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 mb-2 flex-wrap">
                <span className={`text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border uppercase tracking-wider ${getSourceBadgeColor(job.source || job.ats)}`}>
                  via {job.source || job.ats || "web"}
                </span>
                {job.isInternship && (
                  <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-500/30">
                    🌱 Early Career
                  </span>
                )}
                {job.verdict && (
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border bg-cyan-50 dark:bg-cyan-500/10 text-cyan-800 dark:text-cyan-300 border-cyan-200 dark:border-cyan-500/30">
                    {job.verdict}
                  </span>
                )}
              </div>
              <h3 className="font-bold text-base text-slate-900 dark:text-white group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition-colors line-clamp-1 leading-snug">
                {job.title}
              </h3>
              <p className="text-xs text-slate-700 dark:text-slate-300 font-semibold line-clamp-1 mt-0.5">
                {job.company}
              </p>
            </div>
            <ScoreOrb3D score={score} size={64} label="FIT" />
          </div>

          {/* Location & Tags */}
          <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400 font-mono mb-4">
            <span className="line-clamp-1">📍 {job.location || "Remote / Unstated"}</span>
          </div>

          {/* Dual Score Signal Breakdown */}
          <div className="grid grid-cols-2 gap-2 p-3 rounded-2xl bg-slate-50 dark:bg-black/30 border border-slate-200/80 dark:border-white/10 font-mono text-[11px] mb-4">
            <div>
              <span className="text-slate-500 dark:text-slate-400 text-[9px] block uppercase font-bold tracking-wider">
                Rule Fit
              </span>
              <span className="font-black text-emerald-600 dark:text-emerald-400 text-sm">
                {relevance}%
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400 text-[9px] block uppercase font-bold tracking-wider">
                ML Prob
              </span>
              <span className="font-black text-cyan-600 dark:text-cyan-400 text-sm">
                {prediction}%
              </span>
            </div>
          </div>

          {/* Explainable Reasons */}
          {job.reasons && job.reasons.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-4">
              {job.reasons.slice(0, 3).map((r, i) => (
                <span
                  key={i}
                  className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-500/20 text-emerald-800 dark:text-emerald-300"
                >
                  ✓ {r}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-200 dark:border-white/10 gap-2 mt-2">
          <Link
            href={`/jobs/detail?url=${encodeURIComponent(job.url)}`}
            className="text-xs font-mono font-bold text-cyan-600 dark:text-cyan-400 hover:text-cyan-700 dark:hover:text-cyan-300 underline underline-offset-4"
          >
            Details & Score →
          </Link>
          <div className="flex items-center gap-2">
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 rounded-xl text-xs font-mono font-medium border border-slate-300 dark:border-white/10 text-slate-700 dark:text-slate-300 bg-slate-100/80 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 transition-colors"
            >
              Open ATS ↗
            </a>
            <button
              onClick={() => (onTailorClick ? onTailorClick(job) : null)}
              className="px-3.5 py-1.5 rounded-xl text-xs font-mono font-bold bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-md hover:shadow-cyan-500/30 transition-all hover:scale-105"
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
