"use client";

import React, { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Bot, FileSearch, MapPin, Radar, ScanSearch, Send, Sparkles, Target } from "lucide-react";
import { useApp } from "@/context/AppContext";
import { salvoClient, SalvoJob } from "@/lib/salvoClient";
import { fitColor, fitLabel, jobScore } from "@/lib/jobScore";

const JobConstellation3D = dynamic(() => import("@/components/salvo/JobConstellation3D"), {
  ssr: false,
  loading: () => <div className="w-full h-full rounded-[32px] animate-pulse" style={{ background: "var(--glass-bg)" }} />,
});

const steps = [
  { icon: Radar, title: "Scan the boards", body: "The Salvo engine checks Greenhouse, Lever, Ashby, RemoteOK and more for new openings.", href: "/jobs?scan=1", cta: "Run a scan" },
  { icon: Target, title: "Score every job", body: "Each posting gets a fit score from your rules and the prediction model.", href: "/jobs", cta: "See scores" },
  { icon: Sparkles, title: "Tailor your resume", body: "Rewrite your resume for one job, without inventing anything new.", href: "/resume", cta: "Open studio" },
  { icon: Send, title: "Apply and track", body: "Mark what you applied to and follow it through to an offer.", href: "/applications", cta: "Open tracker" },
];

const tools = [
  { icon: ScanSearch, title: "Resume check", body: "Find the skills real postings ask for that your resume is missing.", href: "/analyzer" },
  { icon: FileSearch, title: "Job post reader", body: "Paste a posting and get its requirements as a checklist.", href: "/parser" },
  { icon: Bot, title: "Career coach", body: "Practice interview answers and get resume feedback.", href: "/coach" },
];

