"use client";

import React from "react";
import { EyeOff, MapPin, Star } from "lucide-react";
import Card3DTilt from "@/components/3d/Card3DTilt";
import ScoreOrb3D from "./ScoreOrb3D";
import { SalvoJob } from "@/lib/salvoClient";
import { fitColor, fitLabel, isEarlyCareer, isRemote, jobScore, jobSource } from "@/lib/jobScore";

interface JobCard3DProps {
  job: SalvoJob;
  onTailorClick?: (job: SalvoJob) => void;
  onApplyClick?: (job: SalvoJob) => void;
  onSelect?: (job: SalvoJob) => void;
  onToggleSave?: (job: SalvoJob) => void;
  onDismiss?: (job: SalvoJob) => void;
  isSaved?: boolean;
  isDismissed?: boolean;
}

export const JobCard3D: React.FC<JobCard3DProps> = ({
  job,
  onTailorClick,
  onApplyClick,
  onSelect,
  onToggleSave,
  onDismiss,
  isSaved = false,
  isDismissed = false,
}) => {
  const score = jobScore(job);
  const relevance = job.relevanceScore ?? score;
  const prediction = job.predictionScore;

  return (
    <Card3DTilt maxDegree={5} scaleOnHover={1.015} glowColor="rgba(30,27,75,0.14)" className="h-full rounded-[28px]">
      <article
        onClick={() => onSelect?.(job)}
        className={`glass h-full rounded-[28px] p-5 flex flex-col gap-4 ${isDismissed ? "opacity-55" : ""}`}
      >
        <header className="flex gap-4 items-start">
          <ScoreOrb3D score={score} size={64} label="fit" />
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-[17px] leading-snug line-clamp-2">{job.title}</h3>
            <p className="text-sm mt-0.5 truncate" style={{ color: "var(--theme-text-muted)" }}>
              {job.company}
            </p>
            <p className="text-xs font-semibold mt-1" style={{ color: fitColor(score) }}>
              {fitLabel(score)}
            </p>
          </div>
        </header>

        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="inline-flex items-center gap-1 pr-1" style={{ color: "var(--theme-text-muted)" }}>
            <MapPin size={12} />
            <span className="truncate max-w-[12rem]">{job.location || "Location not listed"}</span>
          </span>
          {isRemote(job) && <Tag>Remote</Tag>}
          {isEarlyCareer(job) && <Tag>Early career</Tag>}
          <Tag muted>{jobSource(job).replace(/-/g, " ")}</Tag>
        </div>

        {job.reasons && job.reasons.length > 0 && (
          <ul className="flex flex-wrap gap-1.5">
            {job.reasons.slice(0, 3).map((r, i) => (
              <li key={i} className="text-xs px-2 py-1 rounded-lg bg-black/[0.04] dark:bg-white/[0.06] line-clamp-1">
                {r}
              </li>
            ))}
          </ul>
        )}

        {/* The two signals behind the fit score */}
        <div className="space-y-1.5 mt-auto">
          <Signal label="Your rules" value={relevance} />
          {typeof prediction === "number" && (
            <Signal label={job.predictionSource === "model" ? "Prediction model" : "Keyword estimate"} value={prediction} />
          )}
        </div>

        <footer className="flex items-center gap-1.5 pt-1" onClick={(e) => e.stopPropagation()}>
          {onToggleSave && (
            <IconButton label={isSaved ? "Remove from saved" : "Save job"} onClick={() => onToggleSave(job)}>
              <Star size={16} fill={isSaved ? "#F5B83D" : "none"} color={isSaved ? "#E9A23B" : "currentColor"} />
            </IconButton>
          )}
          {onDismiss && (
            <IconButton label={isDismissed ? "Restore job" : "Not for me"} onClick={() => onDismiss(job)}>
              <EyeOff size={16} />
            </IconButton>
          )}
          <span className="flex-1" />
          <button
            onClick={() => onTailorClick?.(job)}
            className="px-3.5 py-2 rounded-xl text-sm font-semibold hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
          >
            Tailor
          </button>
          <button
            onClick={() => onApplyClick?.(job)}
            className="px-4 py-2 rounded-xl text-sm font-semibold text-white transition-transform hover:-translate-y-0.5"
            style={{ background: "var(--theme-primary)" }}
          >
            Apply
          </button>
        </footer>
      </article>
    </Card3DTilt>
  );
};

function Signal({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-28 shrink-0" style={{ color: "var(--theme-text-muted)" }}>{label}</span>
      <span className="flex-1 h-1.5 rounded-full bg-black/[0.06] dark:bg-white/10 overflow-hidden">
        <span className="block h-full rounded-full" style={{ width: `${value}%`, background: fitColor(value) }} />
      </span>
      <span className="w-8 text-right font-semibold tabular">{value}</span>
    </div>
  );
}

function Tag({ children, muted = false }: { children: React.ReactNode; muted?: boolean }) {
  return (
    <span
      className="px-2 py-0.5 rounded-full font-medium capitalize"
      style={muted ? { background: "rgba(0,0,0,0.04)", color: "var(--theme-text-muted)" } : { background: "var(--theme-badge-bg)", color: "var(--theme-badge-text)" }}
    >
      {children}
    </span>
  );
}

function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} title={label} aria-label={label} className="p-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/10 transition-colors">
      {children}
    </button>
  );
}

export default JobCard3D;
