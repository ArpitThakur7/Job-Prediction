"use client";

import React, { useState, useEffect } from "react";
import { salvoClient, SalvoJob } from "@/lib/salvoClient";
import JobCard3D from "@/components/salvo/JobCard3D";
import ScanModal from "@/components/salvo/ScanModal";
import TailorModal from "@/components/salvo/TailorModal";
import { useApp } from "@/context/AppContext";

export default function JobsPage() {
  const { currentThemeColors } = useApp();
  const [jobs, setJobs] = useState<SalvoJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<"global" | "india">("global");
  const [searchQuery, setSearchQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [isScanOpen, setIsScanOpen] = useState(false);
  const [selectedJobForTailor, setSelectedJobForTailor] = useState<SalvoJob | null>(null);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = await salvoClient.getJobs({
        mode,
        query: searchQuery,
        source: sourceFilter,
        minScore,
        page,
        limit: 18,
      });
      setJobs(data.jobs || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error("Failed to load jobs", err);
      setJobs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [mode, searchQuery, sourceFilter, minScore, page]);

  return (
    <div className="space-y-6">
      {/* Top Banner & Control Deck */}
      <div
        className="p-6 rounded-3xl border backdrop-blur-xl shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4"
        style={{
          backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)",
          borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)",
        }}
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">⚡</span>
            <h1 className="text-2xl font-black tracking-tight" style={{ color: currentThemeColors.textColor || "#F8FAFC" }}>
              Salvo Agentic Job Feed
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono border border-cyan-500/30 text-cyan-300 bg-cyan-500/10">
              ZERO-AUTH DISCOVERY
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono">
            Unauthenticated public endpoints · Rule-based triage + XGBoost ML signal · Never automated submit
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex p-1 rounded-xl bg-black/30 border border-white/10 text-xs font-mono">
            <button
              onClick={() => { setMode("global"); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                mode === "global" ? "bg-cyan-500 text-black font-bold shadow-md" : "text-slate-400 hover:text-white"
              }`}
            >
              🌐 Global Remote
            </button>
            <button
              onClick={() => { setMode("india"); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                mode === "india" ? "bg-emerald-500 text-black font-bold shadow-md" : "text-slate-400 hover:text-white"
              }`}
            >
              🇮🇳 India Market
            </button>
          </div>

          <button
            onClick={() => setIsScanOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold font-mono text-xs bg-cyan-500 hover:bg-cyan-400 text-black shadow-[0_0_20px_rgba(6,182,212,0.3)] transition-all hover:scale-105"
          >
            <span>📡</span> Scan Boards Now
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="md:col-span-2 relative">
          <input
            type="text"
            placeholder="Search roles, companies, or keywords (e.g. React, Node, AI)..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            className="w-full pl-9 pr-4 py-2.5 rounded-xl text-xs font-mono bg-black/20 border border-white/10 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition-colors"
          />
          <span className="absolute left-3 top-3 text-slate-500 text-xs">🔍</span>
        </div>

        <div>
          <select
            value={sourceFilter}
            onChange={(e) => { setSourceFilter(e.target.value); setPage(1); }}
            className="w-full px-3 py-2.5 rounded-xl text-xs font-mono bg-black/20 border border-white/10 text-slate-200 focus:outline-none focus:border-cyan-400 transition-colors"
          >
            <option value="">All Sources (Greenhouse, Lever, etc.)</option>
            <option value="greenhouse">Greenhouse</option>
            <option value="ashby">Ashby</option>
            <option value="lever">Lever</option>
            <option value="unstop">Unstop (India)</option>
            <option value="remoteok">RemoteOK</option>
          </select>
        </div>

        <div>
          <select
            value={minScore}
            onChange={(e) => { setMinScore(Number(e.target.value)); setPage(1); }}
            className="w-full px-3 py-2.5 rounded-xl text-xs font-mono bg-black/20 border border-white/10 text-slate-200 focus:outline-none focus:border-cyan-400 transition-colors"
          >
            <option value="0">All Match Scores</option>
            <option value="60">Match Score ≥ 60%</option>
            <option value="75">Match Score ≥ 75%</option>
            <option value="85">High Confidence ≥ 85%</option>
          </select>
        </div>
      </div>

      {/* Grid of 3D Cards */}
      {loading ? (
        <div className="py-24 flex flex-col items-center justify-center space-y-3">
          <div className="w-10 h-10 border-4 border-cyan-500/20 border-t-cyan-400 rounded-full animate-spin" />
          <span className="text-xs font-mono text-slate-400">Loading scored postings...</span>
        </div>
      ) : jobs.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {jobs.map((job) => (
              <JobCard3D
                key={job.url}
                job={job}
                onTailorClick={(j) => setSelectedJobForTailor(j)}
              />
            ))}
          </div>

          {/* Pagination */}
          {total > 18 && (
            <div className="flex items-center justify-center gap-3 pt-6 font-mono text-xs text-slate-400">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-lg border border-white/10 disabled:opacity-40 hover:bg-white/5"
              >
                ← Previous
              </button>
              <span>Page {page} of {Math.ceil(total / 18)}</span>
              <button
                disabled={page >= Math.ceil(total / 18)}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 rounded-lg border border-white/10 disabled:opacity-40 hover:bg-white/5"
              >
                Next →
              </button>
            </div>
          )}
        </>
      ) : (
        <div
          className="p-12 rounded-3xl border border-dashed border-white/10 text-center space-y-3 backdrop-blur-md"
          style={{ backgroundColor: "rgba(15, 23, 42, 0.4)" }}
        >
          <span className="text-3xl">📡</span>
          <h3 className="text-lg font-bold text-slate-200">No postings matching criteria</h3>
          <p className="text-xs text-slate-400 font-mono max-w-md mx-auto">
            Try adjusting your search filters, or trigger a live board scan to refresh the discovery queue.
          </p>
          <button
            onClick={() => setIsScanOpen(true)}
            className="px-4 py-2 rounded-xl text-xs font-mono font-bold bg-cyan-500 text-black hover:bg-cyan-400"
          >
            Launch Discovery Scan
          </button>
        </div>
      )}

      {/* Modals */}
      <ScanModal
        isOpen={isScanOpen}
        onClose={() => setIsScanOpen(false)}
        onScanComplete={() => {
          setIsScanOpen(false);
          fetchJobs();
        }}
      />

      <TailorModal
        job={selectedJobForTailor}
        isOpen={!!selectedJobForTailor}
        onClose={() => setSelectedJobForTailor(null)}
      />
    </div>
  );
}