function timeAgo(iso: string | null) {
  if (!iso) return null;
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${Math.max(1, mins)} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs} hours ago`;
  return `${Math.round(hrs / 24)} days ago`;
}

export default function Home() {
  const router = useRouter();
  const { currentThemeColors } = useApp();
  const [jobs, setJobs] = useState<SalvoJob[]>([]);
  const [scannedAt, setScannedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let live = true;
    salvoClient
      .getJobs({ mode: "global", limit: 100 })
      .then((data) => {
        if (!live) return;
        setJobs((data.jobs || []).filter((j: SalvoJob) => !j.blocked));
        setScannedAt(data.scannedAt || null);
      })
      .catch(() => {})
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, []);

  const ranked = useMemo(() => [...jobs].sort((a, b) => jobScore(b) - jobScore(a)), [jobs]);
  const strong = ranked.filter((j) => jobScore(j) >= 75).length;
  const openJob = (j: SalvoJob) => router.push(`/jobs?focus=${encodeURIComponent(j.url)}`);

  return (
    <div className="max-w-[1280px] mx-auto space-y-14 pb-10">
      {/* Hero: the live feed itself */}
      <section className="glass rounded-[36px] overflow-hidden grid lg:grid-cols-[1.05fr_1fr] min-h-[560px]">
        <motion.div
          initial="hidden"
          animate="show"
          variants={{ show: { transition: { staggerChildren: 0.09 } } }}
          className="p-7 sm:p-10 lg:p-14 flex flex-col justify-center gap-6"
        >
          <motion.h1
            variants={rise}
            className="font-display font-extrabold text-[44px] sm:text-[60px] lg:text-[72px] leading-[0.95]"
          >
            Every job, scored against your resume.
          </motion.h1>
          <motion.p variants={rise} className="text-lg leading-relaxed max-w-[34rem]" style={{ color: "var(--theme-text-muted)" }}>
            Fletch scans the job boards, ranks each posting by how well it fits you, and helps you tailor your resume and apply.
          </motion.p>
          <motion.div variants={rise} className="flex flex-wrap gap-3">
            <Link
              href="/jobs"
              className="px-6 py-3.5 rounded-2xl font-semibold text-white shadow-lg transition-transform hover:-translate-y-0.5"
              style={{ background: `linear-gradient(135deg, ${currentThemeColors.primary}, ${currentThemeColors.accent})`, boxShadow: `0 12px 30px -8px ${currentThemeColors.glow}` }}
            >
              Open job feed
            </Link>
            <Link href="/jobs?scan=1" className="glass-strong px-6 py-3.5 rounded-2xl font-semibold transition-transform hover:-translate-y-0.5">
              Scan boards now
            </Link>
          </motion.div>
          <motion.p variants={rise} className="text-sm" style={{ color: "var(--theme-text-muted)" }}>
            {loading ? (
              "Loading your feed…"
            ) : jobs.length ? (
              <>
                <strong className="tabular" style={{ color: "var(--theme-text)" }}>{jobs.length}</strong> jobs scored,{" "}
                <strong className="tabular" style={{ color: "var(--fit-high)" }}>{strong}</strong> strong fits
                {scannedAt && <>. Last scan {timeAgo(scannedAt)}.</>}
              </>
            ) : (
              "No jobs yet. Run a scan to fill your feed."
            )}
          </motion.p>
        </motion.div>

        <div className="relative min-h-[380px] lg:min-h-full">
          {jobs.length > 0 && <JobConstellation3D jobs={ranked.slice(0, 48)} primary={currentThemeColors.primary} onPick={openJob} />}
          {!loading && jobs.length > 0 && (
            <div className="absolute left-5 right-5 bottom-5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs pointer-events-none" style={{ color: "var(--theme-text-muted)" }}>
              {[80, 60, 40].map((s) => (
                <span key={s} className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: fitColor(s) }} />
                  {fitLabel(s)}
                </span>
              ))}
              <span className="ml-auto">Closer to you means a better fit. Click a job to open it.</span>
            </div>
          )}
        </div>
      </section>

      {/* How it works — a real sequence */}
      <section className="space-y-5">
        <h2 className="font-display text-3xl font-bold px-1">How Fletch works</h2>
        <ol className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {steps.map((s, i) => {
            const Icon = s.icon;
            return (
              <li key={s.title} className="glass rounded-[28px] p-6 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <span className="w-11 h-11 rounded-2xl grid place-items-center" style={{ background: `${currentThemeColors.primary}1a`, color: currentThemeColors.primary }}>
                    <Icon size={20} />
                  </span>
                  <span className="font-display text-4xl font-extrabold opacity-15 tabular">{i + 1}</span>
                </div>
                <h3 className="font-display text-xl font-bold">{s.title}</h3>
                <p className="text-[15px] leading-relaxed flex-1" style={{ color: "var(--theme-text-muted)" }}>{s.body}</p>
                <Link href={s.href} className="text-sm font-semibold" style={{ color: currentThemeColors.primary }}>
                  {s.cta}
                </Link>
              </li>
            );
          })}
        </ol>
      </section>

      {/* Best matches right now */}
      <section className="space-y-5">
        <div className="flex items-end justify-between gap-4 px-1">
          <h2 className="font-display text-3xl font-bold">Your best matches right now</h2>
          <Link href="/jobs" className="text-sm font-semibold shrink-0" style={{ color: currentThemeColors.primary }}>
            See all {jobs.length || ""} jobs
          </Link>
        </div>
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {loading
            ? Array.from({ length: 6 }).map((_, i) => <div key={i} className="glass rounded-[24px] h-[120px] animate-pulse" />)
            : ranked.slice(0, 6).map((j) => {
                const s = jobScore(j);
                return (
                  <button
                    key={j.url}
                    onClick={() => openJob(j)}
                    className="glass rounded-[24px] p-5 text-left flex gap-4 items-start transition-transform hover:-translate-y-0.5"
                  >
                    <span className="shrink-0 w-14 h-14 rounded-2xl grid place-items-center font-display font-extrabold text-lg tabular text-white" style={{ background: fitColor(s) }}>
                      {s}
                    </span>
                    <span className="min-w-0">
                      <span className="block font-semibold leading-snug line-clamp-2">{j.title}</span>
                      <span className="block text-sm mt-0.5 truncate" style={{ color: "var(--theme-text-muted)" }}>{j.company}</span>
                      <span className="flex items-center gap-1 text-xs mt-1.5" style={{ color: "var(--theme-text-muted)" }}>
                        <MapPin size={12} />
                        <span className="truncate">{j.location || "Location not listed"}</span>
                      </span>
                    </span>
                  </button>
                );
              })}
        </div>
        {!loading && jobs.length === 0 && (
          <div className="glass rounded-[24px] p-8 text-center space-y-3">
            <p className="font-semibold">Your feed is empty.</p>
            <p className="text-sm" style={{ color: "var(--theme-text-muted)" }}>Start the Salvo engine and run a scan to pull in jobs.</p>
            <Link href="/jobs?scan=1" className="inline-block text-sm font-semibold" style={{ color: currentThemeColors.primary }}>Run a scan</Link>
          </div>
        )}
      </section>

      {/* Supporting tools */}
      <section className="space-y-5">
        <h2 className="font-display text-3xl font-bold px-1">Sharpen your resume</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {tools.map((t) => {
            const Icon = t.icon;
            return (
              <Link key={t.href} href={t.href} className="glass rounded-[24px] p-5 flex gap-4 items-start transition-transform hover:-translate-y-0.5">
                <Icon size={22} className="shrink-0 mt-0.5" style={{ color: currentThemeColors.primary }} />
                <span>
                  <span className="block font-semibold">{t.title}</span>
                  <span className="block text-sm mt-1 leading-relaxed" style={{ color: "var(--theme-text-muted)" }}>{t.body}</span>
                </span>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}

const rise = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};
