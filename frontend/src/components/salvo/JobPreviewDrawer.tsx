"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { Calendar, Copy, ExternalLink, MapPin, Star, X } from "lucide-react";
import { SalvoJob } from "@/lib/salvoClient";
import { fitColor, fitLabel, isEarlyCareer, isRemote, jobScore, jobSource } from "@/lib/jobScore";
import ScoreOrb3D from "./ScoreOrb3D";

interface JobPreviewDrawerProps {
  job: SalvoJob | null;
  isOpen: boolean;
  onClose: () => void;
  onTailorClick?: (job: SalvoJob) => void;
  onApplyClick?: (job: SalvoJob) => void;
  onToggleSave?: (job: SalvoJob) => void;
  isSaved?: boolean;
}

export const JobPreviewDrawer: React.FC<JobPreviewDrawerProps> = ({
  job,
  isOpen,
  onClose,
  onTailorClick,
  onApplyClick,
  onToggleSave,
  isSaved = false,
}) => {
  const [copied, setCopied] = useState<"" | "link" | "desc">("");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", onKey);
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [isOpen, onClose]);

  const copy = async (what: "link" | "desc", text?: string) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(what);
      setTimeout(() => setCopied(""), 1800);
    } catch {}
  };

  return (
    <AnimatePresence>
      {isOpen && job && (
        <div className="fixed inset-0 z-[60] flex justify-end" role="dialog" aria-modal="true" aria-label={job.title}>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-[#1b1640]/35 backdrop-blur-[6px]"
          />

          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 32, stiffness: 320 }}
            className="glass-strong relative w-full max-w-[640px] h-full flex flex-col sm:rounded-l-[32px] overflow-hidden"
          >
            <header className="p-6 pb-5 flex items-start gap-4">
              <div className="flex-1 min-w-0 space-y-2">
                <h2 className="font-display text-2xl font-bold leading-tight">{job.title}</h2>
                <p className="font-semibold">{job.company}</p>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm" style={{ color: "var(--theme-text-muted)" }}>
                  <span className="inline-flex items-center gap-1">
                    <MapPin size={14} /> {job.location || "Location not listed"}
                  </span>
                  {job.postedAt && (
                    <span className="inline-flex items-center gap-1">
                      <Calendar size={14} /> Posted {new Date(job.postedAt).toLocaleDateString()}
                    </span>
                  )}
                  <span className="capitalize">via {jobSource(job).replace(/-/g, " ")}</span>
                </div>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {isRemote(job) && <Pill>Remote</Pill>}
                  {isEarlyCareer(job) && <Pill>Early career</Pill>}
                  {job.verdict && <Pill>{job.verdict}</Pill>}
                </div>
              </div>
              <div className="flex items-center gap-1">
                {onToggleSave && (
                  <button
                    onClick={() => onToggleSave(job)}
                    className="p-2.5 rounded-xl hover:bg-black/5 dark:hover:bg-white/10"
                    aria-label={isSaved ? "Remove from saved" : "Save job"}
                    title={isSaved ? "Remove from saved" : "Save job"}
                  >
                    <Star size={18} fill={isSaved ? "#F5B83D" : "none"} color={isSaved ? "#E9A23B" : "currentColor"} />
                  </button>
                )}
                <button onClick={onClose} className="p-2.5 rounded-xl hover:bg-black/5 dark:hover:bg-white/10" aria-label="Close (Esc)" title="Close (Esc)">
                  <X size={18} />
                </button>
              </div>
            </header>

            <div className="flex-1 overflow-y-auto px-6 pb-6 space-y-6">
              <FitBreakdown job={job} />

              {job.reasons && job.reasons.length > 0 && (
                <section className="space-y-2">
                  <h3 className="font-semibold">Why it matched</h3>
                  <ul className="flex flex-wrap gap-2">
                    {job.reasons.map((r, i) => (
                      <li key={i} className="text-sm px-3 py-1 rounded-xl bg-black/[0.04] dark:bg-white/[0.06]">
                        {r}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <section className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">Description</h3>
                  <div className="flex gap-1 text-sm">
                    <button onClick={() => copy("link", job.url)} className="px-2.5 py-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 inline-flex items-center gap-1.5">
                      <Copy size={13} /> {copied === "link" ? "Copied" : "Copy link"}
                    </button>
                    {job.description && (
                      <button onClick={() => copy("desc", job.description)} className="px-2.5 py-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 inline-flex items-center gap-1.5">
                        <Copy size={13} /> {copied === "desc" ? "Copied" : "Copy text"}
                      </button>
                    )}
                  </div>
                </div>
                <div className="rounded-2xl p-5 bg-white/60 dark:bg-black/20 text-[15px] leading-relaxed whitespace-pre-wrap max-w-[68ch]">
                  {job.description || "This posting's full text wasn't captured. Open the original post to read it."}
                </div>
              </section>

              <Link href={`/jobs/detail?url=${encodeURIComponent(job.url)}`} className="inline-block text-sm font-semibold" style={{ color: "var(--theme-primary)" }}>
                Open the full job page
              </Link>
            </div>

            <footer className="px-6 py-4 flex items-center gap-2 border-t" style={{ borderColor: "var(--glass-line)" }}>
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold hover:bg-black/5 dark:hover:bg-white/10"
              >
                <ExternalLink size={15} /> Original post
              </a>
              <span className="flex-1" />
              <button
                onClick={() => {
                  onClose();
                  onTailorClick?.(job);
                }}
                className="px-4 py-2.5 rounded-xl text-sm font-semibold hover:bg-black/5 dark:hover:bg-white/10"
              >
                Tailor resume
              </button>
              <button
                onClick={() => {
                  onClose();
                  onApplyClick?.(job);
                }}
                className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white"
                style={{ background: "var(--theme-primary)" }}
              >
                Apply
              </button>
            </footer>
          </motion.aside>
        </div>
      )}
    </AnimatePresence>
  );
};

/** Shows the blended score and the two signals behind it. Never fills in a missing model score. */
function FitBreakdown({ job }: { job: SalvoJob }) {
  const score = jobScore(job);
  const relevance = job.relevanceScore ?? (typeof job.score === "number" ? Math.round((job.score / 5) * 100) : null);
  const prediction = typeof job.predictionScore === "number" ? job.predictionScore : null;

  return (
    <section className="rounded-[24px] p-5 bg-white/55 dark:bg-white/[0.04] border flex flex-col sm:flex-row gap-5 items-center" style={{ borderColor: "var(--glass-line)" }}>
      <div className="flex flex-col items-center gap-1 shrink-0">
        <ScoreOrb3D score={score} size={92} label="fit" />
        <span className="text-sm font-semibold" style={{ color: fitColor(score) }}>{fitLabel(score)}</span>
      </div>
      <div className="flex-1 w-full space-y-4">
        <Bar label="Your rules" hint="Title, stack and location match" value={relevance} />
        <Bar
          label={job.predictionSource === "model" || prediction === null ? "Prediction model" : "Keyword estimate"}
          hint={
            prediction === null
              ? "Not scored. Start the prediction API to add this signal."
              : job.predictionSource === "model"
              ? "The trained model's estimate that this job matches your resume"
              : "Scored while the prediction API was offline. Rescan with it running for a model score."
          }
          value={prediction}
        />
      </div>
    </section>
  );
}

function Bar({ label, hint, value }: { label: string; hint: string; value: number | null }) {
  return (
    <div>
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-semibold">{label}</span>
        <span className="font-bold tabular" style={{ color: value === null ? "var(--theme-text-muted)" : fitColor(value) }}>
          {value === null ? "—" : `${value}%`}
        </span>
      </div>
      <div className="h-2 rounded-full bg-black/[0.06] dark:bg-white/10 overflow-hidden mt-1.5">
        {value !== null && <div className="h-full rounded-full" style={{ width: `${value}%`, background: fitColor(value) }} />}
      </div>
      <p className="text-xs mt-1" style={{ color: "var(--theme-text-muted)" }}>{hint}</p>
    </div>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ background: "var(--theme-badge-bg)", color: "var(--theme-badge-text)" }}>
      {children}
    </span>
  );
}

export default JobPreviewDrawer;
