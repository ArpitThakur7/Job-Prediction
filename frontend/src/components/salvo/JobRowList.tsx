"use client";

import React from "react";
import Link from "next/link";
import { SalvoJob } from "@/lib/salvoClient";

interface JobRowListProps {
  jobs: SalvoJob[];
  onSelectJob: (job: SalvoJob) => void;
  onTailorClick: (job: SalvoJob) => void;
  onApplyClick?: (job: SalvoJob) => void;
  onToggleSave: (job: SalvoJob) => void;
  savedUrls: Set<string>;
}

export const JobRowList: React.FC<JobRowListProps> = ({
  jobs,
  onSelectJob,
  onTailorClick,
  onApplyClick,
  onToggleSave,
  savedUrls,
}) => {
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

  const getCompanyInitials = (name?: string) => {
    if (!name) return "CO";
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <div className="space-y-3">
      {jobs.map((job) => {
        const score = job.combinedScore ?? (job.score ? Math.round((job.score / 5) * 100) : 75);
        const isSaved = savedUrls.has(job.url);

        return (
          <div
            key={job.url}
            onClick={() => onSelectJob(job)}
            className="group p-4 md:p-5 rounded-2xl border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-slate-900/90 hover:bg-slate-50/90 dark:hover:bg-slate-800/80 backdrop-blur-xl shadow-xs hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4"
          >
            {/* Left: Avatar + Title & Meta */}
            <div className="flex items-start md:items-center gap-3.5 flex-1 min-w-0">
              <div className="w-11 h-11 shrink-0 rounded-2xl bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border border-cyan-500/30 text-cyan-700 dark:text-cyan-300 font-mono font-bold flex items-center justify-center text-sm shadow-xs">
                {getCompanyInitials(job.company)}
              </div>

              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-bold text-sm md:text-base text-slate-900 dark:text-white group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition-colors line-clamp-1">
                    {job.title}
                  </h3>
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${getSourceBadgeColor(job.source || job.ats)}`}>
                    {job.source || job.ats || "web"}
                  </span>
                  {job.isInternship && (
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-500/30">
                      Early Career
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3 text-xs font-mono text-slate-600 dark:text-slate-400 flex-wrap">
                  <span className="font-semibold text-slate-800 dark:text-slate-200">{job.company}</span>
                  <span>•</span>
                  <span>📍 {job.location || "Remote / Worldwide"}</span>
                  {job.postedAt && (
                    <>
                      <span>•</span>
                      <span>🕒 {new Date(job.postedAt).toLocaleDateString()}</span>
                    </>
                  )}
                  {job.reasons && job.reasons.length > 0 && (
                    <span className="hidden lg:inline-flex text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
                      ✓ {job.reasons[0]}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Right: Scores + Actions */}
            <div
              className="flex items-center justify-between md:justify-end gap-3 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100 dark:border-white/5"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Fit Score Pill */}
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-black/30 border border-slate-200 dark:border-white/10 font-mono text-xs">
                <span className="text-[10px] text-slate-500 uppercase font-bold">Fit</span>
                <span
                  className={`font-black text-sm ${
                    score >= 80
                      ? "text-emerald-600 dark:text-emerald-400"
                      : score >= 60
                      ? "text-cyan-600 dark:text-cyan-400"
                      : "text-amber-600 dark:text-amber-400"
                  }`}
                >
                  {score}%
                </span>
              </div>

              {/* Bookmark Button */}
              <button
                onClick={() => onToggleSave(job)}
                title={isSaved ? "Remove from Saved" : "Save Job"}
                className={`p-2 rounded-xl border text-xs transition-all ${
                  isSaved
                    ? "bg-amber-500 text-slate-950 border-amber-400 font-bold"
                    : "bg-white dark:bg-slate-800 text-slate-400 hover:text-amber-500 border-slate-200 dark:border-white/10"
                }`}
              >
                {isSaved ? "⭐" : "☆"}
              </button>

              {/* Preview Button */}
              <button
                onClick={() => onSelectJob(job)}
                className="px-3 py-1.5 rounded-xl text-xs font-mono font-medium border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors shadow-2xs"
              >
                Preview 👁
              </button>

              {/* Apply Action */}
              <button
                onClick={() => (onApplyClick ? onApplyClick(job) : null)}
                className="px-3.5 py-1.5 rounded-xl text-xs font-mono font-bold bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-sm transition-transform hover:scale-105"
              >
                Apply 🚀
              </button>

              {/* ATS External Link */}
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-xl text-xs font-mono text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                title="Open original job posting"
              >
                ↗
              </a>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default JobRowList;
