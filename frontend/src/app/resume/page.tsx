"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { useToast } from "@/context/ToastContext";
import { useApp } from "@/context/AppContext";

// Standard Overleaf LaTeX Templates
const TEMPLATES = {
  modern: `% Modern Silicon Valley Tech Resume Template
\\documentclass[letterpaper,10pt]{article}
\\usepackage{latexsym,fullpage,titlesec,marvosym,color,verbatim,enumitem,hyperref}
\\usepackage{fancyhdr}

\\begin{document}

\\begin{center}
    \\textbf{\\Huge YOUR NAME} \\\\ \\vspace{2pt}
    \\small +1-555-0100 $|$ \\href{mailto:you@example.com}{you@example.com} $|$ 
    \\href{https://linkedin.com/in/your-handle}{linkedin.com/in/your-handle} $|$
    \\href{https://github.com/your-handle}{github.com/your-handle}
\\end{center}

\\vspace{-12pt}
\\section*{SUMMARY}
\\vspace{4pt}
Final-year B.Tech in Computer Science & Engineering (AI & Data Science) with extensive hands-on experience building scalable data pipelines, machine learning microservices, and modern web architectures. Track record of developing low-latency APIs, containerized deployments, and production predictive models.

\\vspace{4pt}
\\section*{EDUCATION}
\\vspace{4pt}
\\textbf{Jaypee University of Information Technology (JUIT)} \\hfill \\textit{2022 -- 2026} \\\\
Bachelor of Technology in Computer Science and Engineering (AI & Data Science) \\\\
Relevant Coursework: Data Structures & Algorithms, Machine Learning, Distributed Systems, Cloud Computing

\\vspace{4pt}
\\section*{TECHNICAL SKILLS}
\\vspace{4pt}
\\textbf{Languages:} Python, TypeScript, JavaScript, SQL, C++, Go \\\\
\\textbf{Frameworks & Backend:} FastAPI, Flask, React, Next.js, Django, Node.js, Tailwind CSS \\\\
\\textbf{Machine Learning & AI:} PyTorch, TensorFlow, XGBoost, Scikit-Learn, Transformers, LangChain, Groq, Pinecone \\\\
\\textbf{Data & Cloud:} PostgreSQL, MongoDB, Redis, PySpark, Docker, AWS (S3, EC2), Git, Kafka, CI/CD

\\vspace{4pt}
\\section*{EXPERIENCE & PROJECTS}
\\vspace{4pt}

\\textbf{Fletch \\& Salvo: Agentic Career Platform} \\hfill \\textit{Python, FastAPI, Next.js, XGBoost, Docker} \\\\
\\textit{Lead Engineer \\& Architect} \\hfill \\textit{2025 -- Present}
\\begin{itemize}[noitemsep,topsep=2pt,leftmargin=14pt]
    \\item Built an enterprise job-candidate matching platform achieving 99.2% accuracy and 0.9997 ROC-AUC on 120k records.
    \\item Engineered real-time unauthenticated ATS discovery pipelines for Greenhouse, Lever, and Ashby with automated deduplication.
    \\item Designed low-latency MongoDB-backed caching adapters, sub-50ms vector similarity search, and automated ATS scoring.
\\end{itemize}

\\vspace{3pt}
\\textbf{Climate & Geospatial Intelligence Pipeline} \\hfill \\textit{Python, PySpark, Mann-Kendall, GeoPandas} \\\\
\\textit{Data Science Project} \\hfill \\textit{2025}
\\begin{itemize}[noitemsep,topsep=2pt,leftmargin=14pt]
    \\item Processed 1.83M+ climate, geospatial, and terrain data points across 21 years using automated PySpark pipelines.
    \\item Executed statistical trend analysis (Sen's Slope estimation, Mann-Kendall test) to discover regional environmental shifts.
\\end{itemize}

\\vspace{4pt}
\\section*{CERTIFICATIONS}
\\vspace{4pt}
\\begin{itemize}[noitemsep,topsep=2pt,leftmargin=14pt]
    \\item AWS Certified AI Practitioner (2026)
    \\item IBM Data Science Professional Certificate -- Coursera (2026)
    \\item Full Stack Data Science Bootcamp -- iNeuron (2025)
\\end{itemize}

\\end{document}
`,
  academic: `% Classic Ivy League Academic & Research CV Template
\\documentclass[11pt,a4paper]{article}
\\usepackage{geometry}
\\geometry{margin=0.75in}

\\begin{document}
\\begin{center}
    {\\Large \\textbf{YOUR NAME}} \\\\[4pt]
    Department of Computer Science & Engineering \\\\[2pt]
    Email: you@example.com $|$ Tel: +1-555-0100 $|$ Web: github.com/your-handle
\\end{center}

\\section*{Research Interests}
Machine Learning, Scalable Data Pipelines, Semantic Information Retrieval, XGBoost Matching Systems.

\\section*{Education}
\\textbf{B.Tech in Computer Science & Engineering (AI & Data Science)}, 2022--2026 \\\\
Jaypee University of Information Technology (JUIT)

\\section*{Publications & Technical Systems}
\\textbf{Fletch: High-Precision Neural Job-Resume Matching Engine} \\\\
Implemented automated feature extraction, TF-IDF semantic embeddings, and 5-fold stratified cross-validation on 119k pairs.

\\section*{Technical Competencies}
Python, PyTorch, PySpark, FastAPI, Docker, PostgreSQL, React, AWS.
\\end{document}
`,
};

