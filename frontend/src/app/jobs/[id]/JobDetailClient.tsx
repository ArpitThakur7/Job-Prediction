"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { salvoClient, SalvoJob, SalvoApiError, TailorResult } from "@/lib/salvoClient";
import ScoreOrb3D from "@/components/salvo/ScoreOrb3D";
import TailorModal from "@/components/salvo/TailorModal";
import SalvoConnectionGuard from "@/components/salvo/SalvoConnectionGuard";
import Card3DTilt from "@/components/3d/Card3DTilt";
import { useApp } from "@/context/AppContext";
import { useToast } from "@/context/ToastContext";

interface JobDetailClientProps {
  id: string;
}

// Common tech keywords for gap analysis
const COMMON_SKILLS = [
  "react", "node", "typescript", "python", "javascript", "nextjs", "next.js",
  "docker", "kubernetes", "aws", "gcp", "azure", "graphql", "rest",
  "postgresql", "mongodb", "redis", "tailwind", "css", "html",
  "git", "ci/cd", "agile", "java", "go", "rust", "c++", "sql",
  "fastapi", "django", "flask", "express", "vue", "angular", "svelte",
  "tensorflow", "pytorch", "machine learning", "ai", "llm",
  "kafka", "rabbitmq", "elasticsearch", "nginx", "linux",
];

