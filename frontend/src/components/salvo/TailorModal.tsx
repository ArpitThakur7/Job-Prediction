"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { salvoClient, SalvoJob, TailorResult } from "@/lib/salvoClient";
import { useApp } from "@/context/AppContext";

interface TailorModalProps {
  job: SalvoJob | null;
  isOpen: boolean;
  onClose: () => void;
}

export const TailorModal: React.FC<TailorModalProps> = ({ job, isOpen, onClose }) => {
  const { currentThemeColors } = useApp();
  const [mode, setMode] = useState<"api" | "manual">("api");
  const [loading, setLoading] = useState(false);
  const [prepLoading, setPrepLoading] = useState(false);
  const [result, setResult] = useState<TailorResult | null>(null);
  const [manualPrompt, setManualPrompt] = useState<{ systemPrompt: string; jdText: string } | null>(null);
  const [manualInputJson, setManualInputJson] = useState("");
  const [prepStatus, setPrepStatus] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !job) return null;

  const handleRunTailor = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      if (mode === "manual") {
        const res = await salvoClient.tailorJob(job.url, { mode: "manual" });
        if (res.systemPrompt) {
          setManualPrompt({ systemPrompt: res.systemPrompt, jdText: res.jdText || "" });
        } else {
          setResult(res);
        }
      } else {
        const res = await salvoClient.tailorJob(job.url, { mode: "api" });
        if (!res.ok) throw new Error(res.error || "Tailoring failed");
        setResult(res);
      }
    } catch (err: any) {
      setError(err.message || "Failed to tailor resume");
    } finally {
      setLoading(false);
    }
  };

  const handleFinalizeManual = async () => {
    if (!manualInputJson.trim()) return;
    setLoading(true);
    setError(null);
    try {
      let parsed;
      try {
        parsed = JSON.parse(manualInputJson);
      } catch {
        throw new Error("Invalid JSON. Please ensure you pasted a valid JSON object matching the contract.");
      }
      const res = await salvoClient.tailorJob(job.url, { mode: "manual", manualJson: parsed });
      if (!res.ok) throw new Error(res.error || "Failed to finalize manual tailoring");
      setResult(res);
      setManualPrompt(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLaunchPrep = async () => {
    setPrepLoading(true);
    setError(null);
    try {
      const res = await salvoClient.prepJob(job.url);
      if (!res.ok) throw new Error(res.error || "Failed to prep application");
      setPrepStatus(res);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setPrepLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="relative w-full max-w-2xl p-6 rounded-2xl border shadow-2xl overflow-hidden my-8"
          style={{
            backgroundColor: currentThemeColors.panelBg || "rgba(15, 23, 42, 0.95)",
            borderColor: currentThemeColors.panelBorder || "rgba(255, 255, 255, 0.15)",
            color: currentThemeColors.textColor || "#F8FAFC",
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-white/10">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">🎯</span>
                <h3 className="font-bold text-lg">{job.title}</h3>
              </div>
              <p className="text-xs text-slate-400 font-mono">{job.company} · {job.location || "Remote"}</p>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
            >
              ✕
            </button>
          </div>

          {/* Mode Switcher */}
          {!result && !manualPrompt && (
            <div className="my-5">
              <label className="block text-xs font-mono font-medium text-slate-400 mb-2">TAILORING ENGINE MODE</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setMode("api")}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    mode === "api"
                      ? "border-cyan-400 bg-cyan-500/15 shadow-[0_0_15px_rgba(6,182,212,0.2)]"
                      : "border-white/10 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  <div className="font-bold text-xs flex items-center gap-1.5 mb-1 text-cyan-300">
                    <span>⚡</span> API Mode (Automated)
                  </div>
                  <p className="text-[11px] text-slate-400">Claude Haiku / Gemini Flash via API key (~$0.02)</p>
                </button>
                <button
                  type="button"
                  onClick={() => setMode("manual")}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    mode === "manual"
                      ? "border-emerald-400 bg-emerald-500/15 shadow-[0_0_15px_rgba(16,185,129,0.2)]"
                      : "border-white/10 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  <div className="font-bold text-xs flex items-center gap-1.5 mb-1 text-emerald-300">
                    <span>🆓</span> Manual Mode (Zero-Cost)
                  </div>
                  <p className="text-[11px] text-slate-400">Copy system prompt to any free chat & paste back JSON</p>
                </button>
              </div>

              <div className="mt-4 p-3.5 rounded-xl border border-white/5 bg-black/20 text-xs text-slate-300 space-y-1.5">
                <div className="font-bold text-cyan-400 flex items-center gap-1.5 font-mono">
                  <span>🛡️</span> Truth-Bounded Guarantee
                </div>
                <p className="text-[11px] leading-relaxed text-slate-400">
                  The LLM sees only your master resume and verified facts in portfolio.yaml. It may re-emphasize and align wording with the JD, but can NEVER invent employers, titles, dates, or skills.
                </p>
              </div>
            </div>
          )}

          {/* Manual Mode Prompt Viewer */}
          {manualPrompt && (
            <div className="my-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-emerald-400 font-bold">1. Copy Prompt to any Free Chat</span>
                <button
                  onClick={() => navigator.clipboard.writeText(`${manualPrompt.systemPrompt}\n\n${manualPrompt.jdText}`)}
                  className="px-2.5 py-1 rounded bg-white/10 hover:bg-white/20 text-xs font-mono transition-colors"
                >
                  📋 Copy Full Prompt
                </button>
              </div>
              <textarea
                readOnly
                value={`${manualPrompt.systemPrompt}\n\n${manualPrompt.jdText}`}
                className="w-full h-32 p-2.5 text-[10px] font-mono rounded-lg bg-black/40 border border-white/10 text-slate-300 resize-none"
              />
              <div className="pt-2">
                <span className="text-xs font-mono text-emerald-400 font-bold block mb-1">2. Paste Back Structured JSON</span>
                <textarea
                  placeholder='Paste { "resume": {...}, "coverLetter": "...", "keywordReport": {...} } here'
                  value={manualInputJson}
                  onChange={(e) => setManualInputJson(e.target.value)}
                  className="w-full h-28 p-2.5 text-xs font-mono rounded-lg bg-black/40 border border-white/10 text-slate-200 focus:border-emerald-400 focus:outline-none"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setManualPrompt(null)}
                  className="px-3 py-1.5 rounded-lg border border-white/10 text-xs font-mono"
                >
                  Cancel
                </button>
                <button
                  onClick={handleFinalizeManual}
                  disabled={loading || !manualInputJson.trim()}
                  className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-bold text-xs font-mono disabled:opacity-50"
                >
                  {loading ? "Compiling ATS PDF..." : "Compile & Guard Resume"}
                </button>
              </div>
            </div>
          )}

          {/* Result View */}
          {result && result.meta && (
            <div className="my-4 space-y-4">
              <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-emerald-400 text-sm flex items-center gap-1.5">
                    <span>✨</span> Tailored ATS Resume Ready
                  </span>
                  <span className="text-xs font-mono text-slate-400">
                    Single Page: {result.meta.pageCount === 1 ? "✅ Passed (1 page)" : `⚠️ ${result.meta.pageCount} pages`}
                  </span>
                </div>

                {/* Truth Guard Status */}
                {result.meta.truthReport && (
                  <div className="text-[11px] font-mono text-slate-300 py-1 border-t border-white/5 mt-2">
                    {result.meta.truthReport.verified ? (
                      <span className="text-emerald-400">✓ All claims verified against master fact bank.</span>
                    ) : (
                      <span className="text-amber-400">
                        ⚠️ Sanitized {result.meta.truthReport.violations.length} ungrounded assertions.
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Keyword Gap Report */}
              <div className="p-3.5 rounded-xl border border-white/10 bg-black/20 text-xs">
                <h4 className="font-mono font-bold text-slate-300 mb-2">ATS KEYWORD GAP REPORT</h4>
                <div className="space-y-2">
                  <div>
                    <span className="text-[10px] font-mono text-emerald-400 block mb-1">
                      MATCHED ({result.meta.keywordReport?.matched?.length || 0})
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {result.meta.keywordReport?.matched?.map((k, i) => (
                        <span key={i} className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                          {k}
                        </span>
                      ))}
                    </div>
                  </div>
                  {result.meta.keywordReport?.missing?.length > 0 && (
                    <div>
                      <span className="text-[10px] font-mono text-amber-400 block mb-1">
                        HONEST SKILL GAPS ({result.meta.keywordReport?.missing?.length || 0})
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {result.meta.keywordReport?.missing?.map((k, i) => (
                          <span key={i} className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                            {k}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Golden Rule Assisted Apply Box */}
              <div className="p-4 rounded-xl border border-cyan-500/30 bg-cyan-950/20 text-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="font-bold text-cyan-300 text-sm flex items-center gap-1.5 font-mono">
                    <span>🤖</span> Assisted Form Pre-filler (Playwright)
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-cyan-500/30 text-cyan-300 bg-cyan-500/10">
                    GOLDEN RULE PROTECTED
                  </span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">
                  Playwright will open a visible Chromium browser on your machine, navigate to the application, fill your contact info, attach your tailored PDF, and <strong>STOP</strong>.
                  <span className="text-amber-300 font-bold block mt-1">
                    It will NEVER click Submit. Subjective screening questions and final submission belong to you.
                  </span>
                </p>

                {prepStatus ? (
                  <div className="p-3 rounded-lg bg-black/40 border border-emerald-500/30 text-xs">
                    <span className="font-bold text-emerald-400 block mb-1">
                      ✅ Form Pre-filled: {prepStatus.filled?.join(", ") || "Fields populated"}
                    </span>
                    <p className="text-[11px] text-slate-300">{prepStatus.notice}</p>
                    {prepStatus.needsReview?.length > 0 && (
                      <div className="mt-2 text-[10px] text-amber-400">
                        Requires your answer: {prepStatus.needsReview.join(", ")}
                      </div>
                    )}
                  </div>
                ) : (
                  <button
                    onClick={handleLaunchPrep}
                    disabled={prepLoading}
                    className="w-full py-2.5 rounded-xl font-bold font-mono text-xs bg-cyan-500 hover:bg-cyan-400 text-black shadow-lg transition-all"
                  >
                    {prepLoading ? "Launching Playwright Chromium..." : "Launch Application Pre-fill (Never Submits)"}
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="my-3 p-3 rounded-xl border border-red-500/30 bg-red-950/20 text-xs text-red-300 font-mono">
              ❌ {error}
            </div>
          )}

          {/* Initial Actions */}
          {!result && !manualPrompt && (
            <div className="flex justify-end gap-3 pt-3 border-t border-white/10">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-mono text-slate-300 border border-white/10 hover:bg-white/5"
              >
                Close
              </button>
              <button
                type="button"
                onClick={handleRunTailor}
                disabled={loading}
                className="px-5 py-2 rounded-xl text-xs font-mono font-bold bg-cyan-500 hover:bg-cyan-400 text-black shadow-[0_0_20px_rgba(6,182,212,0.4)] disabled:opacity-50"
              >
                {loading ? "Generating Truth-Bounded Resume..." : "Tailor Resume"}
              </button>
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default TailorModal;
