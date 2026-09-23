"use client";

import React, { useState } from "react";
import { X, Edit3, CheckCircle2, AlertTriangle, Sparkles, User, Mail, Phone, Code, BookOpen } from "lucide-react";

interface CandidateDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: any;
  apiBase: string;
  onCandidateUpdated?: () => void;
}

export default function CandidateDetailModal({
  isOpen,
  onClose,
  candidate,
  apiBase,
  onCandidateUpdated,
}: CandidateDetailModalProps) {
  if (!isOpen || !candidate) return null;

  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const structured = candidate.structured || {};
  const contact = structured.contact || {};
  const skills = structured.skills || {};
  const ats = candidate.ats_score || {};
  const breakdown = ats.breakdown || {};
  const issues = ats.issues || [];

  // Edit form state
  const [name, setName] = useState(contact.name || candidate.candidate_name || "");
  const [email, setEmail] = useState(contact.email || candidate.email || "");
  const [phone, setPhone] = useState(contact.phone || candidate.phone || "");
  const [techSkills, setTechSkills] = useState(
    (skills.technical || candidate.skills || []).join(", ")
  );
  const [summary, setSummary] = useState(structured.summary || "");

  const handleSaveOverrides = async () => {
    setSaving(true);
    try {
      const skillsArray = techSkills
        .split(",")
        .map((s: string) => s.trim())
        .filter(Boolean);

      const res = await fetch(`${apiBase}/resume/${candidate.resume_id}/fields`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          email,
          phone,
          summary,
          technical_skills: skillsArray,
        }),
      });

      if (res.ok) {
        setIsEditing(false);
        if (onCandidateUpdated) onCandidateUpdated();
      }
    } catch (err) {
      console.error("Failed to update candidate fields:", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-slate-900 border border-slate-700/60 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-800/80 border-b border-slate-700/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 font-bold">
              {ats.overall_score || 0}%
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                {name || "Candidate Profile"}
                <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800">
                  ATS Verified
                </span>
              </h2>
              <p className="text-xs text-slate-400">{email || "No email provided"}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-xs font-semibold text-slate-200 flex items-center gap-1.5 transition-all"
            >
              <Edit3 className="w-3.5 h-3.5" />
              {isEditing ? "Cancel Edit" : "Recruiter Override Mode"}
            </button>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 rounded-lg transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {/* Low Parse Confidence Alert */}
          {(ats.parse_confidence_score < 75 || candidate.parse_confidence < 75) && (
            <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-300 text-xs flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
              <div>
                <strong className="font-semibold text-amber-200">Parsing Confidence Flag:</strong> Some attributes parsed with low confidence. Use Recruiter Override Mode to verify and edit missing fields.
              </div>
            </div>
          )}

          {/* Edit Form vs View Mode */}
          {isEditing ? (
            <div className="space-y-4 bg-slate-800/40 p-4 rounded-xl border border-slate-700/50">
              <h3 className="text-sm font-semibold text-cyan-400 flex items-center gap-2">
                <Edit3 className="w-4 h-4" /> Recruiter Field Overrides
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Full Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Email</label>
                  <input
                    type="text"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Phone</label>
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 mb-1 block">Technical Skills (comma-separated)</label>
                <input
                  type="text"
                  value={techSkills}
                  onChange={(e) => setTechSkills(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 mb-1 block">Summary</label>
                <textarea
                  rows={3}
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex justify-end">
                <button
                  onClick={handleSaveOverrides}
                  disabled={saving}
                  className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs font-bold text-white shadow-lg transition-all flex items-center gap-2"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {saving ? "Saving Changes..." : "Save & Recalculate ATS Score"}
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Left Column: ATS Score Category Breakdown */}
              <div className="bg-slate-800/40 p-4 rounded-xl border border-slate-700/50 space-y-4">
                <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-cyan-400" /> Category Breakdown
                </h3>

                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs text-slate-300 mb-1">
                      <span>Keyword Match (30%)</span>
                      <span className="font-semibold text-cyan-400">{breakdown.keyword_match || 0} / 30</span>
                    </div>
                    <div className="w-full bg-slate-700/60 rounded-full h-2">
                      <div
                        className="bg-cyan-500 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${((breakdown.keyword_match || 0) / 30) * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs text-slate-300 mb-1">
                      <span>Parseability (25%)</span>
                      <span className="font-semibold text-cyan-400">{breakdown.parseability || 0} / 25</span>
                    </div>
                    <div className="w-full bg-slate-700/60 rounded-full h-2">
                      <div
                        className="bg-cyan-500 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${((breakdown.parseability || 0) / 25) * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs text-slate-300 mb-1">
                      <span>Content Quality (20%)</span>
                      <span className="font-semibold text-cyan-400">{breakdown.content_quality || 0} / 20</span>
                    </div>
                    <div className="w-full bg-slate-700/60 rounded-full h-2">
                      <div
                        className="bg-cyan-500 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${((breakdown.content_quality || 0) / 20) * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs text-slate-300 mb-1">
                      <span>Section Completeness (15%)</span>
                      <span className="font-semibold text-cyan-400">{breakdown.section_completeness || 0} / 15</span>
                    </div>
                    <div className="w-full bg-slate-700/60 rounded-full h-2">
                      <div
                        className="bg-cyan-500 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${((breakdown.section_completeness || 0) / 15) * 100}%` }}
                      />
                    </div>
                  </div>

                  {breakdown.recency_boost > 0 && (
                    <div className="p-2.5 rounded-lg bg-cyan-950/30 border border-cyan-800/40 text-xs text-cyan-300 flex justify-between items-center">
                      <span>Recency & Duration Boost</span>
                      <span className="font-bold text-cyan-400">+{breakdown.recency_boost} pts</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Key Issues & Highlights */}
              <div className="bg-slate-800/40 p-4 rounded-xl border border-slate-700/50 space-y-4">
                <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Extracted Skills & Highlights
                </h3>

                <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto">
                  {(skills.technical || candidate.skills || []).map((sk: string, idx: number) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md bg-cyan-950/80 border border-cyan-700/50 text-cyan-300 text-xs font-medium"
                    >
                      {sk}
                    </span>
                  ))}
                </div>

                {issues.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-slate-700/40">
                    <span className="text-xs font-semibold text-slate-400 block">Identified ATS Issues ({issues.length})</span>
                    <div className="space-y-1.5 max-h-32 overflow-y-auto">
                      {issues.map((iss: any, idx: number) => (
                        <div
                          key={idx}
                          className="text-xs p-2 rounded-lg bg-slate-900/60 border border-slate-700/40 text-slate-300 flex items-start gap-2"
                        >
                          <span
                            className={`w-2 h-2 rounded-full mt-1 shrink-0 ${
                              iss.severity === "high"
                                ? "bg-rose-500"
                                : iss.severity === "medium"
                                ? "bg-amber-500"
                                : "bg-cyan-500"
                            }`}
                          />
                          <span>{iss.message}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
