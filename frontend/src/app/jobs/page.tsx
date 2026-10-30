"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LayoutGrid, List, Radar, RefreshCw, SlidersHorizontal, X } from "lucide-react";
import { salvoClient, SalvoJob, SalvoApiError } from "@/lib/salvoClient";
import { isEarlyCareer, isRemote, isSenior, jobScore, jobSource } from "@/lib/jobScore";
import { sendFeedback } from "@/lib/feedback";
import JobCard3D from "@/components/salvo/JobCard3D";
import JobRowList from "@/components/salvo/JobRowList";
import JobPreviewDrawer from "@/components/salvo/JobPreviewDrawer";
import ScanModal from "@/components/salvo/ScanModal";
import TailorModal from "@/components/salvo/TailorModal";
import ApplyModal from "@/components/salvo/ApplyModal";
import SalvoConnectionGuard from "@/components/salvo/SalvoConnectionGuard";
import FilterRail, { defaultFilters, Filters, Market, topics } from "@/components/salvo/FilterRail";
import { useToast } from "@/context/ToastContext";

type ViewMode = "grid" | "list";
type SortBy = "fit" | "newest" | "company";

const SAVED_KEY = "salvo_saved_job_urls";
const HIDDEN_KEY = "salvo_dismissed_job_urls";
const PAGE_SIZE = 18;

function loadSet(key: string) {
  try {
    const raw = localStorage.getItem(key);
    return new Set<string>(raw ? JSON.parse(raw) : []);
  } catch {
    return new Set<string>();
  }
}

function storeSet(key: string, set: Set<string>) {
  try {
    localStorage.setItem(key, JSON.stringify([...set]));
  } catch {}
}

