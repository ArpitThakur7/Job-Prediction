"use client";

import React, { useState, useEffect, useCallback } from "react";
import { salvoClient, SalvoApiError } from "@/lib/salvoClient";
import SalvoConnectionGuard from "@/components/salvo/SalvoConnectionGuard";
import ScoringWeightsEditor from "@/components/salvo/ScoringWeightsEditor";
import { useApp } from "@/context/AppContext";
import { useToast } from "@/context/ToastContext";

export default function SalvoSettingsPage() {
  const { currentThemeColors } = useApp();
  const { addToast } = useToast();
  const [profileText, setProfileText] = useState("");
  const [health, setHealth] = useState<any>(null);
  const [providerHealth, setProviderHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [pData, hData] = await Promise.all([
        salvoClient.getProfile(),
        salvoClient.getHealth(),
      ]);
      setProfileText(JSON.stringify(pData.profile || {}, null, 2));
      setHealth(hData);

      // Fetch provider health if engine is online
      if (hData.status === "online") {
        try {
          const ph = await salvoClient.getProviderHealth();
          setProviderHealth(ph);
        } catch {}
      }
    } catch (err) {
      console.error("Failed to load salvo settings", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSaveProfile = useCallback(async () => {
    setSaving(true);
    setNotice(null);
    try {
      const parsed = JSON.parse(profileText);
      await salvoClient.updateProfile(parsed);
      addToast({ type: "success", title: "Profile saved", message: "Search profile configuration updated." });
      setNotice(null);
    } catch (err: any) {
      setNotice(`❌ Error saving: ${err.message}`);
      addToast({ type: "error", title: "Invalid JSON", message: err.message });
    } finally {
      setSaving(false);
    }
  }, [profileText, addToast]);

  // Keyboard shortcut Ctrl+S / Cmd+S
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        handleSaveProfile();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleSaveProfile]);

  return (
    <SalvoConnectionGuard>
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Banner */}
      <div
        className="p-6 rounded-3xl border backdrop-blur-xl shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4"
        style={{
          backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)",
          borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)",
        }}
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">⚙️</span>
            <h1 className="text-2xl font-black tracking-tight" style={{ color: currentThemeColors.textColor || "#F8FAFC" }}>
              Salvo Engine Settings
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono border border-cyan-500/30 text-cyan-300 bg-cyan-500/10">
              LOCAL COMPANION ENGINE
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono">
            Profile search filters, scoring weights, board registry health, and LLM provider configuration
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            className="px-3 py-2 rounded-xl text-xs font-mono border border-white/10 text-slate-300 hover:text-white"
          >
            🔄 Refresh Health
          </button>
        </div>
      </div>

      {notice && (
        <div className="p-3 rounded-xl border border-white/10 bg-black/40 text-xs font-mono text-center">
          {notice}
        </div>
      )}

      {/* Engine Status Diagnostic Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 font-mono text-xs">
        <div className="p-4 rounded-2xl border border-white/10 bg-black/20">
          <span className="text-slate-400 text-[10px] block mb-1">ENGINE STATUS</span>
          <div className="flex items-center gap-2 font-bold text-sm">
            <span className={`w-2.5 h-2.5 rounded-full ${health?.status === "online" ? "bg-emerald-400 animate-pulse" : "bg-red-500"}`} />
            <span className={health?.status === "online" ? "text-emerald-400" : "text-red-400"}>
              {health?.status === "online" ? "Online (127.0.0.1:4173)" : "Offline"}
            </span>
          </div>
        </div>

        <div className="p-4 rounded-2xl border border-white/10 bg-black/20">
          <span className="text-slate-400 text-[10px] block mb-1">DISCOVERY PROVIDERS</span>
          <span className="text-sm font-bold text-cyan-400">
            {health?.providersCount || 8} Active Public Adapters
          </span>
        </div>

        <div className="p-4 rounded-2xl border border-white/10 bg-black/20">
          <span className="text-slate-400 text-[10px] block mb-1">EXCEL STORE SYNC</span>
          <span className="text-sm font-bold text-emerald-400">
            {health?.excelStoreConnected ? "Connected (applications.xlsx)" : "Connecting..."}
          </span>
        </div>

        <div className="p-4 rounded-2xl border border-white/10 bg-black/20">
          <span className="text-slate-400 text-[10px] block mb-1">AUTOMATED SUBMIT</span>
          <span className="text-sm font-bold text-amber-400">
            Disabled (Golden Rule)
          </span>
        </div>
      </div>

      {/* Visual Dual Scoring Weights & Gating Sliders */}
      <ScoringWeightsEditor />

      {/* Profile Editor */}
      <div
        className="p-6 rounded-3xl border backdrop-blur-xl shadow-xl space-y-4"
        style={{
          backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)",
          borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)",
        }}
      >
        <div className="flex items-center justify-between pb-3 border-b border-white/10">
          <div>
            <h2 className="font-bold text-sm text-slate-200">config/profile.yaml (Search Profile & Triage Rules)</h2>
            <p className="text-[11px] text-slate-400 font-mono">
              Controls target titles, exclusion guards, location gates, primary/secondary stack weights, and daily targets.
            </p>
          </div>
          <button
            onClick={handleSaveProfile}
            disabled={saving}
            className="px-4 py-2 rounded-xl text-xs font-mono font-bold bg-cyan-500 hover:bg-cyan-400 text-black shadow-md disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Profile"}
          </button>
        </div>

        {loading ? (
          <div className="py-12 text-center text-xs font-mono text-slate-400">Loading profile configuration...</div>
        ) : (
          <textarea
            value={profileText}
            onChange={(e) => setProfileText(e.target.value)}
            rows={22}
            className="w-full p-4 rounded-xl bg-black/40 border border-white/10 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-400 resize-y leading-relaxed"
          />
        )}
      </div>

      {/* Provider Health Grid */}
      {providerHealth && providerHealth.providers && (
        <div
          className="p-6 rounded-3xl border backdrop-blur-xl shadow-xl space-y-4"
          style={{
            backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)",
            borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)",
          }}
        >
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <div>
              <h2 className="font-bold text-sm text-slate-200">Discovery Provider Status</h2>
              <p className="text-[11px] text-slate-400 font-mono">
                {providerHealth.healthy} of {providerHealth.total} providers available
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {providerHealth.providers.map((p: any) => (
              <div
                key={p.name}
                className="p-3 rounded-xl border border-white/5 bg-black/20 text-xs font-mono"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-slate-300 font-bold capitalize">{p.name}</span>
                  <span className={`w-2 h-2 rounded-full ${p.status === "available" ? "bg-emerald-400" : "bg-red-500"}`} />
                </div>
                <span className="text-[10px] text-slate-500">
                  {p.status === "available" ? "Ready" : p.error || "Error"}
                  {p.latency !== null ? ` · ${p.latency}ms` : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
    </SalvoConnectionGuard>
  );
}
