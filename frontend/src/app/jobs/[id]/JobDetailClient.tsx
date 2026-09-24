"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { salvoClient, SalvoJob } from "@/lib/salvoClient";
import ScoreOrb3D from "@/components/salvo/ScoreOrb3D";
import TailorModal from "@/components/salvo/TailorModal";
import { useApp } from "@/context/AppContext";

interface JobDetailClientProps {
  id: string;
}

export default function JobDetailClient({ id }: JobDetailClientProps) {
  const { currentThemeColors } = useApp();
  const [job, setJob] = useState<SalvoJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [isTailorOpen, setIsTailorOpen] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchJob = async () => {
      setLoading(true);
      try {
        const decoded = decodeURIComponent(id);
        const data = await salvoClient.getJob(decoded);
        setJob(data.job || null);
      } catch (err) {
        console.error("Failed to load job details", err);
      } finally {
        setLoading(false);
      }
    };
    fetchJob();
  }, [id]);

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <div className="w-10 h-10 border-4 border-cyan-500/20 border-t-cyan-400 rounded-full animate-spin" />
        <span className="text-xs font-mono text-slate-400">Loading job details and score breakdown...</span>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="p-12 text-center space-y-3">
        <h2 className="text-xl font-bold text-slate-200">Job posting not found</h2>
        <Link href="/jobs" className="text-xs font-mono text-cyan-400 underline">
          ← Back to Discovery Feed
        </Link>
      </div>
    );
  }

  const score = job.combinedScore ?? (job.score ? Math.round((job.score / 5) * 100) : 75);
  const relevance = job.relevanceScore ?? score;
  const prediction = job.predictionScore ?? score;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Back button */}
      <div>
        <Link
          href="/jobs"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-cyan-400 transition-colors"
        >
          ← Back to Discovery Feed
        </Link>
      </div>

      {/* Hero Header Card */}
      <div
        className="p-6 md:p-8 rounded-3xl border backdrop-blur-xl shadow-xl relative overflow-hidden"
        style={{
          backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)",
          borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)",
        }}
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono border bg-cyan-500/10 text-cyan-300 border-cyan-500/30 uppercase">
                via {job.source || job.ats || "web"}
              </span>
              {job.isInternship && (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono border bg-amber-500/10 text-amber-300 border-amber-500/30">
                  🌱 Early Career
                </span>
              )}
              {job.verdict && (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono border bg-emerald-500/10 text-emerald-300 border-emerald-500/30">
                  {job.verdict}
                </span>
              )}
            </div>
            <h1 className="text-2xl md:text-3xl font-black text-slate-100">{job.title}</h1>
            <p className="text-sm font-medium text-slate-400 font-mono">
              {job.company} · 📍 {job.location || "Remote / Unstated"}
            </p>
          </div>

          <div className="flex items-center gap-6">
            <ScoreOrb3D score={score} size={88} label="COMBINED" sublabel="Overall Fit" />
            <div className="flex flex-col gap-2">
              <button
                onClick={() => setIsTailorOpen(true)}
                className="px-5 py-2.5 rounded-xl font-bold font-mono text-xs bg-cyan-500 hover:bg-cyan-400 text-black shadow-[0_0_20px_rgba(6,182,212,0.4)] transition-all hover:scale-105"
              >
                Tailor & Prep Application
              </button>
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 rounded-xl text-center text-xs font-mono border border-white/10 text-slate-300 hover:bg-white/10 transition-colors"
              >
                Open Official ATS Posting ↗
              </a>
            </div>
          </div>
        </div>

        {/* Score Signal Telemetry Bar */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-6 pt-6 border-t border-white/10 font-mono text-xs">
          <div className="p-3.5 rounded-xl bg-black/20 border border-white/5">
            <span className="text-slate-400 block text-[10px] mb-1">SALVO DETERMINISTIC FIT</span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold text-emerald-400">{relevance}%</span>
              <span className="text-[10px] text-slate-400">Rule-based keywords & gates</span>
            </div>
          </div>
          <div className="p-3.5 rounded-xl bg-black/20 border border-white/5">
            <span className="text-slate-400 block text-[10px] mb-1">XGBOOST ML PREDICTION</span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold text-cyan-400">{prediction}%</span>
              <span className="text-[10px] text-slate-400">9-feature semantic model</span>
            </div>
          </div>
          <div className="p-3.5 rounded-xl bg-black/20 border border-white/5">
            <span className="text-slate-400 block text-[10px] mb-1">BLENDED WEIGHT RATIO</span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold text-purple-400">60% / 40%</span>
              <span className="text-[10px] text-slate-400">Relevance / ML Match</span>
            </div>
          </div>
        </div>

        {/* Reasons & Badges */}
        {job.reasons && job.reasons.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {job.reasons.map((r, i) => (
              <span
                key={i}
                className="text-xs font-mono px-3 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
              >
                ✓ {r}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Job Description Body */}
      <div
        className="p-6 md:p-8 rounded-3xl border backdrop-blur-xl shadow-xl space-y-4"
        style={{
          backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)",
          borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)",
        }}
      >
        <div className="flex items-center justify-between pb-3 border-b border-white/10">
          <h2 className="font-bold text-base text-slate-200 flex items-center gap-2">
            <span>📄</span> Original Job Description
          </h2>
          <span className="text-[10px] font-mono text-slate-400 bg-white/5 px-2 py-0.5 rounded border border-white/10">
            PROMPT INJECTION ISOLATED
          </span>
        </div>

        <div className="prose prose-invert max-w-none text-xs md:text-sm text-slate-300 whitespace-pre-wrap leading-relaxed font-sans font-normal opacity-90">
          {job.description || "No full description text was captured from the public endpoint."}
        </div>
      </div>

      <TailorModal
        job={job}
        isOpen={isTailorOpen}
        onClose={() => setIsTailorOpen(false)}
      />
    </div>
  );
}
