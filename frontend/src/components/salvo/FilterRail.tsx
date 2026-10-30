"use client";

import React, { useMemo } from "react";
import { Search, X } from "lucide-react";
import { SalvoJob } from "@/lib/salvoClient";
import { fitColor, jobScore, jobSource } from "@/lib/jobScore";

export type Level = "any" | "early" | "senior";
export type Market = "global" | "india" | "saved";

export interface Filters {
  query: string;
  minFit: number;
  sources: string[];
  level: Level;
  remoteOnly: boolean;
  topic: string;
  showHidden: boolean;
}

export const defaultFilters: Filters = {
  query: "",
  minFit: 0,
  sources: [],
  level: "any",
  remoteOnly: false,
  topic: "",
  showHidden: false,
};

export const topics: { id: string; label: string; pattern: RegExp }[] = [
  { id: "ai", label: "Python and AI", pattern: /python|pytorch|tensorflow|machine learning|\bml\b|\bai\b|llm|data scien/i },
  { id: "frontend", label: "Frontend", pattern: /react|frontend|front-end|next\.?js|typescript|vue|angular/i },
  { id: "backend", label: "Backend and APIs", pattern: /backend|back-end|node|django|flask|fastapi|golang|\bjava\b|\bapi\b|postgres/i },
  { id: "data", label: "Data", pattern: /data engineer|analytics|\bsql\b|spark|airflow|dbt|warehouse/i },
  { id: "devops", label: "Cloud and DevOps", pattern: /devops|kubernetes|\bk8s\b|aws|gcp|azure|terraform|\bsre\b/i },
];

interface Props {
  jobs: SalvoJob[];
  filters: Filters;
  onChange: (next: Partial<Filters>) => void;
  onReset: () => void;
  market: Market;
  onMarket: (m: Market) => void;
  savedCount: number;
  hiddenCount: number;
  searchRef?: React.Ref<HTMLInputElement>;
}

const BUCKETS = 20;

