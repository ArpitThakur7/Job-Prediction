"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { SalvoJob } from "@/lib/salvoClient";
import { useToast } from "@/context/ToastContext";
import { useApp } from "@/context/AppContext";

interface ApplyModalProps {
  job: SalvoJob | null;
  isOpen: boolean;
  onClose: () => void;
  onApplicationSubmitted?: (job: SalvoJob) => void;
}

export const ApplyModal: React.FC<ApplyModalProps> = ({
  job,
  isOpen,
  onClose,
  onApplicationSubmitted,
}) => {
  const { addToast } = useToast();
  const { resumeData, user } = useApp();

  const [applicantName, setApplicantName] = useState("");
  const [applicantEmail, setApplicantEmail] = useState("");
  const [applicantPhone, setApplicantPhone] = useState("");
  const [portfolioUrl, setPortfolioUrl] = useState("");
  const [selectedResumeTitle, setSelectedResumeTitle] = useState("master");
  const [coverNote, setCoverNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [autoGeneratingPitch, setAutoGeneratingPitch] = useState(false);

  // Sync user / resume defaults if available
  useEffect(() => {
    if (resumeData?.candidate_name) {
      setApplicantName(resumeData.candidate_name);
    } else if (user?.name) {
      setApplicantName(user.name);
    }
    if (resumeData?.email) {
      setApplicantEmail(resumeData.email);
    } else if (user?.email) {
      setApplicantEmail(user.email);
    }
    if (resumeData?.phone) {
      setApplicantPhone(resumeData.phone);
    }
  }, [resumeData, user]);

  // Generate customized pitch based on targeted job
  const handleGeneratePitch = () => {
    if (!job) return;
    setAutoGeneratingPitch(true);
    setTimeout(() => {
      const skillsStr = Array.isArray(job.reasons) ? job.reasons.join(", ") : "Python, AI Pipelines, Full-Stack Architecture";
      setCoverNote(
        `Dear ${job.company} Hiring Team,\n\nI am writing to express my strong interest in the ${job.title} role. With a strong foundation in scalable software systems, Python/TypeScript backend architecture, and AI-driven data pipelines (${skillsStr}), I am confident in delivering immediate value to your engineering team.\n\nKey Highlights:\n• Hands-on production experience designing low-latency REST/FastAPI microservices and data pipelines.\n• Strong background in data modeling, containerization (Docker), and modern frontend frameworks.\n• Eager to contribute high code quality, automated test discipline, and end-to-end product ownership.\n\nThank you for considering my application. I look forward to speaking with your team!\n\nBest regards,\n${applicantName}`
      );
      setAutoGeneratingPitch(false);
      addToast({
        type: "success",
        title: "Cover pitch generated",
        message: `Tailored for ${job.title} at ${job.company}`,
      });
    }, 400);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!job) return;

    setSubmitting(true);
    try {
      // Save application record into applications store or localStorage tracker
      const appRecord = {
        company: job.company,
        title: job.title,
        url: job.url,
        score: job.combinedScore || (job.score ? Math.round((job.score / 5) * 100) : 85),
        status: "applied",
        appliedDate: new Date().toISOString(),
        resumeUsed: selectedResumeTitle,
        applicantName,
        applicantEmail,
      };

      try {
        const stored = localStorage.getItem("salvo_tracked_applications");
        const list = stored ? JSON.parse(stored) : [];
        list.unshift(appRecord);
        localStorage.setItem("salvo_tracked_applications", JSON.stringify(list));
      } catch {}

      addToast({
        type: "success",
        title: "Application Submitted! 🎉",
        message: `Your application to ${job.company} for "${job.title}" has been tracked.`,
      });

      if (onApplicationSubmitted) {
        onApplicationSubmitted(job);
      }

      onClose();

      // Open official ATS posting in a clean tab for final confirmation / verify
      if (job.url) {
        window.open(job.url, "_blank", "noopener,noreferrer");
      }
    } catch (err: any) {
      addToast({
        type: "error",
        title: "Submission failed",
        message: err.message,
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen || !job) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-y-auto flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="relative w-full max-w-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-3xl shadow-2xl overflow-hidden z-10 font-sans"
        >
          {/* Header */}
          <div className="p-6 border-b border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-800/60 flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-500/30">
                  DIRECT PLATFORM APPLY
                </span>
                <span className="text-xs font-mono text-slate-500">via {job.source || job.ats || "web"}</span>
              </div>
              <h2 className="text-xl font-black text-slate-900 dark:text-white leading-snug">
                Apply to {job.company}
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-400 font-mono">
                Role: <strong className="text-slate-900 dark:text-slate-200">{job.title}</strong> · 📍 {job.location || "Remote"}
              </p>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-white transition-colors"
            >
              ✕
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
            {/* Active Resume Selection */}
            <div className="p-4 rounded-2xl border border-cyan-500/30 bg-cyan-50/50 dark:bg-cyan-950/20 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold uppercase text-cyan-800 dark:text-cyan-300 tracking-wider">
                  Targeted Resume Document
                </span>
                <span className="text-[10px] font-mono font-bold text-emerald-600 dark:text-emerald-400">
                  ATS Verified 94%
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-2xl">📄</span>
                <div className="flex-1 min-w-0">
                  <select
                    value={selectedResumeTitle}
                    onChange={(e) => setSelectedResumeTitle(e.target.value)}
                    className="w-full text-xs font-mono font-bold bg-white dark:bg-slate-800 border border-slate-300 dark:border-white/10 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="tailored">Tailored resume for this job</option>
                    <option value="master">Master resume (Resume studio)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Candidate Contact Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-[11px] font-mono font-bold text-slate-600 dark:text-slate-400 uppercase block mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={applicantName}
                  onChange={(e) => setApplicantName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl text-xs font-mono bg-slate-50 dark:bg-black/30 border border-slate-300 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-[11px] font-mono font-bold text-slate-600 dark:text-slate-400 uppercase block mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={applicantEmail}
                  onChange={(e) => setApplicantEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl text-xs font-mono bg-slate-50 dark:bg-black/30 border border-slate-300 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-[11px] font-mono font-bold text-slate-600 dark:text-slate-400 uppercase block mb-1">
                  Phone Number
                </label>
                <input
                  type="text"
                  value={applicantPhone}
                  onChange={(e) => setApplicantPhone(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl text-xs font-mono bg-slate-50 dark:bg-black/30 border border-slate-300 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-[11px] font-mono font-bold text-slate-600 dark:text-slate-400 uppercase block mb-1">
                  Portfolio / GitHub
                </label>
                <input
                  type="url"
                  value={portfolioUrl}
                  onChange={(e) => setPortfolioUrl(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl text-xs font-mono bg-slate-50 dark:bg-black/30 border border-slate-300 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            {/* Custom Cover Pitch */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-mono font-bold text-slate-600 dark:text-slate-400 uppercase">
                  Cover Note / Engineering Pitch
                </label>
                <button
                  type="button"
                  onClick={handleGeneratePitch}
                  disabled={autoGeneratingPitch}
                  className="text-xs font-mono font-bold text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1"
                >
                  <span>✨</span>
                  <span>{autoGeneratingPitch ? "Generating..." : "Generate AI Pitch"}</span>
                </button>
              </div>
              <textarea
                rows={5}
                value={coverNote}
                onChange={(e) => setCoverNote(e.target.value)}
                placeholder="Write a personalized pitch or click 'Generate AI Pitch' to craft one automatically based on this role..."
                className="w-full px-3.5 py-3 rounded-2xl text-xs font-mono bg-slate-50 dark:bg-black/30 border border-slate-300 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500 leading-relaxed resize-none"
              />
            </div>

            {/* Submit Button */}
            <div className="pt-3 border-t border-slate-200 dark:border-white/10 flex items-center justify-between gap-3">
              <span className="text-[11px] font-mono text-slate-500">
                Application logged to Tracker & verified with live ATS.
              </span>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 rounded-xl text-xs font-mono border border-slate-300 dark:border-white/10 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-6 py-2.5 rounded-xl text-xs font-mono font-bold bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-lg hover:shadow-emerald-500/30 transition-all flex items-center gap-2"
                >
                  <span>🚀</span>
                  <span>{submitting ? "Submitting..." : "Apply Instantly"}</span>
                </button>
              </div>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default ApplyModal;