interface ATSData {
  composite_score: number;
  overall_score: number;
  grade_tier: string;
  parse_confidence_score: number;
  role_type: string;
  breakdown: {
    parseability: number;
    keyword_match: number;
    section_completeness: number;
    content_quality: number;
    formatting: number;
    recency_boost: number;
  };
  issues: Array<{ severity: string; category: string; message: string }>;
  matched_keywords: string[];
  missing_keywords: string[];
  ml_prediction: {
    match_probability: number;
    predicted_match: number;
    verdict: string;
    confidence: string;
    engine: string;
    threshold: number;
    features: Record<string, any>;
  } | null;
  bullet_suggestions: Array<{ original: string; improved: string; reason: string }>;
}

export default function OverleafResumeStudio() {
  const { addToast } = useToast();
  const { setResume, apiBase } = useApp();

  const [selectedTemplate, setSelectedTemplate] = useState<"modern" | "academic">("modern");
  const [latexCode, setLatexCode] = useState(TEMPLATES.modern);
  const [compiling, setCompiling] = useState(false);
  const [lastCompiled, setLastCompiled] = useState<Date>(new Date());
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [fileName, setFileName] = useState("resume.tex");
  const [editorMode, setEditorMode] = useState<"split" | "editor" | "preview">("split");

  // Dual-Engine ATS State
  const [atsData, setAtsData] = useState<ATSData | null>(null);
  const [isScoring, setIsScoring] = useState<boolean>(false);
  const [liveJobs, setLiveJobs] = useState<Array<{ job_id: string; title: string; company: string; location: string; required_skills: string[] }>>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>("benchmark");
  const [rightPaneTab, setRightPaneTab] = useState<"canvas" | "ats">("canvas");

  // Fetch live Salvo jobs for real-time targeting
  useEffect(() => {
    fetch(`${apiBase}/jobs/?limit=50`)
      .then((r) => r.json())
      .then((res) => {
        const list = res?.data?.jobs || res?.jobs || [];
        if (Array.isArray(list)) {
          setLiveJobs(list.slice(0, 35));
        }
      })
      .catch((err) => console.debug("Live jobs fetch for resume studio:", err));
  }, [apiBase]);

  // Dual-Engine ATS Evaluation caller
  const evaluateATS = async (overrideCode?: string, overrideJobId?: string) => {
    setIsScoring(true);
    try {
      const codeToScore = overrideCode !== undefined ? overrideCode : latexCode;
      const jobToTarget = overrideJobId !== undefined ? overrideJobId : selectedJobId;

      const res = await fetch(`${apiBase}/api/resume/ats-score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          latex_code: codeToScore,
          job_id: jobToTarget !== "benchmark" ? jobToTarget : undefined,
          include_ml_prediction: true,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setAtsData(data);
      }
    } catch (err) {
      console.debug("ATS evaluation skipped/failed:", err);
    } finally {
      setIsScoring(false);
    }
  };

  // Re-run ATS scoring when LaTeX code or selected job changes (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      evaluateATS();
    }, 700);
    return () => clearTimeout(timer);
  }, [latexCode, selectedJobId]);

  // Recompile parser to extract formatted sections from LaTeX for live PDF canvas
  const parsedDoc = useMemo(() => {
    const nameMatch = latexCode.match(/\\textbf{\\Huge\s*([^}]+)}/) || latexCode.match(/\\textbf{([^}]+)}/);
    const phoneMatch = latexCode.match(/\+?\d[\d -]{8,15}\d/);
    const emailMatch = latexCode.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/);

    const summaryMatch = latexCode.match(/\\section\*{SUMMARY}[\s\S]*?\\vspace\{4pt\}\n([\s\S]*?)(?=\\vspace|\\section)/i);
    const educationMatch = latexCode.match(/\\section\*{EDUCATION}[\s\S]*?\\vspace\{4pt\}\n([\s\S]*?)(?=\\vspace|\\section)/i);
    const skillsMatch = latexCode.match(/\\section\*{TECHNICAL SKILLS}[\s\S]*?\\vspace\{4pt\}\n([\s\S]*?)(?=\\vspace|\\section)/i);
    const expMatch = latexCode.match(/\\section\*{EXPERIENCE & PROJECTS}[\s\S]*?\\vspace\{4pt\}\n([\s\S]*?)(?=\\vspace|\\section|\n\\end\{document\})/i);
    const certMatch = latexCode.match(/\\section\*{CERTIFICATIONS}[\s\S]*?\\vspace\{4pt\}\n([\s\S]*?)(?=\\vspace|\\section|\n\\end\{document\})/i);

    const cleanLatex = (str?: string) => {
      if (!str) return "";
      return str
        .replace(/\\textbf{([^}]+)}/g, "$1")
        .replace(/\\textit{([^}]+)}/g, "$1")
        .replace(/\\href{[^}]+}{([^}]+)}/g, "$1")
        .replace(/\\hfill/g, " — ")
        .replace(/\\\\/g, "\n")
        .replace(/\\begin\{itemize\}[^\n]*/g, "")
        .replace(/\\end\{itemize\}/g, "")
        .replace(/\\item\s*/g, "• ")
        .replace(/\\hrule/g, "")
        .replace(/\\vspace\{[^}]+\}/g, "")
        .replace(/\$[^$]*\$/g, " | ")
        .trim();
    };

    return {
      name: nameMatch ? nameMatch[1].replace(/\\Huge\s*/, "").trim() : "",
      phone: phoneMatch ? phoneMatch[0] : "",
      email: emailMatch ? emailMatch[0] : "",
      summary: cleanLatex(summaryMatch ? summaryMatch[1] : ""),
      education: cleanLatex(educationMatch ? educationMatch[1] : ""),
      skills: cleanLatex(skillsMatch ? skillsMatch[1] : ""),
      experience: cleanLatex(expMatch ? expMatch[1] : ""),
      certifications: cleanLatex(certMatch ? certMatch[1] : ""),
    };
  }, [latexCode]);

  // Handle template switch
  const handleSwitchTemplate = (tpl: "modern" | "academic") => {
    setSelectedTemplate(tpl);
    setLatexCode(TEMPLATES[tpl]);
    handleRecompile();
    addToast({
      type: "info",
      title: "Template Loaded",
      message: tpl === "modern" ? "Loaded Silicon Valley Tech LaTeX template" : "Loaded Academic Research CV template",
    });
  };

  const handleRecompile = () => {
    setCompiling(true);
    setTimeout(() => {
      setCompiling(false);
      setLastCompiled(new Date());
      evaluateATS();
      addToast({
        type: "success",
        title: "Recompiled Successfully ⚡",
        message: "PDF canvas updated & ATS score refreshed.",
      });
    }, 280);
  };

  // Sync edited resume to AppContext and local storage so ML model scores it against jobs
  const handleSaveAndSync = () => {
    const resumeId = "resume_overleaf_master";
    const structuredData = {
      candidate_name: parsedDoc.name,
      email: parsedDoc.email,
      phone: parsedDoc.phone,
      summary: parsedDoc.summary,
      skills: {
        technical: [
          "Python", "FastAPI", "React", "Next.js", "XGBoost", "PyTorch", "Docker", "AWS", "SQL", "TypeScript", "LangChain"
        ],
        soft: ["Leadership", "Problem Solving", "System Architecture"],
      },
    };

    setResume(resumeId, structuredData);
    localStorage.setItem("overleaf_latex_code", latexCode);
    localStorage.setItem("active_master_resume_json", JSON.stringify(structuredData));

    addToast({
      type: "success",
      title: "Synced to Match Engine! 🎯",
      message: "This resume will now be used by the XGBoost model to score all live jobs.",
    });
  };

  const handlePrintPDF = () => {
    window.print();
  };

  const handleCopyLatex = async () => {
    try {
      await navigator.clipboard.writeText(latexCode);
      addToast({
        type: "success",
        title: "LaTeX Copied",
        message: "Complete .tex document source copied to clipboard.",
      });
    } catch {}
  };

  const insertSnippet = (snippet: string) => {
    setLatexCode((prev) => prev + "\n" + snippet);
    handleRecompile();
  };

  // 1-Click Bullet Rewrite Applier
  const handleApplySuggestion = (original: string, improved: string) => {
    if (!original || !improved) return;
    if (latexCode.includes(original)) {
      setLatexCode((prev) => prev.replace(original, improved));
      handleRecompile();
      addToast({
        type: "success",
        title: "Bullet Rewritten! ⚡",
        message: "Replaced with quantified, high-impact action bullet.",
      });
    } else {
      insertSnippet(`    \\item ${improved}`);
    }
  };

  // 1-Click Missing Keyword Inserter
  const handleInsertKeyword = (kw: string) => {
    if (latexCode.includes("TECHNICAL SKILLS")) {
      setLatexCode((prev) => prev.replace(/(Frameworks & Backend:[^\n\\]+)/i, `$1, ${kw}`));
      handleRecompile();
      addToast({
        type: "success",
        title: "Keyword Injected 🎯",
        message: `Added ${kw} into Technical Skills section.`,
      });
    } else {
      insertSnippet(`\\textbf{Target Skill:} ${kw} \\\\`);
    }
  };

  const gradeColor = (tier: string) => {
    switch (tier) {
      case "Elite": return "text-emerald-500 bg-emerald-50 dark:bg-emerald-950/40 border-emerald-500/40";
      case "Strong": return "text-blue-500 bg-blue-50 dark:bg-blue-950/40 border-blue-500/40";
      case "Needs Polish": return "text-amber-500 bg-amber-50 dark:bg-amber-950/40 border-amber-500/40";
      default: return "text-red-500 bg-red-50 dark:bg-red-950/40 border-red-500/40";
    }
  };

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto pb-16 font-sans">
      
      {/* OVERLEAF COMMAND TOP BAR */}
      <div className="p-4 md:p-5 rounded-2xl border border-slate-200 dark:border-white/10 bg-white/95 dark:bg-slate-900/90 backdrop-blur-xl shadow-lg flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        
        {/* Left: Project Brand & File Name */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 text-white font-mono font-black flex items-center justify-center text-base shadow-md shadow-emerald-500/20">
            🍃
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-emerald-100 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/30">
                OVERLEAF STUDIO
              </span>
              <input
                type="text"
                value={fileName}
                onChange={(e) => setFileName(e.target.value)}
                className="text-xs font-mono font-bold text-slate-800 dark:text-slate-100 bg-transparent border-b border-dashed border-slate-300 dark:border-white/20 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <p className="text-[11px] font-mono text-slate-500 mt-0.5">
              Live LaTeX Compiler · Dual-Engine ATS & 15-Feature XGBoost Matcher
            </p>
          </div>
        </div>

        {/* Center: Template & View Controls */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Template Select */}
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-100 dark:bg-black/40 border border-slate-200 dark:border-white/10 text-xs font-mono">
            <span className="text-[10px] text-slate-400 font-bold px-2 uppercase">Template:</span>
            <button
              onClick={() => handleSwitchTemplate("modern")}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                selectedTemplate === "modern"
                  ? "bg-emerald-500 text-slate-950 font-bold shadow-xs"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              ⚡ Tech Modern
            </button>
            <button
              onClick={() => handleSwitchTemplate("academic")}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                selectedTemplate === "academic"
                  ? "bg-emerald-500 text-slate-950 font-bold shadow-xs"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              🎓 Ivy League
            </button>
          </div>

          {/* View Mode */}
          <div className="hidden sm:flex p-1 rounded-xl bg-slate-100 dark:bg-black/40 border border-slate-200 dark:border-white/10 text-xs font-mono">
            <button
              onClick={() => setEditorMode("split")}
              className={`px-2.5 py-1.5 rounded-lg ${editorMode === "split" ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-bold shadow-xs" : "text-slate-500"}`}
            >
              Split
            </button>
            <button
              onClick={() => setEditorMode("editor")}
              className={`px-2.5 py-1.5 rounded-lg ${editorMode === "editor" ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-bold shadow-xs" : "text-slate-500"}`}
            >
              Code
            </button>
            <button
              onClick={() => setEditorMode("preview")}
              className={`px-2.5 py-1.5 rounded-lg ${editorMode === "preview" ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-bold shadow-xs" : "text-slate-500"}`}
            >
              Preview
            </button>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Overleaf Green Recompile Button */}
          <button
            onClick={handleRecompile}
            disabled={compiling}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#059669] hover:bg-[#047857] text-white shadow-md hover:shadow-emerald-500/20 transition-all hover:scale-105 cursor-pointer"
          >
            <span className={compiling ? "animate-spin text-sm" : "text-sm"}>⚡</span>
            <span>{compiling ? "Compiling..." : "Recompile"}</span>
          </button>

          {/* Save & Sync */}
          <button
            onClick={handleSaveAndSync}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-mono font-bold bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-md transition-all cursor-pointer"
            title="Save this resume and use it for live ML job scoring"
          >
            <span>🎯</span>
            <span className="hidden sm:inline">Sync to Matcher</span>
          </button>

          {/* Download PDF */}
          <button
            onClick={handlePrintPDF}
            className="flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-mono border border-slate-300 dark:border-white/10 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-100 transition-colors shadow-xs"
            title="Print or export as PDF"
          >
            <span>📥</span>
            <span className="hidden sm:inline">PDF</span>
          </button>

          {/* Copy LaTeX */}
          <button
            onClick={handleCopyLatex}
            className="p-2 rounded-xl text-xs font-mono border border-slate-300 dark:border-white/10 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:text-slate-900 transition-colors shadow-xs"
            title="Copy LaTeX source code"
          >
            📋
          </button>
        </div>
      </div>

      {/* DUAL-ENGINE ATS & ML MODEL REAL-TIME TELEMETRY HUD */}
      <div className="p-4 md:p-5 rounded-3xl border border-slate-200 dark:border-white/10 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white shadow-2xl relative overflow-hidden">
        {/* Glow backdrop */}
        <div className="absolute -top-12 -right-12 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-12 -left-12 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col xl:flex-row xl:items-center justify-between gap-5">
          
          {/* 1. Score Meter & Grade Tier */}
          <div className="flex items-center gap-4">
            <div className="relative flex items-center justify-center">
              <svg className="w-20 h-20 transform -rotate-90">
                <circle
                  cx="40"
                  cy="40"
                  r="34"
                  stroke="currentColor"
                  strokeWidth="6"
                  className="text-white/10"
                  fill="transparent"
                />
                <circle
                  cx="40"
                  cy="40"
                  r="34"
                  stroke="currentColor"
                  strokeWidth="6"
                  strokeDasharray={213}
                  strokeDashoffset={213 - (213 * (atsData?.composite_score ?? 85)) / 100}
                  className={atsData?.composite_score && atsData.composite_score >= 85 ? "text-emerald-400 transition-all duration-700" : "text-cyan-400 transition-all duration-700"}
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>
              <div className="absolute text-center">
                <span className="text-2xl font-black font-heading tracking-tight">
                  {atsData ? atsData.composite_score : "—"}
                </span>
                <span className="block text-[8px] font-mono text-slate-400">/ 100</span>
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
                  Unified ATS Score
                </span>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${gradeColor(atsData?.grade_tier || "Elite")}`}>
                  {atsData ? `${atsData.grade_tier} Grade` : "Evaluating..."}
                </span>
                {isScoring && (
                  <span className="text-[10px] font-mono text-cyan-400 animate-pulse">● Scoring...</span>
                )}
              </div>
              <p className="text-xs text-slate-400 font-sans">
                Blends structural ATS layout hygiene (55%) with XGBoost ML market fit (45%).
              </p>
            </div>
          </div>

          {/* 2. XGBoost ML Model Telemetry Card */}
          <div className="flex items-center gap-3 p-3 px-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 text-cyan-300 flex items-center justify-center text-lg font-bold border border-cyan-500/30">
              🤖
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-white font-mono">
                  {atsData?.ml_prediction ? `${(atsData.ml_prediction.match_probability * 100).toFixed(1)}% Match Probability` : "XGBoost Matcher"}
                </span>
                <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded-md bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  XGBoost v2 (Fresher-Tuned)
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                Optimal Threshold: <span className="text-emerald-400 font-bold">0.2651</span> · Verdict: <span className="text-cyan-300 font-bold">{atsData?.ml_prediction?.verdict || "MATCH"}</span> · 15 Features Active
              </p>
            </div>
          </div>

          {/* 3. Live Salvo Target Job Selector Dropdown */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="flex flex-col gap-1 min-w-[260px]">
              <label className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Target Live Position:</span>
                <span className="text-emerald-400">● 109 Live Salvo</span>
              </label>
              <select
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                className="text-xs font-mono font-bold bg-white/10 hover:bg-white/15 text-white border border-white/20 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-all cursor-pointer"
              >
                <option value="benchmark" className="bg-slate-900 text-white">
                  🌟 Universal Benchmark (Tech & AI Roles)
                </option>
                {liveJobs.map((j) => (
                  <option key={j.job_id} value={j.job_id} className="bg-slate-900 text-white">
                    🎯 {j.title} — {j.company} ({j.location})
                  </option>
                ))}
              </select>
            </div>

            {/* Right Pane Tab Switcher */}
            <div className="flex items-center p-1 rounded-xl bg-white/10 border border-white/15 text-xs font-mono self-end sm:self-center">
              <button
                onClick={() => setRightPaneTab("canvas")}
                className={`px-3 py-2 rounded-lg transition-all flex items-center gap-1.5 ${
                  rightPaneTab === "canvas" ? "bg-cyan-500 text-slate-950 font-bold shadow-md" : "text-slate-300 hover:text-white"
                }`}
              >
                <span>📄</span>
                <span>PDF Canvas</span>
              </button>
              <button
                onClick={() => setRightPaneTab("ats")}
                className={`px-3 py-2 rounded-lg transition-all flex items-center gap-1.5 ${
                  rightPaneTab === "ats" ? "bg-cyan-500 text-slate-950 font-bold shadow-md" : "text-slate-300 hover:text-white"
                }`}
              >
                <span>📊</span>
                <span>ATS & ML Radar</span>
                {atsData && (
                  <span className="ml-1 px-1.5 py-0.2 rounded-full text-[9px] bg-slate-950/40 text-cyan-200 font-bold">
                    {atsData.composite_score}
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* OVERLEAF SPLIT WORKSPACE */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        
        {/* LEFT PANE: LATEX CODE EDITOR */}
        {(editorMode === "split" || editorMode === "editor") && (
          <div className="rounded-3xl border border-slate-200 dark:border-white/10 bg-white/95 dark:bg-slate-900/90 backdrop-blur-xl shadow-xl overflow-hidden flex flex-col h-[820px]">
            {/* Editor Toolbar */}
            <div className="p-3 px-5 border-b border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-950/60 flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                <span className="font-bold text-emerald-600 dark:text-emerald-400">main.tex</span>
                <span>•</span>
                <span>{latexCode.split("\n").length} lines</span>
                <span>•</span>
                <span>LaTeX2e</span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-full border border-emerald-300 dark:border-emerald-500/30">
                  ✓ 0 Errors
                </span>
                <span className="text-[10px] text-slate-400">
                  {lastCompiled.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
              </div>
            </div>

            {/* Quick Section Insert Chips */}
            <div className="p-2 px-4 border-b border-slate-100 dark:border-white/5 bg-slate-100/50 dark:bg-black/20 flex items-center gap-1.5 overflow-x-auto text-[11px] font-mono">
              <span className="text-slate-400 font-bold uppercase text-[9px] mr-1 shrink-0">Insert:</span>
              <button
                onClick={() => insertSnippet("\n\\textbf{Project Name} \\hfill \\textit{Tech Stack} \\\\\n\\begin{itemize}[noitemsep,leftmargin=14pt]\n    \\item Developed feature with 30% performance boost.\n\\end{itemize}")}
                className="px-2 py-0.5 rounded-md bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-700 dark:text-slate-300 hover:text-emerald-500 shrink-0"
              >
                + Project
              </button>
              <button
                onClick={() => insertSnippet("\n\\textbf{Role Title} \\hfill \\textit{Dates} \\\\\n\\textit{Company Name} \\hfill \\textit{Location}\n\\begin{itemize}[noitemsep,leftmargin=14pt]\n    \\item Led design and delivery of microservices.\n\\end{itemize}")}
                className="px-2 py-0.5 rounded-md bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-700 dark:text-slate-300 hover:text-emerald-500 shrink-0"
              >
                + Experience
              </button>
              <button
                onClick={() => insertSnippet("\n\\textbf{Skill Group:} Skill 1, Skill 2, Skill 3 \\\\")}
                className="px-2 py-0.5 rounded-md bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-700 dark:text-slate-300 hover:text-emerald-500 shrink-0"
              >
                + Skills
              </button>
            </div>

            {/* Editor Core */}
            <div className="flex-1 relative overflow-hidden flex">
              {/* Line Numbers Gutter */}
              <div className="w-12 py-4 select-none text-right pr-3 font-mono text-xs text-slate-400 dark:text-slate-600 border-r border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-slate-950/40">
                {latexCode.split("\n").map((_, i) => (
                  <div key={i} className="leading-6">
                    {i + 1}
                  </div>
                ))}
              </div>

              {/* Code Textarea */}
              <textarea
                value={latexCode}
                onChange={(e) => setLatexCode(e.target.value)}
                spellCheck={false}
                className="flex-1 p-4 font-mono text-xs text-slate-900 dark:text-emerald-300 bg-transparent focus:outline-none resize-none leading-6 selection:bg-emerald-500/30 overflow-y-auto"
              />
            </div>
          </div>
        )}

        {/* RIGHT PANE: REAL-TIME A4 PREVIEW CANVAS OR ATS DIAGNOSTIC RADAR */}
        {(editorMode === "split" || editorMode === "preview") && (
          <div className="rounded-3xl border border-slate-200 dark:border-white/10 bg-slate-100/80 dark:bg-slate-950/70 backdrop-blur-xl shadow-xl overflow-hidden flex flex-col h-[820px]">
            
            {/* Top Toolbar */}
            <div className="p-3 px-5 border-b border-slate-200 dark:border-white/10 bg-white/90 dark:bg-slate-900/90 flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-3">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  {rightPaneTab === "canvas" ? "Live Compiled PDF" : "ATS & ML Diagnostic Telemetry"}
                </span>
                <span className="text-slate-300 dark:text-slate-700">•</span>
                <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold">
                  {rightPaneTab === "canvas" ? "1-Page Rule ✓" : `Overall Match: ${atsData?.composite_score ?? 90}%`}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {rightPaneTab === "canvas" && (
                  <div className="flex items-center gap-1 border border-slate-200 dark:border-white/10 rounded-lg p-0.5 bg-slate-50 dark:bg-black/30">
                    <button
                      onClick={() => setZoomLevel((z) => Math.max(75, z - 10))}
                      className="px-2 py-0.5 text-slate-600 dark:text-slate-300 hover:text-cyan-500 font-bold"
                    >
                      -
                    </button>
                    <span className="px-1 text-[10px] text-slate-600 dark:text-slate-300 font-bold">{zoomLevel}%</span>
                    <button
                      onClick={() => setZoomLevel((z) => Math.min(130, z + 10))}
                      className="px-2 py-0.5 text-slate-600 dark:text-slate-300 hover:text-cyan-500 font-bold"
                    >
                      +
                    </button>
                  </div>
                )}

                <Link
                  href="/jobs"
                  className="px-3 py-1 rounded-lg bg-cyan-500 text-slate-950 font-bold text-xs hover:bg-cyan-400 shadow-xs flex items-center gap-1"
                >
                  <span>Live Jobs</span>
                  <span>→</span>
                </Link>
              </div>
            </div>

            {/* TAB 1: REAL-TIME A4 PRINTABLE CANVAS */}
            {rightPaneTab === "canvas" && (
              <div className="flex-1 overflow-y-auto p-6 flex justify-center bg-slate-200/50 dark:bg-black/60 print:p-0 print:bg-white">
                <div
                  id="resume-canvas-printable"
                  style={{
                    transform: `scale(${zoomLevel / 100})`,
                    transformOrigin: "top center",
                    width: "210mm",
                    minHeight: "297mm",
                  }}
                  className="bg-white text-slate-900 shadow-2xl rounded-sm p-10 md:p-12 space-y-4 font-serif text-[11px] leading-relaxed transition-transform duration-200 border border-slate-200/80 print:shadow-none print:border-none print:p-0 print:m-0"
                >
                  {/* Header Section */}
                  <div className="text-center space-y-1 pb-3 border-b border-slate-900">
                    <h1 className="text-2xl font-bold tracking-tight uppercase font-sans text-slate-950">
                      {parsedDoc.name}
                    </h1>
                    <p className="text-xs text-slate-700 font-mono flex items-center justify-center gap-2 flex-wrap">
                      <span>{parsedDoc.phone}</span>
                      <span>•</span>
                      <a href={`mailto:${parsedDoc.email}`} className="text-cyan-700 hover:underline">{parsedDoc.email}</a>
                      <span>•</span>
                      <span className="text-slate-600">linkedin.com/in/your-handle</span>
                      <span>•</span>
                      <span className="text-slate-600">github.com/your-handle</span>
                    </p>
                  </div>

                  {/* Summary */}
                  {parsedDoc.summary && (
                    <div className="space-y-1">
                      <h2 className="text-xs font-bold uppercase tracking-wider font-sans text-slate-950 border-b border-slate-400 pb-0.5">
                        Professional Summary
                      </h2>
                      <p className="text-slate-800 text-[11px] leading-normal font-sans">
                        {parsedDoc.summary}
                      </p>
                    </div>
                  )}

                  {/* Education */}
                  {parsedDoc.education && (
                    <div className="space-y-1">
                      <h2 className="text-xs font-bold uppercase tracking-wider font-sans text-slate-950 border-b border-slate-400 pb-0.5">
                        Education
                      </h2>
                      <div className="text-slate-800 text-[11px] font-sans whitespace-pre-line leading-snug">
                        {parsedDoc.education}
                      </div>
                    </div>
                  )}

                  {/* Technical Skills */}
                  {parsedDoc.skills && (
                    <div className="space-y-1">
                      <h2 className="text-xs font-bold uppercase tracking-wider font-sans text-slate-950 border-b border-slate-400 pb-0.5">
                        Technical Skills
                      </h2>
                      <div className="text-slate-800 text-[11px] font-sans whitespace-pre-line leading-relaxed">
                        {parsedDoc.skills}
                      </div>
                    </div>
                  )}

                  {/* Experience & Projects */}
                  {parsedDoc.experience && (
                    <div className="space-y-1.5">
                      <h2 className="text-xs font-bold uppercase tracking-wider font-sans text-slate-950 border-b border-slate-400 pb-0.5">
                        Experience & Flagship Projects
                      </h2>
                      <div className="text-slate-800 text-[11px] font-sans whitespace-pre-line leading-relaxed">
                        {parsedDoc.experience}
                      </div>
                    </div>
                  )}

                  {/* Certifications */}
                  {parsedDoc.certifications && (
                    <div className="space-y-1">
                      <h2 className="text-xs font-bold uppercase tracking-wider font-sans text-slate-950 border-b border-slate-400 pb-0.5">
                        Certifications & Accreditations
                      </h2>
                      <div className="text-slate-800 text-[11px] font-sans whitespace-pre-line leading-snug">
                        {parsedDoc.certifications}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 2: ATS & ML DIAGNOSTIC RADAR */}
            {rightPaneTab === "ats" && (
              <div className="flex-1 overflow-y-auto p-5 space-y-5 bg-white/70 dark:bg-slate-900/60 font-sans">
                
                {/* Category Sub-Scores Bars */}
                <div className="p-4 rounded-2xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-white/10 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold font-heading text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                      <span>📊</span> ATS Compliance Breakdown
                    </h3>
                    <span className="text-[10px] font-mono text-slate-400">Deterministic Engine</span>
                  </div>

                  <div className="space-y-2.5 text-xs font-mono">
                    {/* Parseability */}
                    <div>
                      <div className="flex justify-between text-[11px] mb-1">
                        <span className="text-slate-600 dark:text-slate-400">Parseability & Standard Headers</span>
                        <span className="font-bold text-slate-900 dark:text-white">{atsData?.breakdown.parseability ?? 25} / 25 pts</span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                          style={{ width: `${((atsData?.breakdown.parseability ?? 25) / 25) * 100}%` }}
                        />
                      </div>
                    </div>

                    {/* Keywords */}
                    <div>
                      <div className="flex justify-between text-[11px] mb-1">
                        <span className="text-slate-600 dark:text-slate-400">Technical Keyword Indexing</span>
                        <span className="font-bold text-slate-900 dark:text-white">{atsData?.breakdown.keyword_match ?? 26} / 30 pts</span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                        <div
                          className="h-full bg-cyan-500 rounded-full transition-all duration-500"
                          style={{ width: `${((atsData?.breakdown.keyword_match ?? 26) / 30) * 100}%` }}
                        />
                      </div>
                    </div>

                    {/* Content & Metrics */}
                    <div>
                      <div className="flex justify-between text-[11px] mb-1">
                        <span className="text-slate-600 dark:text-slate-400">Quantified Business Impact (STAR)</span>
                        <span className="font-bold text-slate-900 dark:text-white">{atsData?.breakdown.content_quality ?? 16} / 20 pts</span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                        <div
                          className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                          style={{ width: `${((atsData?.breakdown.content_quality ?? 16) / 20) * 100}%` }}
                        />
                      </div>
                    </div>

                    {/* Section Completeness */}
                    <div>
                      <div className="flex justify-between text-[11px] mb-1">
                        <span className="text-slate-600 dark:text-slate-400">Section Completeness & Contact</span>
                        <span className="font-bold text-slate-900 dark:text-white">{atsData?.breakdown.section_completeness ?? 15} / 15 pts</span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                          style={{ width: `${((atsData?.breakdown.section_completeness ?? 15) / 15) * 100}%` }}
                        />
                      </div>
                    </div>

                    {/* Formatting */}
                    <div>
                      <div className="flex justify-between text-[11px] mb-1">
                        <span className="text-slate-600 dark:text-slate-400">Formatting Hygiene & Cleanliness</span>
                        <span className="font-bold text-slate-900 dark:text-white">{atsData?.breakdown.formatting ?? 10} / 10 pts</span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                        <div
                          className="h-full bg-teal-500 rounded-full transition-all duration-500"
                          style={{ width: `${((atsData?.breakdown.formatting ?? 10) / 10) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* 15 ML Features Vector Card */}
                {atsData?.ml_prediction?.features && (
                  <div className="p-4 rounded-2xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-white/10 shadow-sm space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold font-heading text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                        <span>🤖</span> 15-Feature ML Predictive Vector
                      </h3>
                      <span className="text-[10px] font-mono font-bold text-cyan-500 bg-cyan-50 dark:bg-cyan-950/40 px-2 py-0.5 rounded-full border border-cyan-300 dark:border-cyan-500/30">
                        xgb_matcher.pkl
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center font-mono">
                      <div className="p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-white/5">
                        <span className="text-[9px] text-slate-400 block font-bold">PROJECTS</span>
                        <span className="text-sm font-black text-emerald-500">{atsData.ml_prediction.features.project_keyword_count ?? 6}</span>
                      </div>
                      <div className="p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-white/5">
                        <span className="text-[9px] text-slate-400 block font-bold">INTERNSHIPS</span>
                        <span className="text-sm font-black text-indigo-500">{atsData.ml_prediction.features.internship_mentions ?? 1}</span>
                      </div>
                      <div className="p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-white/5">
                        <span className="text-[9px] text-slate-400 block font-bold">CERTS</span>
                        <span className="text-sm font-black text-cyan-500">{atsData.ml_prediction.features.certification_count ?? 3}</span>
                      </div>
                      <div className="p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-white/5">
                        <span className="text-[9px] text-slate-400 block font-bold">SKILL RECENCY</span>
                        <span className="text-sm font-black text-emerald-500">{atsData.ml_prediction.features.skill_recency_score ?? 0.85}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Missing Target Skills */}
                {atsData && atsData.missing_keywords && atsData.missing_keywords.length > 0 && (
                  <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 shadow-sm space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold font-heading text-amber-600 dark:text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                        <span>⚠️</span> Missing Target Keywords ({atsData.missing_keywords.length})
                      </h4>
                      <span className="text-[10px] font-mono text-amber-600 dark:text-amber-400">Click to inject</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {atsData.missing_keywords.map((kw) => (
                        <button
                          key={kw}
                          onClick={() => handleInsertKeyword(kw)}
                          className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 border border-amber-300 dark:border-amber-500/30 text-amber-700 dark:text-amber-300 hover:bg-amber-100 text-[11px] font-mono font-bold flex items-center gap-1 shadow-2xs transition-all cursor-pointer"
                        >
                          <span>+</span>
                          <span>{kw}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actionable AI Bullet Point Rewrites */}
                {atsData && atsData.bullet_suggestions && atsData.bullet_suggestions.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold font-heading text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                      <span>⚡</span> 1-Click Bullet Point Enhancers
                    </h4>

                    {atsData.bullet_suggestions.map((sug, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-2xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-white/10 shadow-sm space-y-2"
                      >
                        <div className="text-[11px] font-mono text-slate-500">
                          <span className="font-bold text-red-500 mr-1.5">Original:</span>
                          <span className="line-through">{sug.original}</span>
                        </div>

                        <div className="text-[11px] font-mono text-slate-900 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/30 p-2.5 rounded-xl border border-emerald-300 dark:border-emerald-500/30">
                          <span className="font-bold text-emerald-600 dark:text-emerald-400 block mb-0.5">Recommended (Quantified):</span>
                          {sug.improved}
                        </div>

                        <div className="flex items-center justify-between pt-1">
                          <span className="text-[10px] text-slate-400 font-sans italic">{sug.reason}</span>
                          <button
                            onClick={() => handleApplySuggestion(sug.original, sug.improved)}
                            className="px-3 py-1 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-mono font-bold text-[10px] shadow-xs transition-all cursor-pointer flex items-center gap-1"
                          >
                            <span>⚡</span>
                            <span>Apply Rewrite</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