export default function FilterRail({ jobs, filters, onChange, onReset, market, onMarket, savedCount, hiddenCount, searchRef }: Props) {
  const histogram = useMemo(() => {
    const counts = new Array(BUCKETS).fill(0);
    jobs.forEach((j) => {
      counts[Math.min(BUCKETS - 1, Math.floor(jobScore(j) / (100 / BUCKETS)))]++;
    });
    return counts;
  }, [jobs]);
  const peak = Math.max(1, ...histogram);

  const sources = useMemo(() => {
    const map = new Map<string, number>();
    jobs.forEach((j) => map.set(jobSource(j), (map.get(jobSource(j)) || 0) + 1));
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }, [jobs]);

  const atOrAbove = jobs.filter((j) => jobScore(j) >= filters.minFit).length;
  const dirty = JSON.stringify({ ...filters, showHidden: false }) !== JSON.stringify({ ...defaultFilters });

  const toggleSource = (s: string) =>
    onChange({ sources: filters.sources.includes(s) ? filters.sources.filter((x) => x !== s) : [...filters.sources, s] });

  return (
    <div className="space-y-6 text-[15px]">
      {/* Search */}
      <div className="relative">
        <Search size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 opacity-50" aria-hidden />
        <input
          ref={searchRef}
          type="search"
          value={filters.query}
          onChange={(e) => onChange({ query: e.target.value })}
          placeholder="Title, company, skill…"
          aria-label="Search jobs"
          className="w-full pl-10 pr-9 py-3 rounded-2xl bg-white/70 dark:bg-white/5 border outline-none focus:ring-2"
          style={{ borderColor: "var(--glass-line)", ["--tw-ring-color" as string]: "var(--theme-primary)" }}
        />
        <kbd className="hidden lg:block absolute right-3 top-1/2 -translate-y-1/2 text-[11px] px-1.5 rounded border opacity-50" style={{ borderColor: "var(--glass-line)" }}>/</kbd>
      </div>

      {/* Market */}
      <fieldset>
        <legend className="font-semibold mb-2">Market</legend>
        <div className="grid grid-cols-3 gap-1 p-1 rounded-2xl bg-black/[0.04] dark:bg-white/[0.05]">
          {(
            [
              ["global", "Global"],
              ["india", "India"],
              ["saved", `Saved ${savedCount}`],
            ] as [Market, string][]
          ).map(([id, label]) => (
            <button
              key={id}
              onClick={() => onMarket(id)}
              aria-pressed={market === id}
              className={`py-2 rounded-xl text-sm font-semibold transition-colors ${market === id ? "bg-white dark:bg-white/15 shadow-sm" : "opacity-70 hover:opacity-100"}`}
            >
              {label}
            </button>
          ))}
        </div>
      </fieldset>

      {/* Fit score with distribution */}
      <fieldset>
        <div className="flex items-baseline justify-between mb-2">
          <legend className="font-semibold">Minimum fit</legend>
          <span className="text-sm font-bold tabular" style={{ color: fitColor(filters.minFit || 100) }}>
            {filters.minFit}%
          </span>
        </div>
        <div className="flex items-end gap-[2px] h-12 mb-2" aria-hidden>
          {histogram.map((c, i) => {
            const bucketStart = i * (100 / BUCKETS);
            const on = bucketStart + 100 / BUCKETS > filters.minFit;
            return (
              <span
                key={i}
                className="flex-1 rounded-t-[3px] transition-opacity"
                style={{ height: `${Math.max(4, (c / peak) * 100)}%`, background: fitColor(bucketStart + 2), opacity: on ? 0.9 : 0.18 }}
              />
            );
          })}
        </div>
        <input
          type="range"
          min={0}
          max={95}
          step={5}
          value={filters.minFit}
          onChange={(e) => onChange({ minFit: Number(e.target.value) })}
          className="fit-range"
          aria-label="Minimum fit score"
        />
        <p className="text-xs mt-2" style={{ color: "var(--theme-text-muted)" }}>
          {atOrAbove} of {jobs.length} jobs at {filters.minFit}% or higher
        </p>
      </fieldset>

      {/* Level */}
      <fieldset>
        <legend className="font-semibold mb-2">Level</legend>
        <div className="flex flex-wrap gap-2">
          {(
            [
              ["any", "Any"],
              ["early", "Early career"],
              ["senior", "Senior"],
            ] as [Level, string][]
          ).map(([id, label]) => (
            <Chip key={id} active={filters.level === id} onClick={() => onChange({ level: id })}>
              {label}
            </Chip>
          ))}
        </div>
      </fieldset>

      {/* Remote */}
      <label className="flex items-center justify-between cursor-pointer">
        <span className="font-semibold">Remote only</span>
        <span className="relative inline-flex">
          <input
            type="checkbox"
            className="peer sr-only"
            role="switch"
            aria-label="Remote only"
            checked={filters.remoteOnly}
            onChange={(e) => onChange({ remoteOnly: e.target.checked })}
          />
          <span className="w-11 h-6 rounded-full bg-black/15 dark:bg-white/15 peer-checked:bg-[var(--theme-primary)] transition-colors peer-focus-visible:ring-2 ring-offset-2" />
          <span className="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform peer-checked:translate-x-5" />
        </span>
      </label>

      {/* Topics */}
      <fieldset>
        <legend className="font-semibold mb-2">Topic</legend>
        <div className="flex flex-wrap gap-2">
          {topics.map((t) => (
            <Chip key={t.id} active={filters.topic === t.id} onClick={() => onChange({ topic: filters.topic === t.id ? "" : t.id })}>
              {t.label}
            </Chip>
          ))}
        </div>
      </fieldset>

      {/* Sources */}
      {sources.length > 0 && (
        <fieldset>
          <legend className="font-semibold mb-2">Job board</legend>
          <ul className="space-y-1">
            {sources.map(([s, n]) => (
              <li key={s}>
                <label className="flex items-center gap-3 py-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters.sources.includes(s)}
                    onChange={() => toggleSource(s)}
                    className="w-4 h-4 rounded accent-[var(--theme-primary)]"
                  />
                  <span className="flex-1 capitalize">{s.replace(/-/g, " ")}</span>
                  <span className="text-sm tabular" style={{ color: "var(--theme-text-muted)" }}>{n}</span>
                </label>
              </li>
            ))}
          </ul>
        </fieldset>
      )}

      <div className="flex items-center justify-between pt-1">
        {hiddenCount > 0 ? (
          <button onClick={() => onChange({ showHidden: !filters.showHidden })} className="text-sm font-semibold" style={{ color: "var(--theme-text-muted)" }}>
            {filters.showHidden ? "Hide dismissed jobs" : `Show ${hiddenCount} dismissed`}
          </button>
        ) : (
          <span />
        )}
        {dirty && (
          <button onClick={onReset} className="inline-flex items-center gap-1 text-sm font-semibold" style={{ color: "var(--theme-primary)" }}>
            <X size={14} /> Clear filters
          </button>
        )}
      </div>
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className="px-3.5 py-1.5 rounded-full text-sm font-medium border transition-colors"
      style={
        active
          ? { background: "var(--theme-primary)", color: "#fff", borderColor: "var(--theme-primary)" }
          : { borderColor: "var(--glass-line)", background: "rgba(255,255,255,0.35)" }
      }
    >
      {children}
    </button>
  );
}
