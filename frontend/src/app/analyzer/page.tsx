"use client";

import React, { useState } from "react";
import { useApp } from "@/context/AppContext";
import Card3DTilt from "@/components/3d/Card3DTilt";
import SkillTagCloud3D from "@/components/3d/SkillTagCloud3D";
import CareerPathHorizon3D from "@/components/3d/CareerPathHorizon3D";
import FormattedMarkdown from "@/components/FormattedMarkdown";

interface MatchResult {
  job_id: string;
  title: string;
  company: string;
  location: string;
  match_score: string;
  raw_score: number;
  required_skills: string[];
  salary_min: number | null;
  salary_max: number | null;
}

export default function ResumeAnalyzer() {
  const { resumeData, setResume, apiBase, user, groqApiKey, pineconeApiKey, primaryProvider } = useApp();
  const [file, setFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [paperPlaneFly, setPaperPlaneFly] = useState<boolean>(false);
  const [step, setStep] = useState<number>(resumeData ? 2 : 1);
  const [uploading, setUploading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [matchResults, setMatchResults] = useState<MatchResult[]>([]);
  const [matchLoading, setMatchLoading] = useState<boolean>(false);
  const [ragInsight, setRagInsight] = useState<string>("");
  const [ragLoading, setRagLoading] = useState<boolean>(false);

  const candidatePresets = [
    {
      id: "res_stack_mern_01",
      name: "Alex Chen",
      role: "Senior MERN Stack Developer",
      skills: ["MERN", "MongoDB", "Express", "React", "Node.js", "TypeScript", "REST", "Git", "Docker"],
      experience_years: 5.5,
      education: "Bachelor of Science",
      category: "Engineering",
      tag: "⚡ MERN Stack",
      color: "#10B981",
      summary: "Full-Stack Engineer with 5.5+ years building scalable MERN web applications with TypeScript.",
    },
    {
      id: "res_stack_dotnet_01",
      name: "Sarah Jenkins",
      role: "Lead .NET Cloud Solutions Architect",
      skills: [".NET", ".NET Core", "C#", "ASP.NET Core", "Entity Framework", "Azure", "Microservices", "SQL"],
      experience_years: 7.0,
      education: "Master of Science",
      category: "Engineering",
      tag: "🟣 .NET & C#",
      color: "#8B5CF6",
      summary: "Enterprise Architect with 7 years specializing in .NET Core, ASP.NET Core, and Azure microservices.",
    },
    {
      id: "res_stack_python_01",
      name: "David Kumar",
      role: "Senior Python AI/ML Engineer",
      skills: ["Python", "FastAPI", "PyTorch", "LangChain", "Transformers", "NLP", "Docker", "Pandas", "Scikit-learn"],
      experience_years: 6.0,
      education: "Master of Science",
      category: "Data Science",
      tag: "🐍 Python & AI",
      color: "#3B82F6",
      summary: "AI systems engineer with 6 years experience deploying neural language models and FastAPI services.",
    },
    {
      id: "res_stack_typescript_01",
      name: "Elena Rostova",
      role: "Full-Stack TypeScript & React Engineer",
      skills: ["TypeScript", "React", "Next.js", "Node.js", "GraphQL", "Tailwind CSS", "CI/CD", "Jest"],
      experience_years: 4.5,
      education: "Bachelor of Science",
      category: "Engineering",
      tag: "🔷 TypeScript & React",
      color: "#06B6D4",
      summary: "Full-stack engineer with 4.5+ years delivering reactive 3D interfaces in Next.js, React 19, and Node.js.",
    },
  ];

  const handleSelectPreset = (preset: typeof candidatePresets[0]) => {
    const mockResume = {
      resume_id: preset.id,
      candidate_name: preset.name,
      email: `${preset.name.toLowerCase().replace(" ", ".")}@example.com`,
      phone: "+1-555-0100",
      skills: preset.skills,
      experience_years: preset.experience_years,
      education: preset.education,
      category: preset.category,
      raw_text: `${preset.name} - ${preset.role}\nSkills: ${preset.skills.join(", ")}`,
      ats_score: {
        total_score: 94,
        grade: "Strong Match",
        categories: {
          skills_depth: 96,
          experience_relevance: 92,
          education: 88,
          impact_quantification: 90,
          formatting: 96,
        },
      },
    };
    setResume(preset.id, mockResume);
    setSuccessMsg(`Loaded benchmark candidate: ${preset.name} (${preset.role})`);
    setErrorMsg(null);
    setStep(2);
    fetchMatchPredictions(preset.id, mockResume);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type !== "application/pdf") {
        setErrorMsg("Only PDF document files are supported.");
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setStep(2);
      setErrorMsg(null);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type !== "application/pdf") {
        setErrorMsg("Only PDF document files are supported.");
        return;
      }
      setFile(droppedFile);
      setStep(2);
      setErrorMsg(null);
      
      // Trigger 3D paper plane flying animation
      setPaperPlaneFly(true);
      setTimeout(() => setPaperPlaneFly(false), 1400);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setErrorMsg("Please attach a valid PDF document.");
      return;
    }

    setUploading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    const formData = new FormData();
    formData.append("file", file);
    const userId = user?.id || "guest";

    try {
      const res = await fetch(`${apiBase}/resume/upload?user_id=${userId}`, {
        method: "POST",
        body: formData,
      });

      if (res.status === 200) {
        const data = await res.json();
        setResume(data.resume_id, data);
        setSuccessMsg(`Resume parsed successfully: ${file.name}`);
        setFile(null);
        setStep(3);
        
        // Automatically fetch match predictions
        fetchMatchPredictions(data.resume_id, data);
      } else {
        setErrorMsg("Failed to analyze resume. Verify backend server is running.");
      }
    } catch (err) {
      setErrorMsg("Connection failed. Ensure backend API on port 8000 is online.");
    } finally {
      setUploading(false);
    }
  };

  const fetchMatchPredictions = async (resumeId: string, rData?: any) => {
    setMatchLoading(true);
    try {
      const res = await fetch(`${apiBase}/match/resume/${resumeId}?top_k=10`);
      if (res.status === 200) {
        const body = await res.json();
        const matches = body?.data?.matches || [];
        setMatchResults(matches);
      }
    } catch (err) {
      console.error("Match prediction failed:", err);
    } finally {
      setMatchLoading(false);
    }

    // Fetch RAG AI insight about the resume
    fetchRagInsight(rData || resumeData);
  };

  const fetchRagInsight = async (rData: any) => {
    if (!rData) return;
    setRagLoading(true);
    const skills = rData.skills || [];
    const skillsStr = skills.slice(0, 10).join(", ");
    const question = `Based on a candidate with skills: ${skillsStr}, education: ${rData.education || "N/A"}, and ${rData.experience_years || 0} years of experience in ${rData.category || "technology"} — what are the best career recommendations and skill gaps to fill?`;

    try {
      const payload = {
        question,
        session_id: `analyzer-${rData.resume_id || user?.id || "guest"}-${Date.now()}`,
        primary_provider: primaryProvider || "groq",
        groq_api_key: groqApiKey || null,
        pinecone_api_key: pineconeApiKey || null,
      };
      const res = await fetch(`${apiBase}/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.status === 200) {
        const body = await res.json();
        const answer = body?.data?.answer || "";
        setRagInsight(answer);
      }
    } catch (err) {
      setRagInsight("RAG insight unavailable. Ensure Groq API key is configured in Settings.");
    } finally {
      setRagLoading(false);
    }
  };

  const handleRemoveData = () => {
    if (confirm("Are you sure you want to clear active candidate profile data?")) {
      setResume("", null);
      setSuccessMsg(null);
      setStep(1);
      setMatchResults([]);
      setRagInsight("");
    }
  };

  const handleStepClick = (targetStep: number) => {
    // Can only go to step 2 if file selected or resumeData exists
    if (targetStep === 2 && !file && !resumeData) return;
    // Can only go to step 3 if resumeData exists (upload completed)
    if (targetStep === 3 && !resumeData) return;
    setStep(targetStep);
    
    // If going to step 3 and we have resume data but no matches yet, fetch them
    if (targetStep === 3 && resumeData && matchResults.length === 0) {
      fetchMatchPredictions(resumeData.resume_id, resumeData);
    }
  };

  const getMetrics = () => {
    if (!resumeData) return null;
    const skills = resumeData.skills || [];
    const expYears = parseFloat(resumeData.experience_years) || 0.0;
    const education = resumeData.education || "Bachelors";

    const sScore = Math.min(100, skills.length * 8);
    const eScore = Math.min(100, Math.round(expYears * 10));
    const eduScore = education === "Masters" || education === "PhD" ? 100 : (education === "Bachelors" || education === "B.Tech") ? 75 : 50;
    const overall = Math.round(sScore * 0.4 + eScore * 0.3 + eduScore * 0.3);

    return { sScore, eScore, eduScore, overall, expYears, education, skills };
  };

  const metrics = getMetrics();

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      
      {/* Step Indicator Bar — Clickable */}
      <div className="step-pill-bar max-w-2xl mx-auto shadow-sm">
        <div
          className={`step-pill ${step >= 1 ? "active" : ""} cursor-pointer touch-manipulation`}
          onClick={() => handleStepClick(1)}
        >
          <span className="hidden sm:inline">1. Select PDF Resume</span>
          <span className="sm:hidden">1. Upload</span>
        </div>
        <div
          className={`step-pill ${step >= 2 ? "active" : ""} ${!file && !resumeData ? "opacity-40 cursor-not-allowed" : "cursor-pointer"} touch-manipulation`}
          onClick={() => handleStepClick(2)}
        >
          <span className="hidden sm:inline">2. Inspect Credentials</span>
          <span className="sm:hidden">2. Inspect</span>
        </div>
        <div
          className={`step-pill ${step >= 3 ? "active" : ""} ${!resumeData ? "opacity-40 cursor-not-allowed" : "cursor-pointer"} touch-manipulation`}
          onClick={() => handleStepClick(3)}
        >
          <span className="hidden sm:inline">3. 3D Match Prediction</span>
          <span className="sm:hidden">3. Matches</span>
        </div>
      </div>

      {/* ============ STEP 1: SELECT PDF RESUME ============ */}
      {step === 1 && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-6 space-y-6">
            <Card3DTilt maxDegree={8} scaleOnHover={1.01} className="glass-panel p-6 shadow-xl">
              <div className="space-y-4">
                <h3 className="text-xl font-bold font-heading text-slate-900 flex items-center gap-2">
                  <span>📄</span> Resume Upload Platform
                </h3>

                {errorMsg && (
                  <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-xs font-medium">
                    ⚠️ {errorMsg}
                  </div>
                )}
                {successMsg && (
                  <div className="bg-emerald-50 border border-emerald-200 text-[#10B981] p-3 rounded-xl text-xs font-medium">
                    ✓ {successMsg}
                  </div>
                )}

                <form onSubmit={(e) => { e.preventDefault(); if (file) setStep(2); }} className="space-y-5">
                  {/* 3D Floating Drag-and-Drop Platform Zone */}
                  <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    style={{
                      transform: isDragOver ? "perspective(600px) rotateX(6deg) scale(1.02)" : "perspective(600px) rotateX(3deg)",
                      transition: "all 0.3s cubic-bezier(0.23, 1, 0.32, 1)",
                    }}
                    className={`relative border-2 border-dashed rounded-2xl p-8 text-center transition-all bg-gradient-to-b from-white/90 to-[#EEF2FF]/80 group cursor-pointer shadow-md ${
                      isDragOver
                        ? "border-[#4F46E5] ring-4 ring-[#4F46E5]/20 shadow-2xl"
                        : "border-[#E0E7FF] hover:border-[#4F46E5]/50"
                    }`}
                  >
                    {paperPlaneFly && (
                      <div className="absolute inset-0 pointer-events-none flex items-center justify-center z-30">
                        <span className="text-5xl animate-bounce transform -rotate-45">✈️</span>
                      </div>
                    )}

                    <input
                      type="file"
                      id="resume-file"
                      accept=".pdf"
                      onChange={handleFileChange}
                      className="hidden"
                    />
                    <label htmlFor="resume-file" className="cursor-pointer block space-y-3">
                      <div className="w-16 h-16 rounded-2xl bg-[#E0E7FF] text-[#4F46E5] flex items-center justify-center text-3xl mx-auto shadow-inner group-hover:scale-110 transition-transform">
                        📁
                      </div>
                      <span className="text-base font-bold text-slate-900 block font-heading">
                        {file ? file.name : "Drop PDF Resume or Click to Browse"}
                      </span>
                      <span className="text-xs text-slate-500 block font-mono">
                        {file ? `${(file.size / 1024).toFixed(1)} KB` : "Supports standard PDF formats (Max 10MB)"}
                      </span>
                    </label>
                  </div>

                  <button
                    type="submit"
                    disabled={!file}
                    className="btn-primary-glow w-full py-4 rounded-full font-heading font-extrabold text-sm tracking-wide disabled:opacity-40 cursor-pointer"
                  >
                    Continue to Inspect Credentials →
                  </button>
                </form>
              </div>
            </Card3DTilt>

            {/* Show previous resume data if exists */}
            {resumeData && (
              <Card3DTilt maxDegree={6} scaleOnHover={1.01} className="glass-panel p-6 shadow-lg">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold font-heading text-slate-900 text-base">Previously Uploaded Resume</h4>
                    <span className="px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-mono font-bold border border-emerald-200">
                      ✓ Analyzed
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">
                    <strong>{resumeData.candidate_name}</strong> — {(resumeData.skills || []).length} skills detected. Click &quot;Inspect Credentials&quot; to view details.
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setStep(2)}
                      className="flex-1 py-2 rounded-full bg-[#E0E7FF] text-[#4F46E5] font-bold text-xs font-mono hover:bg-[#c7d2fe] transition-all cursor-pointer"
                    >
                      View Credentials
                    </button>
                    <button
                      onClick={() => { setStep(3); if (matchResults.length === 0) fetchMatchPredictions(resumeData.resume_id, resumeData); }}
                      className="flex-1 py-2 rounded-full bg-[#4F46E5] text-white font-bold text-xs font-mono hover:bg-[#4338ca] transition-all cursor-pointer"
                    >
                      3D Match →
                    </button>
                  </div>
                </div>
              </Card3DTilt>
            )}
          </div>

          {/* Right Column: Tech Stack Candidate Presets */}
          <div className="lg:col-span-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-base font-bold font-heading text-slate-900">⚡ Instant Candidate Presets</h4>
                <p className="text-xs text-slate-500">Test ATS analysis and 3D skill scoring with benchmark stack profiles:</p>
              </div>
              <span className="text-[10px] font-mono font-bold bg-[#E0E7FF] text-[#4F46E5] px-2.5 py-1 rounded-full border border-[#c7d2fe]">
                1-Click Test
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {candidatePresets.map((preset) => (
                <Card3DTilt
                  key={preset.id}
                  maxDegree={8}
                  scaleOnHover={1.02}
                  className="glass-panel p-4 flex flex-col justify-between border border-[#E0E7FF] hover:border-[#4F46E5]/40 transition-all cursor-pointer shadow-sm group"
                  onClick={() => handleSelectPreset(preset)}
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full text-white shadow-xs" style={{ backgroundColor: preset.color }}>
                        {preset.tag}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400 font-semibold">{preset.experience_years}y exp</span>
                    </div>

                    <h5 className="font-bold text-slate-900 text-sm group-hover:text-[#4F46E5] transition-colors">{preset.name}</h5>
                    <p className="text-[11px] text-slate-500 font-medium line-clamp-1">{preset.role}</p>

                    <div className="flex flex-wrap gap-1 pt-1">
                      {preset.skills.slice(0, 4).map((sk) => (
                        <span key={sk} className="text-[9px] font-mono bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-slate-200">
                          {sk}
                        </span>
                      ))}
                      {preset.skills.length > 4 && (
                        <span className="text-[9px] font-mono text-slate-400">+{preset.skills.length - 4}</span>
                      )}
                    </div>
                  </div>

                  <button
                    type="button"
                    className="mt-3 w-full py-1.5 rounded-lg bg-slate-900 group-hover:bg-[#4F46E5] text-white text-[10px] font-mono font-bold transition-all text-center cursor-pointer shadow-xs"
                  >
                    Load {preset.tag.split(" ")[1]} Profile →
                  </button>
                </Card3DTilt>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ============ STEP 2: INSPECT CREDENTIALS ============ */}
      {step === 2 && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: File Details + Upload Button */}
          <div className="lg:col-span-6 space-y-6">
            <Card3DTilt maxDegree={8} scaleOnHover={1.01} className="glass-panel p-6 shadow-xl">
              <div className="space-y-4">
                <h3 className="text-xl font-bold font-heading text-slate-900 flex items-center gap-2">
                  <span>🔍</span> Inspect & Upload
                </h3>

                {errorMsg && (
                  <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-xs font-medium">
                    ⚠️ {errorMsg}
                  </div>
                )}
                {successMsg && (
                  <div className="bg-emerald-50 border border-emerald-200 text-[#10B981] p-3 rounded-xl text-xs font-medium">
                    ✓ {successMsg}
                  </div>
                )}

                {/* File Info */}
                {file && (
                  <div className="bg-gradient-to-r from-[#EEF2FF] to-white border border-[#E0E7FF] rounded-2xl p-4 flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-[#4F46E5] text-white flex items-center justify-center text-xl shadow-lg">
                      📄
                    </div>
                    <div className="flex-1">
                      <p className="font-bold text-slate-900 text-sm font-heading">{file.name}</p>
                      <p className="text-xs text-slate-500 font-mono">{(file.size / 1024).toFixed(1)} KB • PDF Document</p>
                    </div>
                    <button
                      onClick={() => { setFile(null); setStep(1); }}
                      className="text-red-500 hover:text-red-700 text-xs font-bold cursor-pointer"
                    >
                      ✕ Remove
                    </button>
                  </div>
                )}

                {/* Upload & Analyze Button */}
                {file ? (
                  <form onSubmit={handleUpload}>
                    <button
                      type="submit"
                      disabled={uploading}
                      className="btn-primary-glow w-full py-4 rounded-full font-heading font-extrabold text-sm tracking-wide disabled:opacity-40 cursor-pointer"
                    >
                      {uploading ? (
                        <span className="flex items-center justify-center gap-2">
                          <span className="briefcase-spinner">💼</span>
                          <span>Analyzing Skill Vectors...</span>
                        </span>
                      ) : (
                        "Upload & Predict Match →"
                      )}
                    </button>
                  </form>
                ) : resumeData ? (
                  <button
                    type="button"
                    onClick={() => {
                      setStep(3);
                      if (matchResults.length === 0) fetchMatchPredictions(resumeData.resume_id, resumeData);
                    }}
                    className="btn-primary-glow w-full py-4 rounded-full font-heading font-extrabold text-sm tracking-wide cursor-pointer text-center"
                  >
                    Proceed to 3D Match Prediction →
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled
                    className="btn-primary-glow w-full py-4 rounded-full font-heading font-extrabold text-sm tracking-wide opacity-40 cursor-not-allowed"
                  >
                    Select a File or Preset First
                  </button>
                )}

                {/* If we already have resume data, show quick view */}
                {!file && resumeData && (
                  <div className="text-center pt-2">
                    <p className="text-xs text-slate-500 font-mono">Benchmark profile loaded. Click above to view neural matches.</p>
                  </div>
                )}
              </div>
            </Card3DTilt>

            {/* Parsed Resume Credential Details */}
            {resumeData && (
              <Card3DTilt maxDegree={6} scaleOnHover={1.01} className="glass-panel p-6 shadow-lg">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold font-heading text-slate-900 text-base">Candidate Credentials</h4>
                    <span className="px-3 py-1 bg-[#E0E7FF] text-[#4F46E5] rounded-full text-xs font-mono font-bold">
                      {resumeData.category || "Verified Profile"}
                    </span>
                  </div>
                  <div className="space-y-2 text-xs font-mono">
                    <div className="flex justify-between py-1.5 border-b border-slate-200">
                      <span className="text-slate-500">Name:</span>
                      <span className="font-bold text-slate-900">{resumeData.candidate_name || "Parsed Candidate"}</span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-slate-200">
                      <span className="text-slate-500">Email:</span>
                      <span className="font-bold text-slate-900">{resumeData.email || "N/A"}</span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-slate-200">
                      <span className="text-slate-500">Experience Years:</span>
                      <span className="font-bold text-[#10B981]">{metrics?.expYears.toFixed(1)} Years</span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-slate-200">
                      <span className="text-slate-500">Education:</span>
                      <span className="font-bold text-slate-900">{metrics?.education}</span>
                    </div>
                    <div className="flex justify-between py-1.5">
                      <span className="text-slate-500">Resume ID:</span>
                      <span className="font-bold text-slate-500 text-[10px]">{resumeData.resume_id || "N/A"}</span>
                    </div>
                  </div>
                  
                  {/* Skills List */}
                  {resumeData.skills && resumeData.skills.length > 0 && (
                    <div className="pt-2">
                      <p className="text-[10px] font-mono font-bold text-slate-400 uppercase mb-2">Detected Skills ({resumeData.skills.length})</p>
                      <div className="flex flex-wrap gap-1.5">
                        {resumeData.skills.slice(0, 20).map((skill: string, idx: number) => (
                          <span key={idx} className="px-2 py-0.5 bg-[#E0E7FF] text-[#4F46E5] rounded-full text-[10px] font-mono font-bold border border-[#c7d2fe]">
                            {skill}
                          </span>
                        ))}
                        {resumeData.skills.length > 20 && (
                          <span className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded-full text-[10px] font-mono">
                            +{resumeData.skills.length - 20} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </Card3DTilt>
            )}
          </div>

          {/* Right Column: 3D Skill Cloud + Scores */}
          <div className="lg:col-span-6 space-y-6">
            {resumeData && metrics ? (
              <>
                <Card3DTilt maxDegree={8} scaleOnHover={1.01} className="glass-panel p-6 shadow-xl">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold font-heading text-slate-900 text-lg">3D Skill Tag Cloud</h4>
                      <span className="text-xs font-mono font-bold text-[#4F46E5] bg-[#E0E7FF] px-3 py-1 rounded-full">
                        {metrics.skills.length} Detected
                      </span>
                    </div>
                    <SkillTagCloud3D skills={metrics.skills} />
                  </div>
                </Card3DTilt>

                <div className="grid grid-cols-3 gap-4 font-mono text-center">
                  <div className="glass-panel p-4">
                    <span className="text-[10px] text-slate-400 block font-bold">Skills Velocity</span>
                    <span className="text-2xl font-black text-[#4F46E5] font-heading">{metrics.sScore}%</span>
                  </div>
                  <div className="glass-panel p-4">
                    <span className="text-[10px] text-slate-400 block font-bold">Experience Factor</span>
                    <span className="text-2xl font-black text-[#10B981] font-heading">{metrics.eScore}%</span>
                  </div>
                  <div className="glass-panel p-4">
                    <span className="text-[10px] text-slate-400 block font-bold">Education Rating</span>
                    <span className="text-2xl font-black text-[#F97316] font-heading">{metrics.eduScore}%</span>
                  </div>
                </div>

                <button
                  onClick={() => { setStep(3); if (matchResults.length === 0 && resumeData) fetchMatchPredictions(resumeData.resume_id, resumeData); }}
                  className="btn-primary-glow w-full py-4 rounded-full font-heading font-extrabold text-sm tracking-wide cursor-pointer"
                >
                  Proceed to 3D Match Prediction →
                </button>
              </>
            ) : (
              <Card3DTilt maxDegree={6} className="glass-panel p-12 text-center text-slate-500 h-full flex flex-col items-center justify-center space-y-4 shadow-xl">
                <div className="w-20 h-20 rounded-3xl bg-[#E0E7FF] text-[#4F46E5] flex items-center justify-center text-4xl shadow-inner">
                  🔍
                </div>
                <h4 className="text-xl font-bold font-heading text-slate-900">
                  Ready to Inspect
                </h4>
                <p className="max-w-sm text-xs text-slate-500 leading-relaxed">
                  Click &quot;Upload & Predict Match&quot; to parse your resume and extract credentials, skills, and education data.
                </p>
              </Card3DTilt>
            )}
          </div>
        </div>
      )}

      {/* ============ STEP 3: 3D MATCH PREDICTION ============ */}
      {step === 3 && (
        <div className="space-y-8">
          {/* Match Results Header */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-black font-heading text-slate-900">3D Match Prediction Results</h2>
              <p className="text-xs text-slate-500 mt-1">
                AI-powered job matching based on your resume&apos;s skill vectors against {matchResults.length > 0 ? `${matchResults.length} top jobs` : "the job market"}.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setStep(2)}
                className="px-4 py-2 rounded-full bg-white border border-slate-200 text-slate-600 font-bold text-xs font-mono hover:bg-slate-50 transition-all cursor-pointer"
              >
                ← Back to Credentials
              </button>
              <button
                onClick={handleRemoveData}
                className="px-4 py-2 rounded-full border border-red-200 text-red-600 bg-red-50 hover:bg-red-100 font-bold text-xs font-mono transition-all cursor-pointer"
              >
                Clear Data
              </button>
            </div>
          </div>

          {/* Score Summary Bar */}
          {metrics && (
            <div className="grid grid-cols-4 gap-4 font-mono text-center">
              <div className="glass-panel p-4">
                <span className="text-[10px] text-slate-400 block font-bold">Overall Score</span>
                <span className="text-3xl font-black text-[#4F46E5] font-heading">{metrics.overall}%</span>
              </div>
              <div className="glass-panel p-4">
                <span className="text-[10px] text-slate-400 block font-bold">Skills</span>
                <span className="text-2xl font-black text-[#4F46E5] font-heading">{metrics.sScore}%</span>
              </div>
              <div className="glass-panel p-4">
                <span className="text-[10px] text-slate-400 block font-bold">Experience</span>
                <span className="text-2xl font-black text-[#10B981] font-heading">{metrics.eScore}%</span>
              </div>
              <div className="glass-panel p-4">
                <span className="text-[10px] text-slate-400 block font-bold">Education</span>
                <span className="text-2xl font-black text-[#F97316] font-heading">{metrics.eduScore}%</span>
              </div>
            </div>
          )}

          {/* Career Path Horizon — Now with real data */}
          <CareerPathHorizon3D resumeData={resumeData} matchResults={matchResults} />

          {/* Match Results Grid */}
          {matchLoading ? (
            <div className="glass-panel p-12 text-center">
              <div className="briefcase-spinner text-4xl mb-4">💼</div>
              <p className="font-bold font-heading text-slate-900">Computing Neural Match Vectors...</p>
              <p className="text-xs text-slate-500 mt-1">Searching across job database using Pinecone similarity engine.</p>
            </div>
          ) : matchResults.length > 0 ? (
            <div>
              <h3 className="text-lg font-bold font-heading text-slate-900 mb-4">
                🎯 Top {matchResults.length} Job Matches
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {matchResults.map((match, idx) => (
                  <Card3DTilt key={match.job_id || idx} maxDegree={6} scaleOnHover={1.02} className="glass-panel p-5 shadow-lg">
                    <div className="space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="font-bold text-slate-900 font-heading text-sm">{match.title}</p>
                          <p className="text-xs text-slate-500 font-mono">{match.company} • {match.location}</p>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-mono font-black ${
                          match.raw_score >= 0.8 ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                          match.raw_score >= 0.6 ? "bg-blue-50 text-blue-700 border border-blue-200" :
                          "bg-orange-50 text-orange-700 border border-orange-200"
                        }`}>
                          {match.match_score}
                        </span>
                      </div>
                      {match.required_skills && match.required_skills.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {match.required_skills.slice(0, 5).map((skill: string, si: number) => (
                            <span key={si} className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-[10px] font-mono">
                              {skill}
                            </span>
                          ))}
                        </div>
                      )}
                      {(match.salary_min || match.salary_max) && (
                        <p className="text-[10px] font-mono text-slate-400">
                          💰 {match.salary_min ? `$${(match.salary_min / 1000).toFixed(0)}k` : "N/A"} — {match.salary_max ? `$${(match.salary_max / 1000).toFixed(0)}k` : "N/A"}
                        </p>
                      )}
                    </div>
                  </Card3DTilt>
                ))}
              </div>
            </div>
          ) : (
            <div className="glass-panel p-8 text-center">
              <p className="font-bold font-heading text-slate-900">No match results available.</p>
              <p className="text-xs text-slate-500 mt-1">Ensure backend is running and Pinecone has indexed job vectors.</p>
            </div>
          )}

          {/* RAG AI Career Insight */}
          <Card3DTilt maxDegree={4} scaleOnHover={1.005} className="glass-panel p-6 shadow-xl">
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-lg">🤖</span>
                <h4 className="font-bold font-heading text-slate-900 text-base">AI Career Coach Insight</h4>
                <span className="text-[10px] font-mono font-bold text-[#4F46E5] bg-[#E0E7FF] px-2 py-0.5 rounded-full">RAG</span>
              </div>
              {ragLoading ? (
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span className="animate-spin">⚙️</span>
                  <span>Generating AI career recommendations from RAG pipeline...</span>
                </div>
              ) : ragInsight ? (
                <div className="bg-gradient-to-r from-[#EEF2FF]/50 to-white/50 p-4 rounded-xl border border-[#E0E7FF]">
                  <FormattedMarkdown content={ragInsight} isDark={false} />
                </div>
              ) : (
                <p className="text-xs text-slate-400">
                  AI insight will be generated after match prediction completes. Ensure your Groq API key is configured in Settings.
                </p>
              )}
            </div>
          </Card3DTilt>
        </div>
      )}
    </div>
  );
}
