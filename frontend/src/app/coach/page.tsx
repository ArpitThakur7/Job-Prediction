"use client";

import React, { useState, useRef, useEffect } from "react";
import { useApp } from "@/context/AppContext";
import AI3DAvatarOrb from "@/components/3d/AI3DAvatarOrb";
import Card3DTilt from "@/components/3d/Card3DTilt";
import CyberBorder from "@/components/3d/CyberBorder";
import FormattedMarkdown from "@/components/FormattedMarkdown";

export default function CareerCoach() {
  const {
    chatHistory,
    addChatMessage,
    clearChat,
    infraStatus,
    apiBase,
    groqApiKey,
    openaiApiKey,
    anthropicApiKey,
    geminiApiKey,
    openrouterApiKey,
    pineconeApiKey,
    primaryProvider,
  } = useApp();

  const [inputMsg, setInputMsg] = useState<string>("");
  const [generating, setGenerating] = useState<boolean>(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const sampleQuestions = [
    { q: "How can I optimize my software engineer resume for ATS systems?", short: "ATS Resume Tips" },
    { q: "What are common system design interview questions for MERN and Node.js architectures?", short: "⚡ MERN Stack Prep" },
    { q: "How should I explain asynchronous programming, LINQ, and EF Core in a senior .NET interview?", short: "🟣 .NET / C# Prep" },
    { q: "What questions should I prepare for regarding Python FastAPI, async event loops, and LLM RAG pipelines?", short: "🐍 Python AI Prep" },
    { q: "How do Next.js Server Components, React 19, and TypeScript generics come up in technical screens?", short: "🔷 TypeScript Prep" },
  ];

  // Auto scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatHistory, generating]);

  const handleClearSession = async () => {
    clearChat();
    try {
      await fetch(`${apiBase}/chat/nextjs-client-session`, { method: "DELETE" });
    } catch (_) {}
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || generating) return;

    addChatMessage({ role: "user", content: text });
    setInputMsg("");
    setGenerating(true);

    if (infraStatus.backend) {
      try {
        const payload = {
          question: text,
          session_id: "nextjs-client-session",
          primary_provider: primaryProvider || "groq",
          groq_api_key: groqApiKey || null,
          openai_api_key: openaiApiKey || null,
          anthropic_api_key: anthropicApiKey || null,
          gemini_api_key: geminiApiKey || null,
          openrouter_api_key: openrouterApiKey || null,
          pinecone_api_key: pineconeApiKey || null,
        };

        const res = await fetch(`${apiBase}/chat/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (res.status === 200) {
          const body = await res.json();
          const data = body.data || {};
          const answer = data.answer || "";
          const sources = data.sources || [];
          const providerUsed = data.provider_used || "RAG Intelligence Engine";
          addChatMessage({ role: "bot", content: answer, sources, provider_used: providerUsed });
        } else {
          addChatMessage({
            role: "bot",
            content: `Notice (${res.status}): Utilizing Local RAG Intelligence Matrix:`,
            provider_used: "Local RAG Engine",
          });
        }
      } catch (err) {
        addChatMessage({
          role: "bot",
          content: "Local Response Matrix Active. Ensure backend API is online.",
          provider_used: "Local RAG Engine",
        });
      } finally {
        setGenerating(false);
      }
    } else {
      setTimeout(() => {
        addChatMessage({
          role: "bot",
          content: "Offline mode active. Start backend via .\\run.bat for full multi-provider AI support.",
          provider_used: "Offline Engine",
        });
        setGenerating(false);
      }, 700);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendMessage(inputMsg);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 3D AI Coach Top Header */}
      <CyberBorder glowColor="purple" active className="w-full">
        <div className="p-6 min-[821px]:p-8 flex flex-col min-[821px]:flex-row items-center justify-between gap-6">
          <div className="space-y-2 text-center min-[821px]:text-left">
            <span className="text-[10px] font-mono font-bold tracking-widest text-[#00ff88] uppercase bg-[#00ff88]/10 px-3 py-1 rounded-full border border-[#00ff88]/30">
              ⚡ Multi-Provider AI & Context Memory
            </span>
            <h1 className="text-3xl min-[821px]:text-4xl font-black font-heading text-white tracking-tight">
              3D AI Career Coach
            </h1>
            <p className="text-xs text-[#8b8fa8] max-w-xl">
              Ask real-time career questions. Powered by Groq, Gemini, OpenRouter, OpenAI, and Anthropic with automatic multi-provider fallback.
            </p>
          </div>

          <div className="shrink-0">
            <AI3DAvatarOrb isThinking={generating} size={180} />
          </div>
        </div>
      </CyberBorder>

      {/* Main Chat Interface Container */}
      <CyberBorder glowColor="cyan" className="w-full">
        <div className="flex flex-col h-[580px] rounded-[15px] overflow-hidden">
          {/* Top Bar */}
          <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-[#070913]/60 backdrop-blur-md select-none">
            <div className="flex items-center gap-3">
              <span className="w-2.5 h-2.5 rounded-full bg-[#00ff88] animate-pulse" />
              <div>
                <h4 className="text-xs font-bold text-white font-mono m-0">
                  AI RAG Assistant (Multi-Provider Chain)
                </h4>
                <p className="text-[10px] text-[#8b8fa8] font-mono m-0">
                  Primary: <span className="text-[#00ff88] uppercase font-bold">{primaryProvider}</span> • Auto-Fallback: Enabled
                </p>
              </div>
            </div>

            <button
              onClick={handleClearSession}
              className="py-1.5 px-4 rounded-xl border border-red-500/30 hover:border-red-500/60 bg-red-500/10 text-red-400 hover:text-red-300 font-bold text-xs transition-all font-mono select-none cursor-pointer"
            >
              Clear Memory Session
            </button>
          </div>

          {/* Messages Feed */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {chatHistory.length === 0 ? (
              <div className="h-full flex flex-col justify-center items-center text-center max-w-md mx-auto space-y-6">
                <div className="space-y-2">
                  <h4 className="text-base font-bold text-white font-heading">
                    How can I assist your career today?
                  </h4>
                  <p className="text-xs text-[#8b8fa8] leading-relaxed">
                    Conversations retain continuous context memory across multiple turns.
                  </p>
                </div>

                {/* Quick Prompts */}
                <div className="w-full space-y-3">
                  {sampleQuestions.map((q, idx) => (
                    <Card3DTilt key={idx} maxDegree={4} scaleOnHover={1.01} onClick={() => handleSendMessage(q.q)}>
                      <div className="w-full text-left p-3.5 rounded-xl border border-white/10 hover:border-[#00ff88]/50 bg-white/5 hover:bg-white/10 text-xs text-[#a39eff] transition-all cursor-pointer font-mono flex items-center justify-between">
                        <span>💡 {q.short}</span>
                        <span className="text-[#00ff88]">→</span>
                      </div>
                    </Card3DTilt>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {chatHistory.map((msg, index) => {
                  const isBot = msg.role === "bot";
                  return (
                    <div
                      key={index}
                      className={`flex ${isBot ? "justify-start" : "justify-end"} fade-in`}
                    >
                      <div
                        className={`max-w-[80%] rounded-2xl p-4 text-xs leading-relaxed ${
                          isBot
                            ? "bg-[#0d1121]/90 border border-white/10 text-white shadow-lg"
                            : "bg-gradient-to-r from-[#6c63ff] to-[#00ff88] text-black font-semibold shadow-lg shadow-[#6c63ff]/20"
                        }`}
                      >
                        {/* Provider Badge */}
                        {isBot && (
                          <div className="mb-2 flex items-center gap-1.5 font-mono text-[9px]">
                            <span className="px-2 py-0.5 rounded-full bg-[#00ff88]/10 text-[#00ff88] border border-[#00ff88]/30 font-bold">
                              ⚡ {msg.provider_used || "AI Engine"}
                            </span>
                          </div>
                        )}

                        <FormattedMarkdown content={msg.content} isDark={isBot} />

                        {/* Citations */}
                        {isBot && msg.sources && msg.sources.length > 0 && (
                          <div className="mt-3 pt-2.5 border-t border-white/10 space-y-1.5 text-[10px] font-mono">
                            <p className="font-bold text-[#00ff88] tracking-wider uppercase text-[8px]">
                              Vector Citations:
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {msg.sources.map((s, sIdx) => (
                                <span
                                  key={sIdx}
                                  className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-[#8b8fa8]"
                                >
                                  📖 {s.company || s.title || `Doc Chunk #${sIdx + 1}`}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {generating && (
                  <div className="flex justify-start fade-in">
                    <div className="bg-[#0d1121]/80 border border-white/10 text-[#8b8fa8] rounded-2xl px-5 py-3 text-xs flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#00ff88] animate-ping" />
                      <span className="font-mono">Chaining multi-provider AI engine...</span>
                    </div>
                  </div>
                )}
                <div ref={scrollRef} />
              </div>
            )}
          </div>

          {/* Form Input */}
          <form
            onSubmit={handleSubmit}
            className="px-6 py-4 border-t border-white/10 bg-[#070913]/80 backdrop-blur-md flex gap-3 shrink-0"
          >
            <input
              type="text"
              placeholder="Ask the 3D AI Coach anything... (Retains context memory)"
              value={inputMsg}
              onChange={(e) => setInputMsg(e.target.value)}
              disabled={generating}
              className="flex-1 bg-[#0d1121] border border-white/10 rounded-xl px-4 py-3 text-xs text-white placeholder-white/30 focus:border-[#00ff88] focus:outline-none font-mono"
            />
            <button
              type="submit"
              disabled={generating || !inputMsg.trim()}
              className="py-3 px-8 rounded-xl bg-gradient-to-r from-[#6c63ff] to-[#00ff88] text-black font-extrabold text-xs font-mono tracking-wider disabled:opacity-40 select-none cursor-pointer transition-all hover:scale-105 shadow-[0_0_20px_rgba(108,99,255,0.3)]"
            >
              Send
            </button>
          </form>
        </div>
      </CyberBorder>
    </div>
  );
}
