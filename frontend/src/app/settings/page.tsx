"use client";

import React, { useState } from "react";
import { useApp } from "@/context/AppContext";
import Card3DTilt from "@/components/3d/Card3DTilt";

export default function Settings() {
  const {
    groqApiKey,
    pineconeApiKey,
    openaiApiKey,
    anthropicApiKey,
    geminiApiKey,
    openrouterApiKey,
    primaryProvider,
    infraStatus,
    setGroqApiKey,
    setPineconeApiKey,
    setOpenaiApiKey,
    setAnthropicApiKey,
    setGeminiApiKey,
    setOpenrouterApiKey,
    setPrimaryProvider,
    refreshDiagnostics,
  } = useApp();

  const [groqInput, setGroqInput] = useState<string>(groqApiKey);
  const [pineconeInput, setPineconeInput] = useState<string>(pineconeApiKey);
  const [openaiInput, setOpenaiInput] = useState<string>(openaiApiKey);
  const [anthropicInput, setAnthropicInput] = useState<string>(anthropicApiKey);
  const [geminiInput, setGeminiInput] = useState<string>(geminiApiKey);
  const [openrouterInput, setOpenrouterInput] = useState<string>(openrouterApiKey);

  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const handleSaveKeys = (e: React.FormEvent) => {
    e.preventDefault();
    setGroqApiKey(groqInput);
    setPineconeApiKey(pineconeInput);
    setOpenaiApiKey(openaiInput);
    setAnthropicApiKey(anthropicInput);
    setGeminiApiKey(geminiInput);
    setOpenrouterApiKey(openrouterInput);

    setSaveSuccess("API keys & multi-provider preferences saved securely!");
    setTimeout(() => setSaveSuccess(null), 3000);
    refreshDiagnostics();
  };

  const handleRefreshDiagnostics = async () => {
    setRefreshing(true);
    await refreshDiagnostics();
    setRefreshing(false);
  };

  const providers = [
    { id: "groq", name: "Groq (LLaMA 3.3)", free: true, active: infraStatus.groq },
    { id: "gemini", name: "Gemini (1.5 Flash)", free: true, active: infraStatus.gemini },
    { id: "openrouter", name: "OpenRouter (Free Tier)", free: true, active: infraStatus.openrouter },
    { id: "openai", name: "OpenAI (GPT-4o)", free: false, active: infraStatus.openai },
    { id: "anthropic", name: "Anthropic (Claude)", free: false, active: infraStatus.anthropic },
  ];

  return (
    <div className="space-y-8 max-w-5xl mx-auto">

      {/* Primary LLM Provider Selector */}
      <Card3DTilt maxDegree={6} className="glass-panel p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="text-lg font-bold font-heading text-slate-900 flex items-center gap-2">
              <span>🤖</span> Primary Chat LLM Engine & Auto-Fallback Pipeline
            </h3>
            <p className="text-xs text-slate-500">
              Select your primary AI provider. If rate limits (429) or errors occur, the system automatically fails over to the remaining providers in your chain.
            </p>
          </div>
          <span className="px-3 py-1 bg-[#EEF2FF] text-[#4F46E5] rounded-full text-xs font-mono font-bold border border-[#c7d2fe] whitespace-nowrap">
            ⛓️ Auto-Failover Active
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {providers.map((p) => {
            const isSelected = primaryProvider === p.id;
            return (
              <button
                key={p.id}
                onClick={() => setPrimaryProvider(p.id)}
                className={`py-3 px-3 rounded-2xl border text-xs font-bold font-heading transition-all cursor-pointer flex flex-col justify-center items-center gap-1.5 shadow-xs ${
                  isSelected
                    ? "bg-[#4F46E5] text-white border-[#4F46E5] shadow-md"
                    : "bg-white text-slate-700 hover:bg-slate-50 border-slate-200"
                }`}
              >
                <span className="text-center">{p.name}</span>
                <div className="flex items-center gap-1">
                  {p.free && <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${isSelected ? "bg-white/20 text-white" : "bg-emerald-100 text-emerald-700"}`}>FREE</span>}
                  <span className={`w-2 h-2 rounded-full ${p.active ? "bg-[#10B981]" : "bg-orange-400"}`} />
                </div>
              </button>
            );
          })}
        </div>
      </Card3DTilt>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

        {/* API Keys Form */}
        <Card3DTilt maxDegree={6} className="lg:col-span-8 glass-panel p-6 shadow-xl space-y-5">
          <div>
            <h3 className="text-lg font-bold font-heading text-slate-900">🔑 API Credentials (Free & Premium Providers)</h3>
            <p className="text-xs text-slate-500 mt-0.5">Keys are saved locally in your browser — never sent to external third parties.</p>
          </div>

          {saveSuccess && (
            <div className="bg-emerald-50 border border-emerald-200 text-[#10B981] p-3 rounded-xl text-xs font-bold font-mono">
              ✓ {saveSuccess}
            </div>
          )}

          <form onSubmit={handleSaveKeys} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-500 font-mono uppercase tracking-wider flex items-center justify-between">
                  <span>Groq API Key</span>
                  <span className="text-[10px] text-emerald-600 font-bold">Fast Free Tier</span>
                </label>
                <input
                  type="password"
                  placeholder="gsk_..."
                  value={groqInput}
                  onChange={(e) => setGroqInput(e.target.value)}
                  className="w-full bg-white border border-[#E0E7FF] rounded-xl px-4 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#4F46E5]/40 shadow-xs"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-500 font-mono uppercase tracking-wider flex items-center justify-between">
                  <span>Gemini API Key</span>
                  <span className="text-[10px] text-emerald-600 font-bold">Google Free Quota</span>
                </label>
                <input
                  type="password"
                  placeholder="AIzaSy..."
                  value={geminiInput}
                  onChange={(e) => setGeminiInput(e.target.value)}
                  className="w-full bg-white border border-[#E0E7FF] rounded-xl px-4 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#4F46E5]/40 shadow-xs"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-500 font-mono uppercase tracking-wider flex items-center justify-between">
                  <span>OpenRouter API Key</span>
                  <span className="text-[10px] text-emerald-600 font-bold">20+ Free Models</span>
                </label>
                <input
                  type="password"
                  placeholder="sk-or-v1-..."
                  value={openrouterInput}
                  onChange={(e) => setOpenrouterInput(e.target.value)}
                  className="w-full bg-white border border-[#E0E7FF] rounded-xl px-4 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#4F46E5]/40 shadow-xs"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-500 font-mono uppercase tracking-wider">Pinecone API Key</label>
                <input
                  type="password"
                  placeholder="pcsk_..."
                  value={pineconeInput}
                  onChange={(e) => setPineconeInput(e.target.value)}
                  className="w-full bg-white border border-[#E0E7FF] rounded-xl px-4 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#4F46E5]/40 shadow-xs"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-500 font-mono uppercase tracking-wider">OpenAI API Key</label>
                <input
                  type="password"
                  placeholder="sk-..."
                  value={openaiInput}
                  onChange={(e) => setOpenaiInput(e.target.value)}
                  className="w-full bg-white border border-[#E0E7FF] rounded-xl px-4 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#4F46E5]/40 shadow-xs"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-500 font-mono uppercase tracking-wider">Anthropic API Key</label>
                <input
                  type="password"
                  placeholder="sk-ant-..."
                  value={anthropicInput}
                  onChange={(e) => setAnthropicInput(e.target.value)}
                  className="w-full bg-white border border-[#E0E7FF] rounded-xl px-4 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#4F46E5]/40 shadow-xs"
                />
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                className="btn-primary-glow px-8 py-3 rounded-full font-heading font-extrabold text-xs cursor-pointer shadow-md"
              >
                Save All Credentials →
              </button>
            </div>
          </form>
        </Card3DTilt>

        {/* Live Diagnostics */}
        <Card3DTilt maxDegree={6} className="lg:col-span-4 glass-panel p-6 shadow-xl space-y-4">
          <h3 className="text-lg font-bold font-heading text-slate-900">System Status</h3>

          <div className="space-y-3 font-mono text-xs">
            {[
              { label: "FastAPI Backend", ok: infraStatus.backend },
              { label: "MongoDB Store", ok: infraStatus.mongodb },
              { label: "Pinecone Vectors", ok: infraStatus.pinecone },
              { label: "Groq API", ok: infraStatus.groq },
              { label: "OpenRouter API", ok: infraStatus.openrouter },
              { label: "Gemini API", ok: geminiApiKey.length > 5 },
            ].map((s) => (
              <div key={s.label} className="flex justify-between items-center py-2 border-b border-[#E0E7FF]">
                <span className="text-slate-600">{s.label}</span>
                <span className={`px-2.5 py-0.5 rounded-full font-bold ${s.ok ? "bg-emerald-50 text-[#10B981] border border-emerald-200" : "bg-orange-50 text-orange-600 border border-orange-200"}`}>
                  {s.ok ? "Active" : "Standby"}
                </span>
              </div>
            ))}
          </div>

          <button
            onClick={handleRefreshDiagnostics}
            disabled={refreshing}
            className="w-full py-2.5 rounded-full bg-slate-900 hover:bg-slate-800 text-white font-mono font-bold text-xs transition-all cursor-pointer shadow-xs"
          >
            {refreshing ? "Checking..." : "Refresh Status 🔄"}
          </button>

          {/* Context Memory Status */}
          <div className="pt-3 border-t border-[#E0E7FF] space-y-2 text-xs font-mono">
            <div className="flex justify-between"><span className="text-slate-500">Context Memory:</span><span className="font-bold text-emerald-600">Dual-Layer Active</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Redis Buffer:</span><span className="font-bold text-slate-900">{infraStatus.redis ? "Redis Enabled" : "In-Memory Fallback"}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Auto-Failover:</span><span className="font-bold text-indigo-600">5-Tier Chained</span></div>
          </div>
        </Card3DTilt>

      </div>
    </div>
  );
}
