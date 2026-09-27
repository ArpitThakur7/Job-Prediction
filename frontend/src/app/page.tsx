"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { useApp } from "@/context/AppContext";
import Card3DTilt from "@/components/3d/Card3DTilt";
import SalvoDashboardWidget from "@/components/salvo/SalvoDashboardWidget";

// Dynamic non-SSR imports for Three.js 3D WebGL scenes to optimize initial paint
const Hero3DScene = dynamic(() => import("@/components/3d/Hero3DScene"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[360px] min-[821px]:h-[480px] rounded-3xl bg-indigo-500/5 border border-indigo-500/10 flex flex-col items-center justify-center animate-pulse">
      <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-3xl">
        ⚡
      </div>
      <p className="mt-4 text-xs font-mono text-indigo-500/70">Initializing Quantum 3D Visualizer...</p>
    </div>
  ),
});

const HolographicGlobe3D = dynamic(() => import("@/components/3d/HolographicGlobe3D"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[280px] rounded-2xl bg-emerald-500/5 flex items-center justify-center animate-pulse">
      <p className="text-xs font-mono text-emerald-500/60">Rendering Spatial Coordinates...</p>
    </div>
  ),
});

const Interactive3DCubeMesh = dynamic(() => import("@/components/3d/Interactive3DCubeMesh"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[140px] animate-pulse bg-sky-500/5 rounded-xl flex items-center justify-center">
      <p className="text-[10px] font-mono text-sky-500/60">Aligning Vector Hypercube...</p>
    </div>
  ),
});

interface Job {
  job_id: string;
  title: string;
  company: string;
  location: string;
  category?: string;
  required_skills: string | string[];
  salary_min: number | null;
  salary_max: number | null;
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.05,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: "easeOut" as const },
  },
};

