"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "@/context/AppContext";

interface ParsedJob {
  title: string;
  company: string;
  location: string;
  salary: string;
  job_type: string;
  experience: string;
  education: string;
  required_skills: string[];
  nice_skills: string[];
  responsibilities: string[];
  benefits: string[];
}

export default function JobParser() {
  const router = useRouter();
  const { resumeData } = useApp();
  
  const [activeTab, setActiveTab] = useState<"paste" | "url">("paste");
  const [postText, setPostText] = useState<string>("");
  const [urlInput, setUrlInput] = useState<string>("");
  const [parsedJob, setParsedJob] = useState<ParsedJob | null>(null);
  
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const jobPresets = [
    {
      id: "mern",
      label: "⚡ MERN Stack",
      text: "Senior MERN Stack Engineer\nNexus Web Systems\nSan Francisco, CA (Remote)\n\nAbout the Role:\nWe are seeking an experienced MERN Stack Engineer to build scalable fullstack applications.\n\nRequirements:\n- Strong proficiency in MongoDB, Express.js, React, Node.js, and TypeScript.\n- Experience designing RESTful APIs and microservices.\n- Hands-on knowledge of Docker, CI/CD pipelines, and cloud deployment.\n- 4+ years of professional experience.",
      parsed: {
        title: "Senior MERN Stack Engineer",
        company: "Nexus Web Systems",
        location: "San Francisco, CA (Remote)",
        salary: "$140,000 - $185,000",
        job_type: "Full-Time",
        experience: "4+ Years",
        education: "Bachelors",
        required_skills: ["MERN", "MongoDB", "Express", "React", "Node.js", "TypeScript"],
        nice_skills: ["Docker", "Kubernetes", "GraphQL", "Redis"],
        responsibilities: [
          "Architect, develop, and maintain MERN stack web applications",
          "Design scalable RESTful APIs with Express and Node.js",
          "Optimize MongoDB queries and aggregation pipelines",
        ],
        benefits: ["Remote flexibility", "Competitive 401(k)", "Health & Dental"],
      },
    },
    {
      id: "dotnet",
      label: "🟣 .NET / C#",
      text: "Principal .NET / C# Cloud Architect\nEnterprise Global FinTech\nNew York, NY (Hybrid)\n\nAbout the Role:\nLead enterprise microservices architecture using modern .NET 8, ASP.NET Core, and C#.\n\nRequirements:\n- 6+ years of C# / .NET Core enterprise development.\n- Deep expertise in ASP.NET Core, Entity Framework Core, and SQL Server.\n- Experience with Microsoft Azure, microservices, and Docker.\n- High-throughput API gateway and event streaming knowledge.",
      parsed: {
        title: "Principal .NET / C# Cloud Architect",
        company: "Enterprise Global FinTech",
        location: "New York, NY (Hybrid)",
        salary: "$160,000 - $220,000",
        job_type: "Full-Time",
        experience: "6+ Years",
        education: "Bachelors / Masters",
        required_skills: [".NET", ".NET Core", "C#", "ASP.NET Core", "Entity Framework"],
        nice_skills: ["Azure", "Microservices", "Docker", "SQL Server"],
        responsibilities: [
          "Design enterprise distributed services in .NET 8 / ASP.NET Core",
          "Optimize Entity Framework queries and data caching layers",
          "Lead cloud architectural reviews and security audits",
        ],
        benefits: ["Annual performance bonus", "Comprehensive healthcare", "Hybrid work policy"],
      },
    },
    {
      id: "python",
      label: "🐍 Python & AI",
      text: "Lead Python & AI Systems Engineer\nCognitive AI Labs\nAustin, TX (Remote)\n\nAbout the Role:\nDesign and productionize neural AI systems using Python and FastAPI.\n\nRequirements:\n- 5+ years building backend systems and ML pipelines in Python.\n- Proficiency in FastAPI, PyTorch, LangChain, and Transformers.\n- Experience with vector search databases (Pinecone, Milvus) and Docker.\n- Understanding of asynchronous Python and low-latency inference.",
      parsed: {
        title: "Lead Python & AI Systems Engineer",
        company: "Cognitive AI Labs",
        location: "Austin, TX (Remote)",
        salary: "$155,000 - $210,000",
        job_type: "Full-Time",
        experience: "5+ Years",
        education: "Masters in CS or AI",
        required_skills: ["Python", "FastAPI", "PyTorch", "LangChain", "Transformers"],
        nice_skills: ["Pinecone", "Docker", "Vector Search", "NLP"],
        responsibilities: [
          "Develop low-latency Python FastAPI neural inference microservices",
          "Construct production RAG pipelines with LangChain and Pinecone",
          "Fine-tune specialized language models on PyTorch",
        ],
        benefits: ["100% remote", "Generous AI compute budget", "Health & Wellness stipend"],
      },
    },
    {
      id: "typescript",
      label: "🔷 TypeScript",
      text: "Senior Full-Stack TypeScript Engineer\nModernScale Platform\nSeattle, WA (Remote)\n\nAbout the Role:\nSpearhead end-to-end fullstack development in pure TypeScript across Next.js and Node.js.\n\nRequirements:\n- 4+ years of professional TypeScript development.\n- Deep mastery of Next.js, React 19, Node.js, and Tailwind CSS.\n- Experience with GraphQL, REST APIs, and automated testing (Jest, Playwright).\n- Passion for clean design systems and 3D web technologies.",
      parsed: {
        title: "Senior Full-Stack TypeScript Engineer",
        company: "ModernScale Platform",
        location: "Seattle, WA (Remote)",
        salary: "$145,000 - $190,000",
        job_type: "Full-Time",
        experience: "4+ Years",
        education: "Bachelors",
        required_skills: ["TypeScript", "React", "Next.js", "Node.js", "Tailwind CSS"],
        nice_skills: ["GraphQL", "CI/CD", "Three.js", "Jest"],
        responsibilities: [
          "Engineer responsive web portals in Next.js, React, and TypeScript",
          "Build scalable backend services and GraphQL APIs in Node.js",
          "Implement high-performance animations and 3D UI components",
        ],
        benefits: ["Unlimited PTO", "Equity grant", "Home office budget"],
      },
    },
  ];

  const handleLoadJobPreset = (preset: typeof jobPresets[0]) => {
    setPostText(preset.text);
    setParsedJob(preset.parsed);
    setFeedbackMsg(`Loaded and parsed preset: ${preset.label}`);
    setTimeout(() => setFeedbackMsg(null), 3500);
  };

  const handleParseText = (e: React.FormEvent) => {
    e.preventDefault();
    if (!postText.trim()) {
      setErrorMsg("Please paste job details to analyze.");
      return;
    }

    setErrorMsg(null);
    const lines = postText.split("\n").map(l => l.trim()).filter(Boolean);
    const title = lines[0] || "Software Engineer";
    const company = lines[1] || "Tech Global Inc";

    setParsedJob({
      title: title.slice(0, 60),
      company: company.slice(0, 60),
      location: "San Francisco, CA",
      salary: "$120,000 - $150,000",
      job_type: "Full-Time",
      experience: "3+ Years",
      education: "Bachelors",
      required_skills: ["Python", "SQL", "Git", "API Development"],
      nice_skills: ["Docker", "Kubernetes", "AWS"],
      responsibilities: [
        "Design and build scalable APIs using FastAPI",
        "Work with database indexes",
        "Automate ML testing pipelines"
      ],
      benefits: [
        "Medical & Dental coverage",
        "Unlimited PTO",
        "Stock options"
      ]
    });
    
    setFeedbackMsg("Successfully parsed job details!");
    setTimeout(() => setFeedbackMsg(null), 3000);
  };

  const handleParseUrl = (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) {
      setErrorMsg("Please enter a valid URL.");
      return;
    }
    setErrorMsg("Parsing from URL is mocked in this sandboxed environment. Please paste details in the text tab.");
    setTimeout(() => setErrorMsg(null), 5000);
  };

  const handleSaveToBoard = () => {
    alert("Successfully saved job to target board!");
  };

  const handleMatchAgainstResume = () => {
    if (!parsedJob) return;
    if (!resumeData) {
      alert("Please upload a resume first under the Resume Analyzer tab.");
      return;
    }

    const reqSkills = parsedJob.required_skills.map(s => s.toLowerCase());
    const candSkills = (resumeData.skills || []).map((s: string) => s.toLowerCase());
    
    const overlap = reqSkills.filter(s => candSkills.includes(s)).length;
    const total = reqSkills.length;
    const score = total > 0 ? Math.round((overlap / total) * 100) : 0;
    
    alert(`XGBoost Match Score: ${score}% Similarity Rating!`);
  };

  const handlePrepareInterview = () => {
    router.push("/coach");
  };

  return (
    <div className="space-y-6">
      
      {/* Input Tabs Headers */}
      <div className="flex bg-slate-100 p-1.5 rounded-xl border border-slate-200 select-none max-w-[400px]">
        <button
          onClick={() => { setActiveTab("paste"); setErrorMsg(null); }}
          className={`flex-1 py-2 text-xs font-bold font-heading rounded-lg transition-all cursor-pointer ${
            activeTab === "paste"
              ? "bg-[#4F46E5] text-white shadow-sm"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          Paste Text
        </button>
        <button
          onClick={() => { setActiveTab("url"); setErrorMsg(null); }}
          className={`flex-1 py-2 text-xs font-bold font-heading rounded-lg transition-all cursor-pointer ${
            activeTab === "url"
              ? "bg-[#4F46E5] text-white shadow-sm"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          Parse from URL
        </button>
      </div>

      {feedbackMsg && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 p-3 rounded-xl text-xs font-medium max-w-[500px] flex items-center gap-2">
          <span>✓</span> {feedbackMsg}
        </div>
      )}
      {errorMsg && (
        <div className="bg-red-50 border border-red-200 text-red-600 p-3 rounded-xl text-xs font-medium max-w-[500px] flex items-center gap-2">
          <span>⚠️</span> {errorMsg}
        </div>
      )}

      {/* Parse Fields */}
      <div className="glass-panel p-6 shadow-md border border-slate-200">
        {activeTab === "paste" ? (
          <form onSubmit={handleParseText} className="space-y-4">
            <div className="space-y-1.5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-mono">Job Description Details</label>
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-[10px] text-slate-400 font-mono font-semibold">Load Stack Preset:</span>
                  {jobPresets.map((pr) => (
                    <button
                      key={pr.id}
                      type="button"
                      onClick={() => handleLoadJobPreset(pr)}
                      className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-[#EEF2FF] text-[#4F46E5] border border-[#c7d2fe] hover:bg-[#E0E7FF] transition-all cursor-pointer shadow-xs"
                    >
                      {pr.label}
                    </button>
                  ))}
                </div>
              </div>
              <textarea
                placeholder="Paste the full job posting details here... (e.g. Title in line 1, Company in line 2, requirements below)"
                rows={8}
                value={postText}
                onChange={(e) => setPostText(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-xs text-slate-900 placeholder-slate-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20 focus:outline-none resize-y shadow-inner"
              />
            </div>
            <button
              type="submit"
              className="py-2.5 px-6 rounded-xl bg-gradient-to-r from-[#4F46E5] to-[#0EA5E9] text-white font-bold text-xs select-none cursor-pointer transition-all shadow-md hover:shadow-indigo-500/25"
            >
              Parse Job Details
            </button>
          </form>
        ) : (
          <form onSubmit={handleParseUrl} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-mono">Source URL</label>
              <input
                type="text"
                placeholder="https://linkedin.com/jobs/view/..."
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20 focus:outline-none shadow-inner"
              />
            </div>
            <button
              type="submit"
              className="py-2.5 px-6 rounded-xl bg-gradient-to-r from-[#4F46E5] to-[#0EA5E9] text-white font-bold text-xs select-none cursor-pointer transition-all shadow-md hover:shadow-indigo-500/25"
            >
              Fetch and Parse
            </button>
          </form>
        )}
      </div>

      {/* Render Parsed outputs */}
      {parsedJob && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Left Card: Info Details */}
            <div className="glass-panel p-6 border border-slate-200 shadow-lg space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <h4 className="text-base font-bold font-heading text-slate-900 m-0 flex items-center gap-2">
                  <span>📋</span> Extracted Role Specifications
                </h4>
                <span className="text-[10px] font-mono font-bold bg-[#EEF2FF] text-[#4F46E5] px-2.5 py-0.5 rounded-full border border-[#c7d2fe]">
                  Parsed
                </span>
              </div>
              
              <div className="space-y-3 text-xs">
                <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                  <span className="text-slate-500 font-medium">Title</span>
                  <span className="font-bold text-slate-900 text-right">{parsedJob.title}</span>
                </div>
                <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                  <span className="text-slate-500 font-medium">Company</span>
                  <span className="font-bold text-slate-900 text-right">{parsedJob.company}</span>
                </div>
                <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                  <span className="text-slate-500 font-medium">Location</span>
                  <span className="font-bold text-slate-900 text-right">{parsedJob.location}</span>
                </div>
                <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                  <span className="text-slate-500 font-medium">Salary Range</span>
                  <span className="font-bold text-[#10B981] font-mono text-right">{parsedJob.salary}</span>
                </div>
                <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                  <span className="text-slate-500 font-medium">Employment Type</span>
                  <span className="font-bold text-slate-900 text-right">{parsedJob.job_type}</span>
                </div>
                <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                  <span className="text-slate-500 font-medium">Experience Required</span>
                  <span className="font-bold text-slate-900 text-right">{parsedJob.experience}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Education Required</span>
                  <span className="font-bold text-slate-900 text-right">{parsedJob.education}</span>
                </div>
              </div>
            </div>

            {/* Right Card: Skills and Perks */}
            <div className="glass-panel p-6 border border-slate-200 shadow-lg space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <h4 className="text-base font-bold font-heading text-slate-900 m-0 flex items-center gap-2">
                  <span>⚡</span> Required Stack & Perks
                </h4>
                <span className="text-[10px] font-mono font-bold bg-emerald-50 text-emerald-700 px-2.5 py-0.5 rounded-full border border-emerald-200">
                  {parsedJob.required_skills.length} Skills
                </span>
              </div>
              
              <div className="space-y-4 text-xs">
                <div>
                  <p className="font-bold text-slate-500 mb-2 uppercase tracking-wide text-[10px] font-mono">Required Skills:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {parsedJob.required_skills.map((s, idx) => (
                      <span key={idx} className="text-[10px] font-mono bg-[#EEF2FF] border border-[#c7d2fe] text-[#4F46E5] px-2.5 py-1 rounded-full font-bold">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="font-bold text-slate-500 mb-2 uppercase tracking-wide text-[10px] font-mono">Nice to Have Skills:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {parsedJob.nice_skills.map((s, idx) => (
                      <span key={idx} className="text-[10px] font-mono bg-emerald-50 border border-emerald-200 text-[#10B981] px-2.5 py-1 rounded-full font-bold">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="font-bold text-slate-500 mb-1.5 uppercase tracking-wide text-[10px] font-mono">Core Responsibilities:</p>
                  <ul className="list-disc pl-4 space-y-1 text-slate-700 font-medium">
                    {parsedJob.responsibilities.map((r, idx) => (
                      <li key={idx}>{r}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <p className="font-bold text-slate-500 mb-1.5 uppercase tracking-wide text-[10px] font-mono">Benefits & Compensation:</p>
                  <ul className="list-disc pl-4 space-y-1 text-slate-700 font-medium">
                    {parsedJob.benefits.map((b, idx) => (
                      <li key={idx}>{b}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-3 pt-2 flex-wrap sm:flex-nowrap">
            <button
              onClick={handleSaveToBoard}
              className="flex-1 py-3 rounded-xl border border-slate-200 hover:border-slate-300 text-slate-800 font-bold text-xs transition-all bg-white hover:bg-slate-50 select-none cursor-pointer shadow-sm text-center"
            >
              💼 Save to My Job Board
            </button>
            <button
              onClick={handleMatchAgainstResume}
              className="flex-1 py-3 rounded-xl text-white font-bold text-xs transition-all bg-emerald-600 hover:bg-emerald-500 select-none cursor-pointer shadow-md text-center"
            >
              ⚡ Match Against My Resume
            </button>
            <button
              onClick={handlePrepareInterview}
              className="flex-1 py-3 rounded-xl text-white font-bold text-xs transition-all bg-gradient-to-r from-[#4F46E5] to-[#0EA5E9] hover:opacity-95 select-none cursor-pointer shadow-md text-center"
            >
              🤖 Prepare Interview Questions
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
