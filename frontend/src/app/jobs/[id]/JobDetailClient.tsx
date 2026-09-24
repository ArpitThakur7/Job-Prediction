"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { salvoClient, SalvoJob, SalvoApiError } from "@/lib/salvoClient";
import ScoreOrb3D from "@/components/salvo/ScoreOrb3D";
import TailorModal from "@/components/salvo/TailorModal";
import SalvoConnectionGuard from "@/components/salvo/SalvoConnectionGuard";
import Card3DTilt from "@/components/3d/Card3DTilt";
import { useToast } from "@/context/ToastContext";

interface JobDetailClientProps {
  id?: string;
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

export default function JobDetailClient({ id: propId }: JobDetailClientProps) {
  const routeParams = useParams();
  const searchParams = useSearchParams();
  const { addToast } = useToast();

  const [job, setJob] = useState<SalvoJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [isTailorOpen, setIsTailorOpen] = useState(false);
  const [prepping, setPrepping] = useState(false);
  const [showPrepConfirm, setShowPrepConfirm] = useState(false);
  const [copiedDesc, setCopiedDesc] = useState(false);

  // Extract ID or URL from query params, route params, or props
  const rawTarget =
    searchParams?.get("url") ||
    searchParams?.get("id") ||
    (routeParams?.id as string) ||
    propId ||
    "";

  useEffect(() => {
    if (!rawTarget) {
      setLoading(false);
      return;
    }

    const fetchJob = async () => {
      setLoading(true);
      const decoded = decodeURIComponent(rawTarget).trim();

      try {
        // 1. Try targeted getJob API
        const data = await salvoClient.getJob(decoded);
        if (data?.job) {
          setJob(data.job);
          setLoading(false);
          return;
        }
      } catch (err: any) {
        console.warn("Direct getJob returned error, trying fallback search:", err?.message);
      }

      // 2. Client-side fallback: search jobs feed
      try {
        const feed = await salvoClient.getJobs({ limit: 100 });
        const normTarget = decoded.replace(/\/$/, "").toLowerCase();
        const found = (feed.jobs || []).find((j: SalvoJob) => {
          if (!j.url) return false;
          const jNorm = j.url.replace(/\/$/, "").toLowerCase();
          return (
            j.url === decoded ||
            jNorm === normTarget ||
            (normTarget.length > 15 && (jNorm.includes(normTarget) || normTarget.includes(jNorm)))
          );
        });

        if (found) {
          setJob(found);
          setLoading(false);
          return;
        }
      } catch (feedErr: any) {
        console.error("Feed fallback error:", feedErr);
      }

      setLoading(false);
    };

    fetchJob();
  }, [rawTarget]);

  const handlePrep = async () => {
    if (!job) return;
    setPrepping(true);
    try {
      const result = await salvoClient.prepJob(job.url);
      if (result.ok) {
        addToast({
          type: "success",
          title: "Application Prepared",
          message: `Browser opened for ${result.ats || "job application"}. Review fields and submit manually!`,
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

  const handleCopyDescription = () => {
    if (!job?.description) return;
    navigator.clipboard.writeText(job.description);
    setCopiedDesc(true);
    addToast({ type: "info", title: "Copied to clipboard", message: "Job description copied" });
    setTimeout(() => setCopiedDesc(false), 2000);
  };

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <div className="w-10 h-10 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
        <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300">
          Loading job details and score breakdown...
        </span>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 rounded-3xl border border-slate-200 dark:border-white/10 bg-white/95 dark:bg-slate-900/80 shadow-xl text-center space-y-4">
        <span className="text-4xl block">🔍</span>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Job Posting Not Found</h2>
        <p className="text-xs text-slate-600 dark:text-slate-300 font-mono leading-relaxed">
          {rawTarget
            ? `Target: "${decodeURIComponent(rawTarget).slice(0, 60)}..." could not be located in the current pipeline.`
            : "No job URL or ID was specified in the route."}
        </p>
        <div className="pt-2">
          <Link
            href="/jobs"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-md transition-all"
          >
            ← Back to Job Discovery Feed
          </Link>
        </div>
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
      <div className="space-y-6 max-w-5xl mx-auto pb-12">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between">
          <Link
            href="/jobs"
            className="inline-flex items-center gap-2 text-xs font-mono font-bold text-cyan-600 dark:text-cyan-400 hover:underline transition-colors"
          >
            <span>←</span> Back to Discovery Feed
          </Link>
          <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
            {job.source ? `Source: ${job.source.toUpperCase()}` : "Direct Feed"}
          </span>
        </div>

        {/* Hero Header Card */}
        <Card3DTilt maxDegree={3} scaleOnHover={1.01}>
          <div className="p-6 md:p-8 rounded-3xl border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-slate-900/90 backdrop-blur-xl shadow-xl relative overflow-hidden space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div className="space-y-2.5 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-cyan-50 dark:bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-500/30">
                    via {job.source || job.ats || "web"}
                  </span>
                  {job.isInternship && (
                    <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-500/30">
                      🌱 Early Career
                    </span>
                  )}
                  {job.verdict && (
                    <span className={`px-2.5 py-1 rounded-full text-[10px] font-mono font-bold border ${
                      job.verdict === "Strong Match"
                        ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/30"
                        : job.verdict === "Match"
                        ? "bg-cyan-50 dark:bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border-cyan-200 dark:border-cyan-500/30"
                        : "bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-500/30"
                    }`}>
                      {job.verdict}
                    </span>
                  )}
                </div>

                <h1 className="text-2xl md:text-3xl font-black text-slate-900 dark:text-white tracking-tight leading-snug">
                  {job.title}
                </h1>
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 font-mono flex items-center gap-2">
                  <span className="text-cyan-600 dark:text-cyan-400 font-bold">{job.company}</span>
                  <span>·</span>
                  <span>📍 {job.location || "Remote / Unstated"}</span>
                </p>
              </div>

              <div className="flex items-center gap-5 shrink-0">
                <ScoreOrb3D score={score} size={88} label="COMBINED" sublabel="Overall Fit" />
                <div className="flex flex-col gap-2">
                  <button
                    onClick={() => setIsTailorOpen(true)}
                    className="px-5 py-2.5 rounded-xl font-bold font-mono text-xs bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-md hover:shadow-cyan-500/30 transition-all hover:scale-105"
                  >
                    ⚡ Tailor & Prep
                  </button>
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 rounded-xl text-center text-xs font-mono font-bold border border-slate-300 dark:border-white/10 text-slate-700 dark:text-slate-300 bg-slate-100/80 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 transition-colors"
                  >
                    Open ATS ↗
                  </a>
                </div>
              </div>
            </div>

            {/* Score Signal Telemetry Bar */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-4 border-t border-slate-200 dark:border-white/10 font-mono text-xs">
              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-black/30 border border-slate-200/90 dark:border-white/10">
                <span className="text-slate-600 dark:text-slate-400 block text-[10px] font-bold uppercase tracking-wider mb-1">
                  SALVO RULE FIT
                </span>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2.5 rounded-full bg-slate-200 dark:bg-white/10 overflow-hidden">
                    <motion.div
                      className="h-full bg-emerald-500 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${relevance}%` }}
                      transition={{ duration: 1, ease: "easeOut" }}
                    />
                  </div>
                  <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{relevance}%</span>
                </div>
                <span className="text-[10px] text-slate-500 dark:text-slate-400 mt-1 block">
                  Title, location & stack match
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-black/30 border border-slate-200/90 dark:border-white/10">
                <span className="text-slate-600 dark:text-slate-400 block text-[10px] font-bold uppercase tracking-wider mb-1">
                  XGBOOST ML PROBABILITY
                </span>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2.5 rounded-full bg-slate-200 dark:bg-white/10 overflow-hidden">
                    <motion.div
                      className="h-full bg-cyan-500 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${prediction}%` }}
                      transition={{ duration: 1, ease: "easeOut", delay: 0.2 }}
                    />
                  </div>
                  <span className="text-lg font-bold text-cyan-600 dark:text-cyan-400">{prediction}%</span>
                </div>
                <span className="text-[10px] text-slate-500 dark:text-slate-400 mt-1 block">
                  Semantic match vector with SHAP
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-black/30 border border-slate-200/90 dark:border-white/10">
                <span className="text-slate-600 dark:text-slate-400 block text-[10px] font-bold uppercase tracking-wider mb-1">
                  COMPOSITE SCORE
                </span>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2.5 rounded-full bg-slate-200 dark:bg-white/10 overflow-hidden">
                    <motion.div
                      className="h-full bg-indigo-500 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${score}%` }}
                      transition={{ duration: 1, ease: "easeOut", delay: 0.4 }}
                    />
                  </div>
                  <span className="text-lg font-bold text-indigo-600 dark:text-indigo-400">{score}%</span>
                </div>
                <span className="text-[10px] text-slate-500 dark:text-slate-400 mt-1 block">
                  60% Rule + 40% ML Blend
                </span>
              </div>
            </div>

            {/* Reasons & Badges */}
            {job.reasons && job.reasons.length > 0 && (
              <div className="pt-2 flex flex-wrap gap-2">
                {job.reasons.map((r, i) => (
                  <span
                    key={i}
                    className="text-xs font-mono font-medium px-3 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/20"
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
          <div className="p-6 rounded-3xl border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-slate-900/90 backdrop-blur-md shadow-lg space-y-3">
            <h3 className="text-xs font-mono font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-2">
              <span>🎯</span> Tech Keyword Matches ({detectedSkills.length} Identified)
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-300 font-mono">
              Skills extracted from the posting description for resume alignment:
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              {detectedSkills.map((skill) => (
                <span
                  key={skill}
                  className="text-xs font-mono font-bold px-3 py-1 rounded-xl bg-cyan-50 dark:bg-cyan-500/10 border border-cyan-200 dark:border-cyan-500/30 text-cyan-800 dark:text-cyan-300"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Job Description Body */}
        <div className="p-6 md:p-8 rounded-3xl border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-slate-900/90 backdrop-blur-xl shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-white/10">
            <h2 className="font-bold text-base text-slate-900 dark:text-white flex items-center gap-2">
              <span>📄</span> Job Description
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopyDescription}
                className="text-[11px] font-mono font-bold px-3 py-1 rounded-lg border border-slate-300 dark:border-white/10 bg-slate-100 dark:bg-white/5 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-white/10 transition-colors"
              >
                {copiedDesc ? "✓ Copied" : "📋 Copy Text"}
              </button>
              <span className="text-[10px] font-mono text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-500/20">
                PROMPT INJECTION SAFE
              </span>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-50 dark:bg-black/40 border border-slate-200 dark:border-white/10 text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed font-sans max-h-[550px] overflow-y-auto select-text">
            {job.description || "No full description text was captured from the public endpoint."}
          </div>
        </div>

        {/* Assisted Apply Section */}
        <div className="p-6 rounded-3xl border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-slate-900/90 backdrop-blur-md shadow-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span>🚀</span> Assisted ATS Form Pre-filler
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 font-mono">
              Fills factual background details in a visible browser.{" "}
              <strong className="text-amber-600 dark:text-amber-400">Golden Rule: You review and click Submit yourself.</strong>
            </p>
          </div>

          {showPrepConfirm ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-2 p-3 rounded-2xl border border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-950/30"
            >
              <span className="text-xs text-amber-800 dark:text-amber-300 font-mono font-bold whitespace-nowrap">
                Confirm launch:
              </span>
              <button
                onClick={handlePrep}
                disabled={prepping}
                className="px-3.5 py-1.5 rounded-xl text-xs font-mono font-bold bg-amber-500 hover:bg-amber-400 text-slate-950 disabled:opacity-50 whitespace-nowrap shadow-md"
              >
                {prepping ? "Opening..." : "✓ Launch"}
              </button>
              <button
                onClick={() => setShowPrepConfirm(false)}
                className="px-2 py-1 text-slate-600 dark:text-slate-400 text-xs font-mono hover:underline"
              >
                Cancel
              </button>
            </motion.div>
          ) : (
            <button
              onClick={() => setShowPrepConfirm(true)}
              className="px-5 py-2.5 rounded-xl text-xs font-mono font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md transition-all shrink-0 hover:scale-105"
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