export default function JobDetailClient({ id }: JobDetailClientProps) {
  const { currentThemeColors } = useApp();
  const { addToast } = useToast();
  const [job, setJob] = useState<SalvoJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [isTailorOpen, setIsTailorOpen] = useState(false);
  const [prepping, setPrepping] = useState(false);
  const [showPrepConfirm, setShowPrepConfirm] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchJob = async () => {
      setLoading(true);
      try {
        const decoded = decodeURIComponent(id);
        const data = await salvoClient.getJob(decoded);
        setJob(data.job || null);
      } catch (err: any) {
        if (!(err instanceof SalvoApiError && err.isOffline)) {
          addToast({ type: "error", title: "Failed to load job", message: err.message });
        }
      } finally {
        setLoading(false);
      }
    };
    fetchJob();
  }, [id]);

  const handlePrep = async () => {
    if (!job) return;
    setPrepping(true);
    try {
      const result = await salvoClient.prepJob(job.url);
      if (result.ok) {
        addToast({
          type: "success",
          title: "Application Prepared",
          message: `Browser opened for ${result.ats}. Complete custom questions and submit yourself!`,
          duration: 8000,
        });
      }
    } catch (err: any) {
      if (err instanceof SalvoApiError && err.isConflict) {
        addToast({ type: "warning", title: "Excel is locked", message: err.message, duration: 6000 });
      } else {
        addToast({ type: "error", title: "Prep failed", message: err.message });
      }
    } finally {
      setPrepping(false);
      setShowPrepConfirm(false);
    }
  };

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
        <span className="text-3xl block mb-2">🔍</span>
        <h2 className="text-xl font-bold text-slate-200">Job posting not found</h2>
        <p className="text-xs text-slate-400 font-mono">This posting may not yet be scanned or has been removed.</p>
        <Link href="/jobs" className="text-xs font-mono text-cyan-400 underline">
          ← Back to Discovery Feed
        </Link>
      </div>
    );
  }

  const score = job.combinedScore ?? (job.score ? Math.round((job.score / 5) * 100) : 75);
  const relevance = job.relevanceScore ?? score;
  const prediction = job.predictionScore ?? score;

  // Keyword gap analysis
  const descLower = (job.description || "").toLowerCase();
  const titleLower = (job.title || "").toLowerCase();
  const detectedSkills = COMMON_SKILLS.filter((s) => descLower.includes(s) || titleLower.includes(s));

  return (
    <SalvoConnectionGuard>
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
        <Card3DTilt maxDegree={3} scaleOnHover={1.01}>
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
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono border ${
                      job.verdict === "Strong Match"
                        ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                        : job.verdict === "Match"
                        ? "bg-cyan-500/10 text-cyan-300 border-cyan-500/30"
                        : "bg-amber-500/10 text-amber-300 border-amber-500/30"
                    }`}>
                      {job.verdict}
                    </span>
                  )}
                </div>
                <h1 className="text-2xl md:text-3xl font-black text-slate-100">{job.title}</h1>
                <p className="text-sm font-medium text-slate-400 font-mono">
                  {job.company} · 📍 {job.location || "Remote / Unstated"}
                </p>
              </div>

              <div className="flex items-center gap-6 shrink-0">
                <ScoreOrb3D score={score} size={88} label="COMBINED" sublabel="Overall Fit" />
                <div className="flex flex-col gap-2">
                  <button
                    onClick={() => setIsTailorOpen(true)}
                    className="px-5 py-2.5 rounded-xl font-bold font-mono text-xs bg-cyan-500 hover:bg-cyan-400 text-black shadow-[0_0_20px_rgba(6,182,212,0.4)] transition-all hover:scale-105"
                  >
                    ⚡ Tailor & Prep
                  </button>
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 rounded-xl text-center text-xs font-mono border border-white/10 text-slate-300 hover:bg-white/10 transition-colors"
                  >
                    Open ATS ↗
                  </a>
                </div>
              </div>
            </div>

            {/* Score Signal Telemetry Bar */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-6 pt-6 border-t border-white/10 font-mono text-xs">
              <div className="p-3.5 rounded-xl bg-black/20 border border-white/5">
                <span className="text-slate-400 block text-[10px] mb-1">SALVO DETERMINISTIC FIT</span>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2 rounded-full bg-white/10 overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${relevance}%` }}
                      transition={{ duration: 1, ease: "easeOut" }}
                    />
                  </div>
                  <span className="text-lg font-bold text-emerald-400">{relevance}%</span>
                </div>
                <span className="text-[10px] text-slate-500">Rule-based: title, location, stack keywords</span>
              </div>
              <div className="p-3.5 rounded-xl bg-black/20 border border-white/5">
                <span className="text-slate-400 block text-[10px] mb-1">XGBOOST ML PREDICTION</span>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2 rounded-full bg-white/10 overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-cyan-500 to-cyan-400 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${prediction}%` }}
                      transition={{ duration: 1, ease: "easeOut", delay: 0.2 }}
                    />
                  </div>
                  <span className="text-lg font-bold text-cyan-400">{prediction}%</span>
                </div>
                <span className="text-[10px] text-slate-500">9-feature semantic model with SHAP</span>
              </div>
              <div className="p-3.5 rounded-xl bg-black/20 border border-white/5">
                <span className="text-slate-400 block text-[10px] mb-1">BLENDED WEIGHT RATIO</span>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2 rounded-full bg-white/10 overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-purple-500 to-violet-400 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${score}%` }}
                      transition={{ duration: 1, ease: "easeOut", delay: 0.4 }}
                    />
                  </div>
                  <span className="text-lg font-bold text-purple-400">{score}%</span>
                </div>
                <span className="text-[10px] text-slate-500">60% Relevance + 40% ML Match</span>
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
        </Card3DTilt>

        {/* Keyword Gap Analysis */}
        {detectedSkills.length > 0 && (
          <div
            className="p-5 rounded-2xl border backdrop-blur-md"
            style={{ backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)", borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)" }}
          >
            <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <span>🎯</span> Keyword Gap Analysis
            </h3>
            <p className="text-[11px] text-slate-400 font-mono mb-3">
              Tech skills detected in this posting ({detectedSkills.length} matched from {COMMON_SKILLS.length} tracked):
            </p>
            <div className="flex flex-wrap gap-2">
              {detectedSkills.map((skill) => (
                <span
                  key={skill}
                  className="text-[11px] font-mono px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

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

          <div className="prose prose-invert max-w-none text-xs md:text-sm text-slate-300 whitespace-pre-wrap leading-relaxed font-sans font-normal opacity-90 max-h-[500px] overflow-y-auto">
            {job.description || "No full description text was captured from the public endpoint."}
          </div>
        </div>

        {/* Assisted Apply Section */}
        <div
          className="p-5 rounded-2xl border backdrop-blur-md flex flex-col sm:flex-row items-center justify-between gap-4"
          style={{ backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)", borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)" }}
        >
          <div>
            <h3 className="text-sm font-bold text-slate-200 mb-1 flex items-center gap-2">
              <span>🚀</span> Assisted Form Pre-filler
            </h3>
            <p className="text-[10px] text-slate-400 font-mono">
              Opens a visible browser, fills factual fields (name, email, resume PDF). <strong className="text-amber-400">NEVER clicks Submit.</strong>
            </p>
          </div>

          {showPrepConfirm ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-2 p-3 rounded-xl border border-amber-500/30 bg-amber-950/20"
            >
              <span className="text-[10px] text-amber-400 font-mono whitespace-nowrap">Golden Rule: Never submits.</span>
              <button
                onClick={handlePrep}
                disabled={prepping}
                className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-amber-500 text-black hover:bg-amber-400 disabled:opacity-50 whitespace-nowrap"
              >
                {prepping ? "Launching..." : "✓ Confirm Launch"}
              </button>
              <button
                onClick={() => setShowPrepConfirm(false)}
                className="px-2 py-1 text-slate-400 text-xs"
              >
                Cancel
              </button>
            </motion.div>
          ) : (
            <button
              onClick={() => setShowPrepConfirm(true)}
              className="px-5 py-2.5 rounded-xl text-xs font-mono font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md transition-all shrink-0"
            >
              🚀 Launch Assisted Apply
            </button>
          )}
        </div>

        <TailorModal
          job={job}
          isOpen={isTailorOpen}
          onClose={() => setIsTailorOpen(false)}
        />
      </div>
    </SalvoConnectionGuard>
  );
}
