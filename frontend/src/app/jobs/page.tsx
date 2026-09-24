"use client";

import React, { useState, useEffect } from "react";
import { salvoClient, SalvoJob, SalvoApiError } from "@/lib/salvoClient";
import JobCard3D from "@/components/salvo/JobCard3D";
import ScanModal from "@/components/salvo/ScanModal";
import TailorModal from "@/components/salvo/TailorModal";
import SalvoConnectionGuard from "@/components/salvo/SalvoConnectionGuard";
import { useToast } from "@/context/ToastContext";

export default function JobsPage() {
  const { addToast } = useToast();
  const [jobs, setJobs] = useState<SalvoJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<"global" | "india">("global");
  const [searchQuery, setSearchQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [scannedAt, setScannedAt] = useState<string | null>(null);
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
      setScannedAt(data.scannedAt || null);
    } catch (err: any) {
      if (err instanceof SalvoApiError && err.isOffline) {
        setJobs([]);
      } else {
        addToast({ type: "error", title: "Failed to load jobs", message: err.message });
        setJobs([]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [mode, searchQuery, sourceFilter, minScore, page]);

  return (
    <SalvoConnectionGuard>
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        {/* Top Banner & Control Deck */}
        <div className="p-6 md:p-8 rounded-3xl border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-slate-900/90 backdrop-blur-xl shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="space-y-1">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="text-2xl">⚡</span>
              <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">
                Salvo Agentic Job Feed
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border border-cyan-500/30 text-cyan-700 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-500/10">
                ZERO-AUTH DISCOVERY
              </span>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 font-mono">
              Unauthenticated public endpoints · Rule-based triage + XGBoost ML signal · Never automated submit
              {scannedAt && (
                <span className="ml-2 font-semibold text-slate-700 dark:text-slate-300">
                  · Last scan: {new Date(scannedAt).toLocaleString()}
                </span>
              )}
            </p>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex p-1 rounded-2xl bg-slate-100 dark:bg-black/40 border border-slate-300 dark:border-white/10 text-xs font-mono">
              <button
                onClick={() => {
                  setMode("global");
                  setPage(1);
                }}
                className={`px-3.5 py-1.5 rounded-xl transition-all ${
                  mode === "global"
                    ? "bg-cyan-500 text-slate-950 font-bold shadow-md"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                🌐 Global Remote
              </button>
              <button
                onClick={() => {
                  setMode("india");
                  setPage(1);
                }}
                className={`px-3.5 py-1.5 rounded-xl transition-all ${
                  mode === "india"
                    ? "bg-emerald-500 text-slate-950 font-bold shadow-md"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                🇮🇳 India Market
              </button>
            </div>

            <button
              onClick={() => setIsScanOpen(true)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold font-mono text-xs bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-md hover:shadow-cyan-500/30 transition-all hover:scale-105"
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
              placeholder="Search roles, companies, or keywords (e.g. React, Node, Python)..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              className="w-full pl-10 pr-4 py-3 rounded-2xl text-xs font-mono bg-white dark:bg-black/40 border border-slate-300 dark:border-white/10 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 shadow-sm transition-all"
            />
            <span className="absolute left-3.5 top-3.5 text-slate-400 dark:text-slate-500 text-sm">🔍</span>
          </div>

          <div>
            <select
              value={sourceFilter}
              onChange={(e) => {
                setSourceFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-4 py-3 rounded-2xl text-xs font-mono bg-white dark:bg-black/40 border border-slate-300 dark:border-white/10 text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-sm transition-all"
            >
              <option value="" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                All Sources (Greenhouse, Lever, etc.)
              </option>
              <option value="greenhouse" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                Greenhouse
              </option>
              <option value="ashby" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                Ashby
              </option>
              <option value="lever" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                Lever
              </option>
              <option value="unstop" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                Unstop (India)
              </option>
              <option value="remoteok" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                RemoteOK
              </option>
              <option value="remotive" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                Remotive
              </option>
              <option value="hn-hiring" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                Hacker News
              </option>
            </select>
          </div>

          <div>
            <select
              value={minScore}
              onChange={(e) => {
                setMinScore(Number(e.target.value));
                setPage(1);
              }}
              className="w-full px-4 py-3 rounded-2xl text-xs font-mono bg-white dark:bg-black/40 border border-slate-300 dark:border-white/10 text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-sm transition-all"
            >
              <option value="0" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                All Match Scores
              </option>
              <option value="50" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                Match Score ≥ 50%
              </option>
              <option value="60" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                Match Score ≥ 60%
              </option>
              <option value="75" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                Match Score ≥ 75%
              </option>
              <option value="85" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                High Confidence ≥ 85%
              </option>
            </select>
          </div>
        </div>

        {/* Results Summary */}
        {!loading && jobs.length > 0 && (
          <div className="flex items-center justify-between text-xs font-mono text-slate-600 dark:text-slate-400 px-1">
            <span>
              Showing <strong className="text-slate-900 dark:text-white">{jobs.length}</strong> of{" "}
              <strong className="text-slate-900 dark:text-white">{total}</strong> matched postings (page {page})
            </span>
            <span className="font-semibold text-cyan-700 dark:text-cyan-400">
              {mode === "india" ? "🇮🇳 India Market" : "🌐 Global Remote"}
            </span>
          </div>
        )}

        {/* Grid of 3D Cards */}
        {loading ? (
          <div className="py-24 flex flex-col items-center justify-center space-y-3">
            <div className="w-10 h-10 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
            <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300">
              Loading scored postings...
            </span>
          </div>
        ) : jobs.length > 0 ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
              <div className="flex items-center justify-center gap-3 pt-6 font-mono text-xs">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="px-4 py-2 rounded-xl border border-slate-300 dark:border-white/10 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors shadow-sm"
                >
                  ← Previous
                </button>
                <span className="text-slate-600 dark:text-slate-400 font-bold px-2">
                  Page {page} of {Math.ceil(total / 18)}
                </span>
                <button
                  disabled={page >= Math.ceil(total / 18)}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-4 py-2 rounded-xl border border-slate-300 dark:border-white/10 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors shadow-sm"
                >
                  Next →
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="p-12 rounded-3xl border border-dashed border-slate-300 dark:border-white/10 bg-white/80 dark:bg-slate-900/40 text-center space-y-4 shadow-sm">
            <span className="text-4xl block">📡</span>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">No postings matching criteria</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 font-mono max-w-md mx-auto">
              Try adjusting your search query, lowering the minimum match score, or launching a live discovery scan.
            </p>
            <button
              onClick={() => setIsScanOpen(true)}
              className="px-5 py-2.5 rounded-xl text-xs font-mono font-bold bg-cyan-500 text-slate-950 hover:bg-cyan-400 transition-all shadow-md"
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
            addToast({
              type: "success",
              title: "Scan Complete",
              message: "Pipeline updated and synced to Excel tracker.",
            });
          }}
        />

        <TailorModal
          job={selectedJobForTailor}
          isOpen={!!selectedJobForTailor}
          onClose={() => setSelectedJobForTailor(null)}
        />
      </div>
    </SalvoConnectionGuard>
  );
}
