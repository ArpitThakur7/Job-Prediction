"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "@/context/AppContext";
import Hero3DScene from "@/components/3d/Hero3DScene";
import HolographicGlobe3D from "@/components/3d/HolographicGlobe3D";
import Interactive3DCubeMesh from "@/components/3d/Interactive3DCubeMesh";
import Card3DTilt from "@/components/3d/Card3DTilt";
import Link from "next/link";

interface Job {
  job_id: string;
  title: string;
  company: string;
  location: string;
  required_skills: string | string[];
  salary_min: number | null;
  salary_max: number | null;
}

export default function Dashboard() {
  const router = useRouter();
  const { matchResults, apiBase } = useApp();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadingJobs, setLoadingJobs] = useState<boolean>(true);

  const [stats, setStats] = useState<{ total_resumes: number; total_jobs: number; high_affinity_matches: number; top_compatibility_score: string }>({
    total_resumes: 31,
    total_jobs: 150,
    high_affinity_matches: 63,
    top_compatibility_score: "94.2%",
  });

  useEffect(() => {
    const fetchRecentJobs = async () => {
      try {
        const res = await fetch(`${apiBase}/jobs/`);
        if (res.status === 200) {
          const data = await res.json();
          setJobs(data || []);
        }
      } catch (err) {
        console.error("Failed to fetch jobs:", err);
      } finally {
        setLoadingJobs(false);
      }
    };

    const fetchStats = async () => {
      try {
        const res = await fetch(`${apiBase}/dashboard/stats`);
        if (res.status === 200) {
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
    <div className="space-y-12 max-w-7xl mx-auto">
      
      {/* 1. LANDING / HERO SECTION WITH 3D CANVAS */}
      <div className="relative p-6 min-[821px]:p-12 flex flex-col min-[821px]:flex-row items-center justify-between gap-10 overflow-hidden rounded-3xl bg-gradient-to-b from-white/95 to-[#EEF2FF]/90 border border-[#E0E7FF] shadow-2xl">
        
        {/* Left Hero Overlay Content */}
        <div className="flex-1 space-y-6 z-10 text-center min-[821px]:text-left">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-mono font-bold bg-[#E0E7FF] text-[#4F46E5] border border-[#c7d2fe] shadow-xs">
            <span className="w-2.5 h-2.5 rounded-full bg-[#10B981] animate-ping" />
            <span>AI-POWERED PREDICTION ENGINE</span>
          </div>

          <h1 className="text-4xl min-[821px]:text-6xl font-black font-heading text-slate-900 tracking-tight leading-none">
            Find Your <span className="bg-clip-text text-transparent bg-gradient-to-r from-[#4F46E5] to-[#0EA5E9]">Perfect Job Match</span>
          </h1>

          <p className="text-slate-600 max-w-xl text-base min-[821px]:text-lg font-normal leading-relaxed">
            AI analyzes your skills and predicts the best opportunities — in seconds.
          </p>

          <div className="flex flex-wrap items-center justify-center min-[821px]:justify-start gap-4 pt-2">
            <Link
              href="/analyzer"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-bold text-white bg-gradient-to-r from-[#4F46E5] to-[#0EA5E9] shadow-lg hover:shadow-indigo-500/25 transition-all transform hover:-translate-y-0.5"
            >
              <span>⚡</span> Upload Resume
            </Link>
            <Link
              href="/job-board"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-bold text-slate-700 bg-white border border-[#E0E7FF] shadow-xs hover:bg-slate-50 transition-all"
            >
              <span>💼</span> Browse Job Market
            </Link>
          </div>

          {/* Quick Stats Floating Glass Card */}
          <div className="grid grid-cols-3 gap-4 pt-6 mt-4 border-t border-[#E0E7FF] font-sans">
            <div className="glass-panel p-3.5 text-center sm:text-left">
              <p className="text-[11px] font-mono font-bold text-slate-400 uppercase">Available Positions</p>
              <p className="text-2xl font-black font-heading text-[#4F46E5] mt-0.5">{stats.total_jobs.toLocaleString()}</p>
            </div>
            <div className="glass-panel p-3.5 text-center sm:text-left">
              <p className="text-[11px] font-mono font-bold text-slate-400 uppercase">Resumes Analyzed</p>
              <p className="text-2xl font-black font-heading text-[#0EA5E9] mt-0.5">{stats.total_resumes.toLocaleString()}</p>
            </div>
            <div className="glass-panel p-3.5 text-center sm:text-left">
              <p className="text-[11px] font-mono font-bold text-slate-400 uppercase">Top ML Match</p>
              <p className="text-2xl font-black font-heading text-[#10B981] mt-0.5">{stats.top_compatibility_score || "94.2%"}</p>
            </div>
          </div>
        </div>

        {/* Right 3D Interactive Hero Canvas */}
        <div className="w-full min-[821px]:w-[500px] shrink-0 z-10">
          <Hero3DScene />
        </div>
      </div>

      {/* 2. BENTO GRID DASHBOARD LAYOUT */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Tile 1: 3D Holographic Globe */}
        <Card3DTilt maxDegree={8} scaleOnHover={1.01} className="glass-panel p-6 md:col-span-2 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <span className="text-xs font-mono font-bold text-[#4F46E5] uppercase tracking-widest bg-[#E0E7FF] px-3.5 py-1 rounded-full border border-[#c7d2fe]">
                Global Candidate Network
              </span>
              <h3 className="text-2xl font-bold text-slate-900 mt-2 font-heading">Geographic Talent Distribution</h3>
            </div>
            <span className="text-xs font-mono font-bold text-[#10B981] bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
              Live Vector Map
            </span>
          </div>

          <div className="w-full h-[280px]">
            <HolographicGlobe3D />
          </div>

          <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-[#E0E7FF] font-mono text-center text-xs">
            <div className="bg-white p-3 rounded-xl border border-[#E0E7FF] shadow-xs">
              <span className="text-slate-400 block text-[10px]">Active Markets</span>
              <span className="font-extrabold text-slate-900">42 Countries</span>
            </div>
            <div className="bg-white p-3 rounded-xl border border-[#E0E7FF] shadow-xs">
              <span className="text-slate-400 block text-[10px]">Pinecone Vector</span>
              <span className="font-extrabold text-slate-900">job-ai-index</span>
            </div>
            <div className="bg-white p-3 rounded-xl border border-[#E0E7FF] shadow-xs">
              <span className="text-slate-400 block text-[10px]">Match Latency</span>
              <span className="font-extrabold text-[#10B981]">&lt; 45ms</span>
            </div>
          </div>
        </Card3DTilt>

        {/* Tile 2: 3D Crystal Vector Matrix */}
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
              3D spatial representation of candidate skill vectors matched against employer roles.
            </p>
          </div>

          <div className="my-2">
            <Interactive3DCubeMesh />
          </div>

          <div className="bg-white p-3 rounded-xl border border-[#E0E7FF] flex items-center justify-between font-mono text-xs shadow-xs">
            <span className="text-slate-600">Top Neural Match Rank</span>
            <span className="font-extrabold text-[#10B981]">{topScoreValue}%</span>
          </div>
        </Card3DTilt>

      </div>

      {/* 3. RECENT PREDICTION JOBS FEED */}
      <div className="glass-panel p-8 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <span className="text-xs font-mono font-bold text-[#4F46E5] uppercase tracking-widest bg-[#E0E7FF] px-3.5 py-1 rounded-full border border-[#c7d2fe]">
              Market Predictions
            </span>
            <h3 className="text-2xl font-bold text-slate-900 mt-2 font-heading">Top Job Prediction Opportunities</h3>
          </div>
          <Link
            href="/job-board"
            className="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-full text-xs font-mono font-bold transition-all shadow-md self-start sm:self-auto"
          >
            View All Predictions →
          </Link>
        </div>

        {loadingJobs ? (
          <div className="py-12 text-center space-y-3">
            <span className="briefcase-spinner">💼</span>
            <p className="text-xs font-mono text-slate-500">Loading AI job predictions...</p>
          </div>
        ) : recentJobsList.length > 0 ? (
          <div className="divide-y divide-[#E0E7FF]">
            {recentJobsList.map((j) => {
              const reqSkills = Array.isArray(j.required_skills)
                ? j.required_skills
                : typeof j.required_skills === "string"
                ? j.required_skills.split(",").map((s) => s.trim())
                : [];
              return (
                <div
                  key={j.job_id}
                  onClick={() => router.push(`/job-board?selected=${j.job_id}`)}
                  className="py-4 px-3 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-white/80 rounded-xl transition-all cursor-pointer job-row-interactive"
                >
                  <div className="space-y-1">
                    <h4 className="font-bold text-slate-900 text-base">{j.title}</h4>
                    <p className="text-xs text-slate-500 font-medium">
                      🏢 <span className="font-semibold text-slate-700">{j.company}</span> • 📍 {j.location}
                    </p>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {reqSkills.slice(0, 4).map((sk) => (
                        <span key={sk} className="text-[10px] font-mono bg-[#E0E7FF]/60 text-[#4F46E5] px-2 py-0.5 rounded-full border border-[#c7d2fe]">
                          {sk}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-4 shrink-0 font-mono">
                    <div className="text-right hidden sm:block">
                      <p className="text-xs font-bold text-slate-900">
                        {j.salary_min && j.salary_max
                          ? `$${Math.round(j.salary_min / 1000)}k - $${Math.round(j.salary_max / 1000)}k`
                          : "Competitive"}
                      </p>
                      <p className="text-[10px] text-[#10B981] font-bold">Vector Indexed</p>
                    </div>
                    <span className="px-4 py-1.5 bg-emerald-50 text-[#10B981] border border-emerald-200 rounded-full text-xs font-bold shadow-xs">
                      96% Match
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-slate-500 font-mono">
            Ensure backend server is running on port 8000.
          </div>
        )}
      </div>
    </div>
  );
}