export default function Dashboard() {
  const router = useRouter();
  const { matchResults, apiBase, currentThemeColors } = useApp();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadingJobs, setLoadingJobs] = useState<boolean>(true);

  const [stats, setStats] = useState<{
    total_resumes: number;
    total_jobs: number;
    high_affinity_matches: number;
    top_compatibility_score: string;
  }>({
    total_resumes: 31,
    total_jobs: 150,
    high_affinity_matches: 63,
    top_compatibility_score: "94.2%",
  });

  useEffect(() => {
    let isMounted = true;

    const fetchRecentJobs = async () => {
      try {
        const res = await fetch(`${apiBase}/jobs/`);
        if (res.status === 200 && isMounted) {
          const data = await res.json();
          setJobs(data || []);
        }
      } catch (err) {
        console.error("Failed to fetch jobs:", err);
      } finally {
        if (isMounted) setLoadingJobs(false);
      }
    };

    const fetchStats = async () => {
      try {
        const res = await fetch(`${apiBase}/dashboard/stats`);
        if (res.status === 200 && isMounted) {
          const body = await res.json();
          if (body?.data) {
            setStats(body.data);
          }
        }
      } catch (err) {
        console.error("Failed to fetch stats:", err);
      }
    };

    fetchRecentJobs();
    fetchStats();

    return () => {
      isMounted = false;
    };
  }, [apiBase]);

  const getTopScore = () => {
    if (!matchResults || matchResults.length === 0) return 96;
    const scores = matchResults.map((r) => {
      const val = typeof r.match_score === "string" ? r.match_score.replace("%", "") : r.match_score;
      const s = parseFloat(val);
      return isNaN(s) ? 0 : s;
    });
    const maxScore = Math.max(...scores);
    return Math.min(100, Math.round(maxScore));
  };

  const topScoreValue = getTopScore();
  const recentJobsList = jobs.slice(0, 6);

  return (
    <div className="space-y-10 max-w-7xl mx-auto">
      {/* 1. HERO SECTION WITH 3D CANVAS & FRAMER MOTION ENTRANCE */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="relative p-6 sm:p-8 min-[821px]:p-12 flex flex-col min-[821px]:flex-row items-center justify-between gap-10 overflow-hidden rounded-3xl bg-gradient-to-b from-white/95 to-[#EEF2FF]/90 border border-[#E0E7FF] dark:border-white/10 shadow-2xl backdrop-blur-xl"
      >
        {/* Decorative background glow */}
        <div
          className="absolute -top-32 -left-32 w-96 h-96 rounded-full blur-3xl opacity-20 pointer-events-none"
          style={{ backgroundColor: currentThemeColors.primary }}
        />
        <div
          className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full blur-3xl opacity-20 pointer-events-none"
          style={{ backgroundColor: currentThemeColors.secondary }}
        />

        {/* Left Hero Overlay Content */}
        <div className="flex-1 space-y-6 z-10 text-center min-[821px]:text-left">
          <motion.div variants={itemVariants} className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-mono font-bold bg-[#E0E7FF]/80 text-[#4F46E5] border border-[#c7d2fe] shadow-xs">
            <span className="w-2.5 h-2.5 rounded-full bg-[#10B981] animate-ping" />
            <span>AI-POWERED PREDICTION ENGINE</span>
          </motion.div>

          <motion.h1
            variants={itemVariants}
            className="text-4xl sm:text-5xl min-[821px]:text-6xl font-black font-heading text-slate-900 tracking-tight leading-[1.08]"
          >
            Find Your{" "}
            <span
              className="bg-clip-text text-transparent"
              style={{
                backgroundImage: `linear-gradient(135deg, ${currentThemeColors.primary}, ${currentThemeColors.secondary})`,
              }}
            >
              Perfect Job Match
            </span>
          </motion.h1>

          <motion.p
            variants={itemVariants}
            className="text-slate-600 max-w-xl text-base sm:text-lg font-normal leading-relaxed mx-auto min-[821px]:mx-0"
          >
            Neural AI analyzes your skills, computes multidimensional vector similarity, and predicts top-tier career opportunities in seconds.
          </motion.p>

          <motion.div
            variants={itemVariants}
            className="flex flex-wrap items-center justify-center min-[821px]:justify-start gap-4 pt-2"
          >
            <Link
              href="/analyzer"
              className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-xl font-bold text-white shadow-lg transition-all transform hover:-translate-y-0.5 hover:shadow-xl cursor-pointer"
              style={{
                background: `linear-gradient(135deg, ${currentThemeColors.primary}, ${currentThemeColors.secondary})`,
                boxShadow: `0 8px 24px ${currentThemeColors.glow}`,
              }}
            >
              <span className="text-lg">⚡</span>
              <span>Upload Resume</span>
            </Link>
            <Link
              href="/job-board"
              className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-xl font-bold text-slate-700 bg-white/90 border border-[#E0E7FF] shadow-xs hover:bg-slate-50 transition-all transform hover:-translate-y-0.5 cursor-pointer"
            >
              <span className="text-lg">💼</span>
              <span>Browse Job Market</span>
            </Link>
          </motion.div>

          {/* Quick Stats Floating Glass Cards */}
          <motion.div
            variants={itemVariants}
            className="grid grid-cols-3 gap-3 sm:gap-4 pt-6 mt-4 border-t border-[#E0E7FF] font-sans"
          >
            <div className="glass-panel p-3 sm:p-4 text-center sm:text-left">
              <p className="text-[10px] sm:text-[11px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                Available Positions
              </p>
              <p
                className="text-xl sm:text-2xl font-black font-heading mt-1"
                style={{ color: currentThemeColors.primary }}
              >
                {stats.total_jobs.toLocaleString()}
              </p>
            </div>
            <div className="glass-panel p-3 sm:p-4 text-center sm:text-left">
              <p className="text-[10px] sm:text-[11px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                Resumes Analyzed
              </p>
              <p
                className="text-xl sm:text-2xl font-black font-heading mt-1"
                style={{ color: currentThemeColors.secondary }}
              >
                {stats.total_resumes.toLocaleString()}
              </p>
            </div>
            <div className="glass-panel p-3 sm:p-4 text-center sm:text-left">
              <p className="text-[10px] sm:text-[11px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                Top Compatibility
              </p>
              <p className="text-xl sm:text-2xl font-black font-heading mt-1 text-[#10B981]">
                {stats.top_compatibility_score || "94.2%"}
              </p>
            </div>
          </motion.div>
        </div>

        {/* Right 3D Interactive Hero Canvas */}
        <div className="w-full min-[821px]:w-[480px] shrink-0 z-10">
          <Hero3DScene />
        </div>
      </motion.div>

      {/* 2. BENTO GRID DASHBOARD LAYOUT */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Tile 0: Salvo Engine Status Widget */}
        <SalvoDashboardWidget />

        {/* Tile 1: 3D Holographic Globe */}
        <Card3DTilt maxDegree={8} scaleOnHover={1.01} className="glass-panel p-6 md:col-span-2 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <span
                className="text-xs font-mono font-bold uppercase tracking-widest px-3.5 py-1 rounded-full border"
                style={{
                  color: currentThemeColors.primary,
                  backgroundColor: currentThemeColors.badgeBg,
                  borderColor: currentThemeColors.badgeBorder,
                }}
              >
                Global Candidate Network
              </span>
              <h3 className="text-2xl font-bold text-slate-900 mt-2 font-heading">
                Geographic Talent Distribution
              </h3>
            </div>
            <span className="text-xs font-mono font-bold text-[#10B981] bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
              Live Vector Map
            </span>
          </div>

          <div className="w-full h-[280px]">
            <HolographicGlobe3D />
          </div>

          <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-[#E0E7FF] font-mono text-center text-xs">
            <div className="bg-white/80 p-3 rounded-xl border border-[#E0E7FF] shadow-xs">
              <span className="text-slate-400 block text-[10px]">Active Markets</span>
              <span className="font-extrabold text-slate-900">42 Countries</span>
            </div>
            <div className="bg-white/80 p-3 rounded-xl border border-[#E0E7FF] shadow-xs">
              <span className="text-slate-400 block text-[10px]">Vector Store</span>
              <span className="font-extrabold text-slate-900">Pinecone Cloud</span>
            </div>
            <div className="bg-white/80 p-3 rounded-xl border border-[#E0E7FF] shadow-xs">
              <span className="text-slate-400 block text-[10px]">Match Latency</span>
              <span className="font-extrabold text-[#10B981]">&lt; 38ms</span>
            </div>
          </div>
        </Card3DTilt>

        {/* Tile 2: 3D Neural Match Vector Matrix */}
        <Card3DTilt maxDegree={10} scaleOnHover={1.02} className="glass-panel p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono font-bold text-[#0EA5E9] uppercase tracking-widest bg-sky-50 px-3 py-1 rounded-full border border-sky-200">
                Neural Match Engine
              </span>
              <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 font-heading">Match Vector Matrix</h3>
            <p className="text-xs text-slate-500 mt-1">
              3D spatial representation of candidate skill vectors matched against employer postings.
            </p>
          </div>

          <div className="my-2">
            <Interactive3DCubeMesh />
          </div>

          <div className="bg-white/80 p-3 rounded-xl border border-[#E0E7FF] flex items-center justify-between font-mono text-xs shadow-xs">
            <span className="text-slate-600">Top Neural Match Rank</span>
            <span className="font-extrabold text-[#10B981]">{topScoreValue}%</span>
          </div>
        </Card3DTilt>
      </div>

      {/* 3. RECENT PREDICTION JOBS FEED WITH BENTO CARDS & SKELETON LOADERS */}
      <div className="glass-panel p-6 sm:p-8 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <span
              className="text-xs font-mono font-bold uppercase tracking-widest px-3.5 py-1 rounded-full border"
              style={{
                color: currentThemeColors.primary,
                backgroundColor: currentThemeColors.badgeBg,
                borderColor: currentThemeColors.badgeBorder,
              }}
            >
              Market Predictions
            </span>
            <h3 className="text-2xl font-bold text-slate-900 mt-2 font-heading">
              Top Prediction Opportunities
            </h3>
          </div>
          <Link
            href="/job-board"
            className="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-full text-xs font-mono font-bold transition-all shadow-md self-start sm:self-auto hover:shadow-lg"
          >
            View All Predictions →
          </Link>
        </div>

        {loadingJobs ? (
          /* Shimmer skeleton loading grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map((idx) => (
              <div
                key={idx}
                className="bg-white/70 border border-[#E0E7FF] rounded-2xl p-5 space-y-4 animate-pulse"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-slate-200" />
                  <div className="space-y-1.5 flex-1">
                    <div className="h-4 bg-slate-200 rounded-md w-3/4" />
                    <div className="h-3 bg-slate-100 rounded-md w-1/2" />
                  </div>
                </div>
                <div className="flex gap-2">
                  <div className="h-5 bg-slate-100 rounded-full w-16" />
                  <div className="h-5 bg-slate-100 rounded-full w-20" />
                </div>
                <div className="pt-3 border-t border-slate-100 flex justify-between items-center">
                  <div className="h-4 bg-slate-200 rounded-md w-24" />
                  <div className="h-6 bg-slate-200 rounded-full w-20" />
                </div>
              </div>
            ))}
          </div>
        ) : recentJobsList.length > 0 ? (
          /* Modern interactive job cards grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {recentJobsList.map((j) => {
              const reqSkills = Array.isArray(j.required_skills)
                ? j.required_skills
                : typeof j.required_skills === "string"
                ? j.required_skills.split(",").map((s) => s.trim())
                : [];

              const match = matchResults?.find((m: any) => String(m.job_id) === String(j.job_id));
              const scoreVal = match
                ? typeof match.match_score === "number"
                  ? match.match_score <= 1
                    ? Math.round(match.match_score * 100)
                    : Math.round(match.match_score)
                  : 94
                : null;

              return (
                <div
                  key={j.job_id}
                  onClick={() => router.push(`/job-board?selected=${j.job_id}`)}
                  className="group bg-white/80 hover:bg-white border border-[#E0E7FF] hover:border-indigo-300 rounded-2xl p-5 flex flex-col justify-between transition-all duration-300 shadow-xs hover:shadow-xl hover:-translate-y-1 cursor-pointer"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-10 h-10 rounded-xl flex items-center justify-center font-heading font-black text-white text-base shadow-sm shrink-0"
                          style={{
                            background: `linear-gradient(135deg, ${currentThemeColors.primary}, ${currentThemeColors.secondary})`,
                          }}
                        >
                          {j.company?.charAt(0).toUpperCase() || "J"}
                        </div>
                        <div>
                          <h4 className="font-bold text-slate-900 text-sm group-hover:text-indigo-600 transition-colors line-clamp-1">
                            {j.title}
                          </h4>
                          <p className="text-xs text-slate-500 font-medium">
                            {j.company} • 📍 {j.location}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {reqSkills.slice(0, 3).map((sk) => (
                        <span
                          key={sk}
                          className="text-[10px] font-mono bg-[#E0E7FF]/60 text-[#4F46E5] px-2 py-0.5 rounded-full border border-[#c7d2fe]"
                        >
                          {sk}
                        </span>
                      ))}
                      {reqSkills.length > 3 && (
                        <span className="text-[10px] font-mono text-slate-400 px-1 py-0.5">
                          +{reqSkills.length - 3}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="pt-4 mt-4 border-t border-slate-100 flex items-center justify-between font-mono text-xs">
                    <div>
                      <p className="font-bold text-slate-900">
                        {j.salary_min && j.salary_max
                          ? `$${Math.round(j.salary_min / 1000)}k - $${Math.round(j.salary_max / 1000)}k`
                          : "Competitive"}
                      </p>
                      <p className="text-[10px] text-emerald-600 font-bold">Vector Indexed</p>
                    </div>

                    {scoreVal !== null ? (
                      <span className="px-3 py-1 bg-emerald-50 text-[#10B981] border border-emerald-200 rounded-full text-xs font-bold shadow-xs">
                        {scoreVal}% Match
                      </span>
                    ) : (
                      <span className="px-3 py-1 bg-indigo-50 text-indigo-600 border border-indigo-200 rounded-full text-xs font-semibold shadow-xs">
                        Open Role
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-12 text-center text-xs text-slate-500 font-mono space-y-2">
            <p>No job predictions found in the database.</p>
            <p className="text-[11px] text-slate-400">Ensure the backend API is running on port 8000.</p>
          </div>
        )}
      </div>
    </div>
  );
}
