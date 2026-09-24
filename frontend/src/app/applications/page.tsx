"use client";

import React, { useState, useEffect } from "react";
import { salvoClient, ApplicationRecord, DailyLogEntry } from "@/lib/salvoClient";
import Card3DTilt from "@/components/3d/Card3DTilt";
import { useApp } from "@/context/AppContext";

const STATUS_COLUMNS: Array<{ key: ApplicationRecord["status"]; label: string; color: string }> = [
  { key: "discovered", label: "Discovered", color: "#64748b" },
  { key: "prepared", label: "Prepared", color: "#eab308" },
  { key: "applied", label: "Applied", color: "#06b6d4" },
  { key: "interview", label: "Interviewing", color: "#3b82f6" },
  { key: "offer", label: "Offer", color: "#10b981" },
  { key: "rejected", label: "Rejected", color: "#ef4444" },
];

export default function ApplicationsTrackerPage() {
  const { currentThemeColors } = useApp();
  const [sheets, setSheets] = useState<Record<string, ApplicationRecord[]>>({});
  const [dailyLog, setDailyLog] = useState<DailyLogEntry[]>([]);
  const [currentSheet, setCurrentSheet] = useState("Applications");
  const [viewMode, setViewMode] = useState<"kanban" | "table">("kanban");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [editingNotesUrl, setEditingNotesUrl] = useState<string | null>(null);
  const [notesDraft, setNotesDraft] = useState("");

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await salvoClient.getApplications();
      setSheets(data.sheets || {});
      setDailyLog(data.dailyLog || []);
    } catch (err) {
      console.error("Failed to load application data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleStatusChange = async (url: string, newStatus: ApplicationRecord["status"]) => {
    try {
      await salvoClient.patchApplication(url, "status", newStatus, currentSheet);
      // Optimistic update
      setSheets((prev) => {
        const list = prev[currentSheet] || [];
        return {
          ...prev,
          [currentSheet]: list.map((a) => (a.url === url ? { ...a, status: newStatus } : a)),
        };
      });
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  const handleSaveNotes = async (url: string) => {
    try {
      await salvoClient.patchApplication(url, "notes", notesDraft, currentSheet);
      setSheets((prev) => {
        const list = prev[currentSheet] || [];
        return {
          ...prev,
          [currentSheet]: list.map((a) => (a.url === url ? { ...a, notes: notesDraft } : a)),
        };
      });
      setEditingNotesUrl(null);
    } catch (err: any) {
      alert(`Notes update failed: ${err.message}`);
    }
  };

  const applications = (sheets[currentSheet] || []).filter((app) =>
    search ? app.company.toLowerCase().includes(search.toLowerCase()) ||
             app.title.toLowerCase().includes(search.toLowerCase())
           : true
  );

  // Funnel calculations
  const countStatus = (s: ApplicationRecord["status"]) =>
    applications.filter((a) => (a.status || "").toLowerCase() === s).length;

  return (
    <div className="space-y-6">
      {/* Top Banner & Export Deck */}
      <div
        className="p-6 rounded-3xl border backdrop-blur-xl shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4"
        style={{
          backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)",
          borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)",
        }}
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">📊</span>
            <h1 className="text-2xl font-black tracking-tight" style={{ color: currentThemeColors.textColor || "#F8FAFC" }}>
              Application Tracker & Pipeline
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono border border-emerald-500/30 text-emerald-300 bg-emerald-500/10">
              EXCEL SYNCHRONIZED
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono">
            Synced with data/applications.xlsx · Notes & statuses are never overwritten by scans
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex p-1 rounded-xl bg-black/30 border border-white/10 text-xs font-mono">
            {Object.keys(sheets).length > 0 ? (
              Object.keys(sheets).map((name) => (
                <button
                  key={name}
                  onClick={() => setCurrentSheet(name)}
                  className={`px-3 py-1.5 rounded-lg transition-all ${
                    currentSheet === name ? "bg-cyan-500 text-black font-bold" : "text-slate-400 hover:text-white"
                  }`}
                >
                  {name}
                </button>
              ))
            ) : (
              <span className="px-3 py-1.5 text-slate-400">Applications</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <a
              href={salvoClient.getExportUrl("xlsx")}
              download="applications.xlsx"
              className="px-3 py-2 rounded-xl text-xs font-mono font-bold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
            >
              📥 Export XLSX
            </a>
            <a
              href={salvoClient.getExportUrl("csv")}
              download="applications.csv"
              className="px-3 py-2 rounded-xl text-xs font-mono border border-white/10 text-slate-300 hover:bg-white/10 transition-colors"
            >
              CSV
            </a>
          </div>
        </div>
      </div>

      {/* 3D Funnel Telemetry */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {STATUS_COLUMNS.map((col) => {
          const count = countStatus(col.key);
          return (
            <Card3DTilt key={col.key} maxDegree={6} scaleOnHover={1.03}>
              <div
                className="p-4 rounded-2xl border backdrop-blur-md shadow-md text-center"
                style={{
                  backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)",
                  borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)",
                }}
              >
                <span className="text-[10px] font-mono uppercase tracking-wider block text-slate-400 mb-1">
                  {col.label}
                </span>
                <span className="text-2xl font-black font-mono" style={{ color: col.color }}>
                  {count}
                </span>
              </div>
            </Card3DTilt>
          );
        })}
      </div>

      {/* View Switcher and Search */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="relative w-full md:w-80">
          <input
            type="text"
            placeholder="Search tracked companies or roles..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl text-xs font-mono bg-black/20 border border-white/10 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400"
          />
          <span className="absolute left-3 top-2.5 text-slate-500 text-xs">🔍</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode("kanban")}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-colors ${
              viewMode === "kanban" ? "bg-white/20 text-white font-bold" : "text-slate-400 hover:bg-white/10"
            }`}
          >
            📋 Kanban Pipeline
          </button>
          <button
            onClick={() => setViewMode("table")}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-colors ${
              viewMode === "table" ? "bg-white/20 text-white font-bold" : "text-slate-400 hover:bg-white/10"
            }`}
          >
            📑 Excel Table
          </button>
          <button
            onClick={loadData}
            className="px-2.5 py-1.5 rounded-lg text-xs font-mono border border-white/10 text-slate-400 hover:text-white"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Main Content: Kanban or Table */}
      {loading ? (
        <div className="py-24 flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 border-4 border-cyan-500/20 border-t-cyan-400 rounded-full animate-spin" />
          <span className="text-xs font-mono text-slate-400">Loading spreadsheet data...</span>
        </div>
      ) : viewMode === "kanban" ? (
        /* KANBAN BOARD */
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3 min-h-[480px]">
          {STATUS_COLUMNS.map((col) => {
            const items = applications.filter((a) => (a.status || "discovered").toLowerCase() === col.key);
            return (
              <div
                key={col.key}
                className="flex flex-col p-3 rounded-2xl border bg-black/20 border-white/5 space-y-3"
              >
                <div className="flex items-center justify-between pb-2 border-b border-white/5">
                  <span className="font-mono font-bold text-xs" style={{ color: col.color }}>
                    {col.label}
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/10 text-slate-300">
                    {items.length}
                  </span>
                </div>

                <div className="flex-1 space-y-2.5 overflow-y-auto max-h-[640px]">
                  {items.map((app) => (
                    <div
                      key={app.url}
                      className="p-3 rounded-xl border border-white/10 bg-black/40 hover:border-cyan-500/30 transition-all text-xs space-y-2 group shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-1">
                        <span className="font-bold text-slate-200 line-clamp-1">{app.title}</span>
                        <span className="font-mono text-[10px] text-cyan-400">{app.score}%</span>
                      </div>
                      <p className="text-[11px] text-slate-400 font-mono line-clamp-1">{app.company}</p>

                      {app.notes && (
                        <p className="text-[10px] text-slate-400 font-sans italic bg-white/5 p-1.5 rounded border border-white/5">
                          "{app.notes}"
                        </p>
                      )}

                      {/* Status Selector Dropdown */}
                      <div className="pt-1 flex items-center justify-between border-t border-white/5">
                        <select
                          value={app.status || "discovered"}
                          onChange={(e) => handleStatusChange(app.url, e.target.value as any)}
                          className="text-[10px] font-mono bg-black/50 border border-white/10 rounded px-1.5 py-0.5 text-slate-300 focus:outline-none"
                        >
                          {STATUS_COLUMNS.map((s) => (
                            <option key={s.key} value={s.key}>{s.label}</option>
                          ))}
                        </select>
                        <a
                          href={app.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[10px] font-mono text-cyan-400 hover:underline"
                        >
                          ATS ↗
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* DATA TABLE VIEW */
        <div
          className="rounded-2xl border overflow-x-auto shadow-xl"
          style={{
            backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)",
            borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)",
          }}
        >
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-black/40 border-b border-white/10 text-slate-400 uppercase text-[10px]">
              <tr>
                <th className="p-3">Status</th>
                <th className="p-3">Company</th>
                <th className="p-3">Role</th>
                <th className="p-3">Score</th>
                <th className="p-3">Location</th>
                <th className="p-3">Source</th>
                <th className="p-3">User Notes</th>
                <th className="p-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {applications.map((app) => (
                <tr key={app.url} className="hover:bg-white/5 transition-colors">
                  <td className="p-3">
                    <select
                      value={app.status || "discovered"}
                      onChange={(e) => handleStatusChange(app.url, e.target.value as any)}
                      className="px-2 py-1 rounded bg-black/40 border border-white/10 text-[10px] focus:outline-none"
                    >
                      {STATUS_COLUMNS.map((s) => (
                        <option key={s.key} value={s.key}>{s.label}</option>
                      ))}
                    </select>
                  </td>
                  <td className="p-3 font-bold text-slate-100">{app.company}</td>
                  <td className="p-3">{app.title}</td>
                  <td className="p-3 text-cyan-400 font-bold">{app.score}%</td>
                  <td className="p-3 text-slate-400 text-[11px]">{app.location || "Remote"}</td>
                  <td className="p-3 text-slate-400 text-[10px]">{app.source}</td>
                  <td className="p-3 max-w-xs">
                    {editingNotesUrl === app.url ? (
                      <div className="flex gap-1.5">
                        <input
                          type="text"
                          value={notesDraft}
                          onChange={(e) => setNotesDraft(e.target.value)}
                          className="px-2 py-1 rounded bg-black/60 border border-cyan-400 text-xs text-white"
                        />
                        <button
                          onClick={() => handleSaveNotes(app.url)}
                          className="px-2 py-0.5 rounded bg-emerald-500 text-black font-bold text-[10px]"
                        >
                          ✓
                        </button>
                        <button
                          onClick={() => setEditingNotesUrl(null)}
                          className="px-1.5 py-0.5 text-slate-400 text-[10px]"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <div
                        onClick={() => { setEditingNotesUrl(app.url); setNotesDraft(app.notes || ""); }}
                        className="cursor-pointer hover:underline text-slate-400 text-[11px] truncate"
                        title="Click to edit user note"
                      >
                        {app.notes || "(click to add note)"}
                      </div>
                    )}
                  </td>
                  <td className="p-3">
                    <a
                      href={app.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400 hover:underline text-[11px]"
                    >
                      Open ATS ↗
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
