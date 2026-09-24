"use client";

import React, { useState, useEffect } from "react";
import { salvoClient } from "@/lib/salvoClient";
import { useApp } from "@/context/AppContext";

export default function ResumeHubPage() {
  const { currentThemeColors } = useApp();
  const [activeTab, setActiveTab] = useState<"resume" | "portfolio">("resume");
  const [resumeText, setResumeText] = useState("");
  const [portfolioYaml, setPortfolioYaml] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [rData, pData] = await Promise.all([
        salvoClient.getResume(),
        salvoClient.getPortfolio(),
      ]);
      setResumeText(rData.content || "");
      setPortfolioYaml(JSON.stringify(pData.portfolio || {}, null, 2));
    } catch (err) {
      console.error("Failed to load resume/portfolio facts", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSaveResume = async () => {
    setSaving(true);
    setNotice(null);
    try {
      await salvoClient.updateResume(resumeText);
      setNotice("✅ Master resume.md updated successfully!");
    } catch (err: any) {
      setNotice(`❌ Error saving: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleSavePortfolio = async () => {
    setSaving(true);
    setNotice(null);
    try {
      const parsed = JSON.parse(portfolioYaml);
      await salvoClient.updatePortfolio(parsed);
      setNotice("✅ Verified portfolio.yaml facts updated successfully!");
    } catch (err: any) {
      setNotice(`❌ Error saving JSON/YAML: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
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
            <span className="text-xl">📝</span>
            <h1 className="text-2xl font-black tracking-tight" style={{ color: currentThemeColors.textColor || "#F8FAFC" }}>
              Truth Bank & Resume Hub
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono border border-cyan-500/30 text-cyan-300 bg-cyan-500/10">
              TRUTH-BOUNDED SOURCES
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono">
            Source of truth for all tailoring. LLMs cannot invent anything not declared in these files.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab("resume")}
            className={`px-4 py-2 rounded-xl text-xs font-mono transition-all ${
              activeTab === "resume" ? "bg-cyan-500 text-black font-bold shadow-md" : "text-slate-400 hover:text-white"
            }`}
          >
            📄 Master Resume (resume.md)
          </button>
          <button
            onClick={() => setActiveTab("portfolio")}
            className={`px-4 py-2 rounded-xl text-xs font-mono transition-all ${
              activeTab === "portfolio" ? "bg-emerald-500 text-black font-bold shadow-md" : "text-slate-400 hover:text-white"
            }`}
          >
            🗃️ Verified Facts (portfolio.yaml)
          </button>
        </div>
      </div>

      {notice && (
        <div className="p-3 rounded-xl border border-white/10 bg-black/40 text-xs font-mono text-center">
          {notice}
        </div>
      )}

      {loading ? (
        <div className="py-24 flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 border-4 border-cyan-500/20 border-t-cyan-400 rounded-full animate-spin" />
          <span className="text-xs font-mono text-slate-400">Loading master facts...</span>
        </div>
      ) : activeTab === "resume" ? (
        /* MASTER RESUME EDITOR */
        <div
          className="p-6 rounded-3xl border backdrop-blur-xl shadow-xl space-y-4"
          style={{
            backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)",
            borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)",
          }}
        >
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <div>
              <h2 className="font-bold text-sm text-slate-200">data/resume/resume.md</h2>
              <p className="text-[11px] text-slate-400 font-mono">
                Your canonical background: contact info, education, work history, and baseline skill list.
              </p>
            </div>
            <button
              onClick={handleSaveResume}
              disabled={saving}
              className="px-4 py-2 rounded-xl text-xs font-mono font-bold bg-cyan-500 hover:bg-cyan-400 text-black shadow-md disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save resume.md"}
            </button>
          </div>

          <textarea
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            rows={22}
            className="w-full p-4 rounded-xl bg-black/40 border border-white/10 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-400 resize-y leading-relaxed"
            placeholder="# Your Name&#10;Email | Phone | Location&#10;&#10;## Education&#10;...&#10;&#10;## Experience&#10;..."
          />
        </div>
      ) : (
        /* PORTFOLIO FACTS EDITOR */
        <div
          className="p-6 rounded-3xl border backdrop-blur-xl shadow-xl space-y-4"
          style={{
            backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.75)",
            borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.1)",
          }}
        >
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <div>
              <h2 className="font-bold text-sm text-slate-200">config/portfolio.yaml</h2>
              <p className="text-[11px] text-slate-400 font-mono">
                Verified repository facts: real projects, metrics, and technologies. The tailor selects from these.
              </p>
            </div>
            <button
              onClick={handleSavePortfolio}
              disabled={saving}
              className="px-4 py-2 rounded-xl text-xs font-mono font-bold bg-emerald-500 hover:bg-emerald-400 text-black shadow-md disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save portfolio.yaml"}
            </button>
          </div>

          <textarea
            value={portfolioYaml}
            onChange={(e) => setPortfolioYaml(e.target.value)}
            rows={22}
            className="w-full p-4 rounded-xl bg-black/40 border border-white/10 text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-400 resize-y leading-relaxed"
          />
        </div>
      )}
    </div>
  );
}
