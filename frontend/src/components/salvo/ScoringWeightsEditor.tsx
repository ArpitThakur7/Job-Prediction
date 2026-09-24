"use client";

import React, { useState, useEffect } from "react";
import { salvoClient, ScoringConfig } from "@/lib/salvoClient";
import { useToast } from "@/context/ToastContext";
import Card3DTilt from "@/components/3d/Card3DTilt";

interface ScoringWeightsEditorProps {
  onWeightsChange?: (config: ScoringConfig) => void;
}

export default function ScoringWeightsEditor({ onWeightsChange }: ScoringWeightsEditorProps) {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [relevanceWeight, setRelevanceWeight] = useState(60); // 60%
  const [applyMin, setApplyMin] = useState(65);
  const [highConfidence, setHighConfidence] = useState(80);
  const [maxPerCompany, setMaxPerCompany] = useState(3);

  // Sample simulation inputs
  const [simRuleScore, setSimRuleScore] = useState(85);
  const [simMlScore, setSimMlScore] = useState(70);

  const mlWeight = 100 - relevanceWeight;

  // Calculate simulated composite score
  const simCombined = Math.round(
    ((relevanceWeight / 100) * simRuleScore) + ((mlWeight / 100) * simMlScore)
  );

  const getVerdict = (score: number) => {
    if (score >= highConfidence) return { text: "Strong Match", color: "#10b981", badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" };
    if (score >= applyMin) return { text: "Match", color: "#06b6d4", badge: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30" };
    return { text: "Moderate Match", color: "#eab308", badge: "bg-amber-500/10 text-amber-400 border-amber-500/30" };
  };

  const simVerdict = getVerdict(simCombined);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await salvoClient.getScoringConfig();
      if (data?.scoring) {
        const w = data.scoring.weights;
        const t = data.scoring.thresholds;
        if (w?.relevance !== undefined) setRelevanceWeight(Math.round(w.relevance * 100));
        if (t?.apply_min !== undefined) setApplyMin(t.apply_min);
        if (t?.high_confidence !== undefined) setHighConfidence(t.high_confidence);
        if (t?.max_per_company !== undefined) setMaxPerCompany(t.max_per_company);
      }
    } catch (err: any) {
      console.warn("Could not load scoring config:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    const config: ScoringConfig = {
      weights: {
        relevance: relevanceWeight / 100,
        prediction: mlWeight / 100,
      },
      thresholds: {
        apply_min: applyMin,
        high_confidence: highConfidence,
        max_per_company: maxPerCompany,
      },
    };

    try {
      await salvoClient.updateScoringConfig(config);
      onWeightsChange?.(config);
      addToast({
        type: "success",
        title: "Scoring Weights Updated",
        message: `Relevance: ${relevanceWeight}% · ML Match: ${mlWeight}% · Threshold: ${applyMin}`,
      });
    } catch (err: any) {
      addToast({
        type: "error",
        title: "Failed to Update Weights",
        message: err.message,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleResetDefaults = () => {
    setRelevanceWeight(60);
    setApplyMin(65);
    setHighConfidence(80);
    setMaxPerCompany(3);
    addToast({
      type: "info",
      title: "Reset to Recommended",
      message: "60% deterministic rule / 40% ML match model",
    });
  };

  if (loading) {
    return (
      <div className="p-6 rounded-3xl border border-white/10 bg-black/20 text-xs font-mono text-slate-400 text-center">
        Loading scoring parameters...
      </div>
    );
  }

  return (
    <div className="p-6 rounded-3xl border border-white/10 bg-slate-900/60 backdrop-blur-xl shadow-xl space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-white/10 gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">⚖️</span>
            <h2 className="text-sm font-bold text-slate-200">Dual Scoring Blend & Gating Thresholds</h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono border border-cyan-500/30 text-cyan-300 bg-cyan-500/10">
              CONFIG/SCORING.YAML
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-mono">
            Calibrates the balance between rule-based keyword/seniority matching and Project 1's ML match model.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleResetDefaults}
            className="px-3 py-1.5 rounded-xl text-xs font-mono border border-white/10 text-slate-400 hover:text-white transition-colors"
          >
            Defaults
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-1.5 rounded-xl text-xs font-mono font-bold bg-cyan-500 hover:bg-cyan-400 text-black shadow-md disabled:opacity-50 transition-all flex items-center gap-1.5"
          >
            <span>💾</span>
            <span>{saving ? "Saving..." : "Apply & Save"}</span>
          </button>
        </div>
      </div>

      {/* Main Sliders Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Weight Balance */}
        <div className="space-y-5">
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-slate-300 font-bold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                Rule Relevance: {relevanceWeight}%
              </span>
              <span className="text-slate-300 font-bold flex items-center gap-1.5">
                ML Predictor: {mlWeight}%
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
              </span>
            </div>

            {/* Visual Balance Bar */}
            <div className="w-full h-3 rounded-full overflow-hidden flex bg-black/40 border border-white/10">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
                style={{ width: `${relevanceWeight}%` }}
              />
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300"
                style={{ width: `${mlWeight}%` }}
              />
            </div>

            {/* Slider */}
            <input
              type="range"
              min={10}
              max={90}
              step={5}
              value={relevanceWeight}
              onChange={(e) => setRelevanceWeight(Number(e.target.value))}
              className="w-full accent-cyan-400 cursor-pointer"
            />
            <p className="text-[10px] text-slate-500 font-mono">
              Drag left for higher ML emphasis, drag right for strict keyword & seniority rules.
            </p>
          </div>

          {/* Thresholds */}
          <div className="grid grid-cols-2 gap-4 pt-2 border-t border-white/5 font-mono text-xs">
            <div className="space-y-1.5">
              <div className="flex justify-between text-slate-400">
                <span>Apply Min:</span>
                <span className="text-cyan-400 font-bold">{applyMin}/100</span>
              </div>
              <input
                type="range"
                min={40}
                max={85}
                step={5}
                value={applyMin}
                onChange={(e) => setApplyMin(Number(e.target.value))}
                className="w-full accent-cyan-400 cursor-pointer"
              />
              <span className="text-[9px] text-slate-500 block">Minimum score to auto-queue</span>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between text-slate-400">
                <span>High Confidence:</span>
                <span className="text-emerald-400 font-bold">{highConfidence}/100</span>
              </div>
              <input
                type="range"
                min={70}
                max={95}
                step={5}
                value={highConfidence}
                onChange={(e) => setHighConfidence(Number(e.target.value))}
                className="w-full accent-emerald-400 cursor-pointer"
              />
              <span className="text-[9px] text-slate-500 block">Score for glowing badge</span>
            </div>
          </div>
        </div>

        {/* Right: Live Interactive Simulation Preview */}
        <Card3DTilt maxDegree={4} scaleOnHover={1.01}>
          <div className="p-4 rounded-2xl border border-white/10 bg-black/40 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-white/5">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
                🧪 Live Simulation Sandbox
              </span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${simVerdict.badge}`}>
                {simVerdict.text}
              </span>
            </div>

            {/* Test Inputs */}
            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-2.5 rounded-xl bg-white/5 border border-white/5 space-y-1">
                <span className="text-[10px] text-slate-400 block">TEST RULE SCORE</span>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={simRuleScore}
                    onChange={(e) => setSimRuleScore(Math.max(0, Math.min(100, Number(e.target.value))))}
                    className="w-14 px-2 py-0.5 rounded bg-black/50 border border-white/10 text-cyan-400 font-bold text-center"
                  />
                  <span className="text-slate-500 text-[10px]">/ 100</span>
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-white/5 border border-white/5 space-y-1">
                <span className="text-[10px] text-slate-400 block">TEST ML PROBABILITY</span>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={simMlScore}
                    onChange={(e) => setSimMlScore(Math.max(0, Math.min(100, Number(e.target.value))))}
                    className="w-14 px-2 py-0.5 rounded bg-black/50 border border-white/10 text-emerald-400 font-bold text-center"
                  />
                  <span className="text-slate-500 text-[10px]">/ 100</span>
                </div>
              </div>
            </div>

            {/* Composite Result Orb / Gauge */}
            <div className="p-3.5 rounded-xl bg-gradient-to-r from-cyan-950/30 to-emerald-950/30 border border-cyan-500/20 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase text-slate-400 block">
                  Simulated Composite
                </span>
                <span className="text-3xl font-black font-mono" style={{ color: simVerdict.color }}>
                  {simCombined}
                  <span className="text-xs text-slate-500 font-normal">/100</span>
                </span>
              </div>

              <div className="text-right text-[11px] font-mono text-slate-400 space-y-0.5">
                <div>Rule: {Math.round((relevanceWeight / 100) * simRuleScore)} pts ({relevanceWeight}%)</div>
                <div>ML: {Math.round((mlWeight / 100) * simMlScore)} pts ({mlWeight}%)</div>
                <div className="text-[10px] text-slate-500">
                  {simCombined >= applyMin ? "✅ Passes Filter Gate" : "⚠️ Below Apply Threshold"}
                </div>
              </div>
            </div>
          </div>
        </Card3DTilt>
      </div>
    </div>
  );
}