export default function JobsPage() {
  const { addToast } = useToast();
  const searchRef = useRef<HTMLInputElement>(null);

  const [allJobs, setAllJobs] = useState<SalvoJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [scannedAt, setScannedAt] = useState<string | null>(null);

  const [market, setMarket] = useState<Market>("global");
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [query, setQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortBy>("fit");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [page, setPage] = useState(1);
  const [sheetOpen, setSheetOpen] = useState(false);

  const [saved, setSaved] = useState<Set<string>>(new Set());
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const [previewJob, setPreviewJob] = useState<SalvoJob | null>(null);
  const [tailorJob, setTailorJob] = useState<SalvoJob | null>(null);
  const [applyJob, setApplyJob] = useState<SalvoJob | null>(null);
  const [scanOpen, setScanOpen] = useState(false);
  const focusUrl = useRef<string | null>(null);

  // Browser-only state (localStorage, URL) is read after hydration so the static HTML matches.
  // Links from the home page: ?focus=<job url> opens a job, ?scan=1 opens the scanner.
  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect */
    setSaved(loadSet(SAVED_KEY));
    setHidden(loadSet(HIDDEN_KEY));
    const params = new URLSearchParams(window.location.search);
    if (params.get("scan") === "1") setScanOpen(true);
    /* eslint-enable react-hooks/set-state-in-effect */
    focusUrl.current = params.get("focus");
  }, []);

  // Debounce typing into the search box.
  useEffect(() => {
    const t = setTimeout(() => setQuery(filters.query.trim().toLowerCase()), 200);
    return () => clearTimeout(t);
  }, [filters.query]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;
      if (e.key === "/" && !typing) {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const fetchJobs = useCallback(
    async (manual = false) => {
      if (manual) setRefreshing(true);
      else setLoading(true);
      try {
        const data = await salvoClient.getJobs({ mode: market === "india" ? "india" : "global", limit: 150 });
        const jobs: SalvoJob[] = (data.jobs || []).filter((j: SalvoJob) => !j.blocked);
        setAllJobs(jobs);
        setScannedAt(data.scannedAt || null);
        if (focusUrl.current) {
          const match = jobs.find((j) => j.url === focusUrl.current);
          if (match) setPreviewJob(match);
          focusUrl.current = null;
        }
        if (manual) addToast({ type: "success", title: "Feed refreshed", message: `${jobs.length} jobs loaded.` });
      } catch (err) {
        if (!(err instanceof SalvoApiError && err.isOffline)) {
          addToast({ type: "error", title: "Couldn't load jobs", message: err instanceof Error ? err.message : String(err) });
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [market, addToast]
  );

  // Refetch only when switching between the global and India pipelines; "saved" filters locally.
  const pipeline = market === "india" ? "india" : "global";
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loading data from the engine is the effect's job
    fetchJobs();
  }, [pipeline]); // eslint-disable-line react-hooks/exhaustive-deps

  const updateFilters = (next: Partial<Filters>) => {
    setFilters((f) => ({ ...f, ...next }));
    setPage(1);
  };
  const resetFilters = () => {
    setFilters(defaultFilters);
    setPage(1);
  };

  const toggleSave = useCallback(
    (job: SalvoJob) => {
      setSaved((prev) => {
        const next = new Set(prev);
        if (next.has(job.url)) {
          next.delete(job.url);
          addToast({ type: "info", title: "Removed from saved", message: job.title });
        } else {
          next.add(job.url);
          sendFeedback(job, "save");
          addToast({ type: "success", title: "Saved", message: `${job.title} at ${job.company}` });
        }
        storeSet(SAVED_KEY, next);
        return next;
      });
    },
    [addToast]
  );

  const toggleHidden = useCallback(
    (job: SalvoJob) => {
      setHidden((prev) => {
        const next = new Set(prev);
        if (next.has(job.url)) {
          next.delete(job.url);
        } else {
          next.add(job.url);
          sendFeedback(job, "dismiss");
          addToast({ type: "info", title: "Hidden from your feed", message: "Salvo will learn from this." });
        }
        storeSet(HIDDEN_KEY, next);
        return next;
      });
    },
    [addToast]
  );

  const openApply = (job: SalvoJob) => setApplyJob(job);

  // Jobs in the current market, before the panel filters — used for the histogram and board counts.
  const marketJobs = useMemo(
    () => (market === "saved" ? allJobs.filter((j) => saved.has(j.url)) : allJobs),
    [allJobs, market, saved]
  );

  const results = useMemo(() => {
    const topic = topics.find((t) => t.id === filters.topic);
    const list = marketJobs.filter((j) => {
      if (!filters.showHidden && hidden.has(j.url)) return false;
      if (jobScore(j) < filters.minFit) return false;
      if (filters.sources.length && !filters.sources.includes(jobSource(j))) return false;
      if (filters.level === "early" && !isEarlyCareer(j)) return false;
      if (filters.level === "senior" && !isSenior(j)) return false;
      if (filters.remoteOnly && !isRemote(j)) return false;
      const text = `${j.title} ${j.company} ${j.location} ${j.description || ""} ${(j.reasons || []).join(" ")}`;
      if (topic && !topic.pattern.test(text)) return false;
      if (query && !text.toLowerCase().includes(query)) return false;
      return true;
    });
    return list.sort((a, b) => {
      if (sortBy === "newest") return (b.postedAt || 0) - (a.postedAt || 0);
      if (sortBy === "company") return (a.company || "").localeCompare(b.company || "");
      return jobScore(b) - jobScore(a);
    });
  }, [marketJobs, filters, query, sortBy, hidden]);

  const totalPages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  const pageJobs = results.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const hiddenCount = marketJobs.filter((j) => hidden.has(j.url)).length;

  const chips: { label: string; clear: () => void }[] = [];
  if (filters.query) chips.push({ label: `“${filters.query}”`, clear: () => updateFilters({ query: "" }) });
  if (filters.minFit) chips.push({ label: `Fit ${filters.minFit}%+`, clear: () => updateFilters({ minFit: 0 }) });
  if (filters.level !== "any") chips.push({ label: filters.level === "early" ? "Early career" : "Senior", clear: () => updateFilters({ level: "any" }) });
  if (filters.remoteOnly) chips.push({ label: "Remote only", clear: () => updateFilters({ remoteOnly: false }) });
  if (filters.topic) chips.push({ label: topics.find((t) => t.id === filters.topic)!.label, clear: () => updateFilters({ topic: "" }) });
  filters.sources.forEach((s) => chips.push({ label: s.charAt(0).toUpperCase() + s.slice(1).replace(/-/g, " "), clear: () => updateFilters({ sources: filters.sources.filter((x) => x !== s) }) }));

  const rail = (
    <FilterRail
      jobs={marketJobs}
      filters={filters}
      onChange={updateFilters}
      onReset={resetFilters}
      market={market}
      onMarket={(m) => {
        setMarket(m);
        setPage(1);
      }}
      savedCount={saved.size}
      hiddenCount={hiddenCount}
      searchRef={searchRef}
    />
  );

  return (
    <SalvoConnectionGuard>
      <div className="max-w-[1400px] mx-auto grid lg:grid-cols-[300px_minmax(0,1fr)] gap-6 items-start">
        <aside className="glass rounded-[28px] p-5 hidden lg:block sticky top-4 max-h-[calc(100vh-2rem)] overflow-y-auto" aria-label="Filters">
          {rail}
        </aside>

        <section className="space-y-5 min-w-0">
          {/* Toolbar */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="mr-auto">
              <p className="font-display text-2xl font-bold tabular">
                {loading ? "Loading jobs…" : `${results.length} ${results.length === 1 ? "job" : "jobs"}`}
              </p>
              <p className="text-sm" style={{ color: "var(--theme-text-muted)" }}>
                {market === "saved" ? "Your saved jobs" : market === "india" ? "India market" : "Global and remote"}
                {scannedAt && `, last scan ${new Date(scannedAt).toLocaleDateString()}`}
              </p>
            </div>

            <button
              onClick={() => setSheetOpen(true)}
              className="lg:hidden glass inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl text-sm font-semibold"
            >
              <SlidersHorizontal size={16} /> Filters{chips.length ? ` (${chips.length})` : ""}
            </button>

            <label className="glass inline-flex items-center gap-2 pl-4 pr-2 py-1.5 rounded-2xl text-sm">
              <span style={{ color: "var(--theme-text-muted)" }}>Sort</span>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value as SortBy)} className="bg-transparent font-semibold py-1 outline-none">
                <option value="fit">Best fit</option>
                <option value="newest">Newest</option>
                <option value="company">Company A–Z</option>
              </select>
            </label>

            <div className="glass inline-flex p-1 rounded-2xl" role="group" aria-label="Layout">
              {(
                [
                  ["grid", LayoutGrid, "Cards"],
                  ["list", List, "List"],
                ] as const
              ).map(([id, Icon, label]) => (
                <button
                  key={id}
                  onClick={() => setViewMode(id)}
                  aria-pressed={viewMode === id}
                  title={label}
                  className={`p-2 rounded-xl transition-colors ${viewMode === id ? "bg-white dark:bg-white/15 shadow-sm" : "opacity-60 hover:opacity-100"}`}
                >
                  <Icon size={18} />
                  <span className="sr-only">{label}</span>
                </button>
              ))}
            </div>

            <button
              onClick={() => fetchJobs(true)}
              disabled={refreshing}
              className="glass p-2.5 rounded-2xl disabled:opacity-50"
              title="Refresh feed"
              aria-label="Refresh feed"
            >
              <RefreshCw size={18} className={refreshing ? "animate-spin" : ""} />
            </button>

            <button
              onClick={() => setScanOpen(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl text-sm font-semibold text-white transition-transform hover:-translate-y-0.5"
              style={{ background: "var(--theme-primary)" }}
            >
              <Radar size={16} /> Scan boards
            </button>
          </div>

          {chips.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {chips.map((c) => (
                <button
                  key={c.label}
                  onClick={c.clear}
                  className="inline-flex items-center gap-1.5 pl-3 pr-2 py-1 rounded-full text-sm font-medium"
                  style={{ background: "var(--theme-badge-bg)", color: "var(--theme-badge-text)" }}
                  aria-label={`Remove filter ${c.label}`}
                >
                  {c.label} <X size={14} />
                </button>
              ))}
              <button onClick={resetFilters} className="text-sm font-semibold px-2" style={{ color: "var(--theme-text-muted)" }}>
                Clear all
              </button>
            </div>
          )}

          {loading ? (
            <div className="grid md:grid-cols-2 2xl:grid-cols-3 gap-5">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="glass rounded-[28px] h-[290px] animate-pulse" />
              ))}
            </div>
          ) : pageJobs.length > 0 ? (
            <>
              {viewMode === "grid" ? (
                <div className="grid md:grid-cols-2 2xl:grid-cols-3 gap-5">
                  {pageJobs.map((job) => (
                    <JobCard3D
                      key={job.url}
                      job={job}
                      onSelect={setPreviewJob}
                      onTailorClick={setTailorJob}
                      onApplyClick={openApply}
                      onToggleSave={toggleSave}
                      onDismiss={toggleHidden}
                      isSaved={saved.has(job.url)}
                      isDismissed={hidden.has(job.url)}
                    />
                  ))}
                </div>
              ) : (
                <div className="glass rounded-[28px] overflow-hidden">
                  <JobRowList
                    jobs={pageJobs}
                    onSelectJob={setPreviewJob}
                    onTailorClick={setTailorJob}
                    onApplyClick={openApply}
                    onToggleSave={toggleSave}
                    savedUrls={saved}
                  />
                </div>
              )}

              {totalPages > 1 && (
                <nav className="flex items-center justify-center gap-3 pt-4" aria-label="Pages">
                  <button
                    disabled={page <= 1}
                    onClick={() => {
                      setPage((p) => p - 1);
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                    className="glass px-4 py-2 rounded-2xl text-sm font-semibold disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <span className="text-sm tabular" style={{ color: "var(--theme-text-muted)" }}>
                    Page {page} of {totalPages}
                  </span>
                  <button
                    disabled={page >= totalPages}
                    onClick={() => {
                      setPage((p) => p + 1);
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                    className="glass px-4 py-2 rounded-2xl text-sm font-semibold disabled:opacity-40"
                  >
                    Next
                  </button>
                </nav>
              )}
            </>
          ) : (
            <div className="glass rounded-[28px] p-10 text-center space-y-3">
              <p className="font-display text-xl font-bold">
                {market === "saved" && saved.size === 0 ? "You haven't saved any jobs yet" : "No jobs match these filters"}
              </p>
              <p className="text-sm max-w-md mx-auto" style={{ color: "var(--theme-text-muted)" }}>
                {market === "saved" && saved.size === 0
                  ? "Use the star on any job to keep it here."
                  : chips.length
                  ? "Lower the minimum fit or remove a filter to see more."
                  : "Run a scan to pull new jobs from the boards."}
              </p>
              <div className="flex justify-center gap-3 pt-2">
                {chips.length > 0 && (
                  <button onClick={resetFilters} className="glass-strong px-5 py-2.5 rounded-2xl text-sm font-semibold">
                    Clear filters
                  </button>
                )}
                <button
                  onClick={() => (market === "saved" ? setMarket("global") : setScanOpen(true))}
                  className="px-5 py-2.5 rounded-2xl text-sm font-semibold text-white"
                  style={{ background: "var(--theme-primary)" }}
                >
                  {market === "saved" ? "Browse all jobs" : "Scan boards"}
                </button>
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Mobile filter sheet */}
      {sheetOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex flex-col justify-end bg-black/30 backdrop-blur-sm" onClick={() => setSheetOpen(false)}>
          <div
            className="glass-strong rounded-t-[28px] p-5 max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="Filters"
          >
            <div className="flex items-center justify-between mb-4">
              <span className="font-display text-lg font-bold">Filters</span>
              <button onClick={() => setSheetOpen(false)} className="p-2 rounded-full hover:bg-black/5" aria-label="Close filters">
                <X size={18} />
              </button>
            </div>
            {rail}
            <button
              onClick={() => setSheetOpen(false)}
              className="w-full mt-6 py-3 rounded-2xl font-semibold text-white"
              style={{ background: "var(--theme-primary)" }}
            >
              Show {results.length} jobs
            </button>
          </div>
        </div>
      )}

      <JobPreviewDrawer
        job={previewJob}
        isOpen={!!previewJob}
        onClose={() => setPreviewJob(null)}
        onTailorClick={setTailorJob}
        onApplyClick={openApply}
        onToggleSave={toggleSave}
        isSaved={previewJob ? saved.has(previewJob.url) : false}
      />
      <ScanModal
        isOpen={scanOpen}
        onClose={() => setScanOpen(false)}
        onScanComplete={() => {
          setScanOpen(false);
          fetchJobs(true);
        }}
      />
      <TailorModal job={tailorJob} isOpen={!!tailorJob} onClose={() => setTailorJob(null)} />
      <ApplyModal
        job={applyJob}
        isOpen={!!applyJob}
        onClose={() => setApplyJob(null)}
        onApplicationSubmitted={(j) => sendFeedback(j, "apply")}
      />
    </SalvoConnectionGuard>
  );
}
