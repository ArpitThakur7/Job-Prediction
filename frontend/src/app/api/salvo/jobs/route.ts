import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const SALVO_API_URL = process.env.SALVO_API_URL || process.env.NEXT_PUBLIC_SALVO_API || "http://127.0.0.1:4173";

function getPipelineData(mode: string) {
  const root = path.resolve(process.cwd(), "..");
  const filename = mode === "india" ? "pipeline-india.json" : "pipeline.json";
  const primaryPath = path.join(root, "data", filename);
  const fallbackPath = path.join(process.cwd(), "data", filename);

  const targetPath = fs.existsSync(primaryPath)
    ? primaryPath
    : fs.existsSync(fallbackPath)
    ? fallbackPath
    : null;

  if (!targetPath) {
    return { scannedAt: null, stats: { total: 0, kept: 0 }, jobs: [] };
  }

  try {
    const raw = fs.readFileSync(targetPath, "utf-8");
    return JSON.parse(raw);
  } catch (err) {
    console.error("Failed to read pipeline file:", err);
    return { scannedAt: null, stats: { total: 0, kept: 0 }, jobs: [] };
  }
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const mode = searchParams.get("mode") === "india" ? "india" : "global";
  const query = (searchParams.get("query") || "").toLowerCase().trim();
  const source = (searchParams.get("source") || "").toLowerCase().trim();
  const minScore = Number(searchParams.get("minScore") || 0);
  const experience = (searchParams.get("experience") || "").toLowerCase().trim();
  const workType = (searchParams.get("workType") || "").toLowerCase().trim();
  const sortBy = searchParams.get("sortBy") || "score_desc";
  const page = Math.max(1, Number(searchParams.get("page") || 1));
  const limit = Math.max(1, Math.min(100, Number(searchParams.get("limit") || 18)));
  const singleUrl = searchParams.get("url") || searchParams.get("id");

  // 1. First attempt proxying to active Salvo Engine on port 4173
  try {
    const salvoRes = await fetch(`${SALVO_API_URL}/api/jobs?${searchParams.toString()}`, {
      signal: AbortSignal.timeout(1500),
      headers: { Accept: "application/json" },
    });
    if (salvoRes.ok) {
      const data = await salvoRes.json();
      return NextResponse.json({ ...data, source: "live_engine" });
    }
  } catch {
    // Engine offline or unreachable: gracefully fall back to local pipeline dataset
  }

  // 2. Read from disk fallback
  const pipeline = getPipelineData(mode);
  let jobs: any[] = pipeline.jobs || [];

  // Single job lookup
  if (singleUrl) {
    const decoded = decodeURIComponent(singleUrl).trim().toLowerCase();
    const found = jobs.find((j) => {
      const jUrl = (j.url || "").toLowerCase();
      return jUrl === decoded || (decoded.length > 15 && jUrl.includes(decoded));
    });
    if (found) {
      return NextResponse.json({ job: found, source: "local_cache" });
    }
    // Also check other mode if not found
    const altPipeline = getPipelineData(mode === "india" ? "global" : "india");
    const altFound = (altPipeline.jobs || []).find((j: any) => {
      const jUrl = (j.url || "").toLowerCase();
      return jUrl === decoded || (decoded.length > 15 && jUrl.includes(decoded));
    });
    if (altFound) {
      return NextResponse.json({ job: altFound, source: "local_cache" });
    }
    return NextResponse.json({ error: "Job not found" }, { status: 404 });
  }

  // Filters
  if (query) {
    jobs = jobs.filter((j) => {
      const title = String(j.title || "").toLowerCase();
      const company = String(j.company || "").toLowerCase();
      const loc = String(j.location || "").toLowerCase();
      const desc = String(j.description || "").toLowerCase();
      const reasons = Array.isArray(j.reasons) ? j.reasons.join(" ").toLowerCase() : "";
      return title.includes(query) || company.includes(query) || loc.includes(query) || desc.includes(query) || reasons.includes(query);
    });
  }

  if (source && source !== "all") {
    jobs = jobs.filter((j) => {
      const s = String(j.source || j.ats || "").toLowerCase();
      return s.includes(source);
    });
  }

  if (minScore > 0) {
    jobs = jobs.filter((j) => {
      const s = j.combinedScore ?? (j.score ? Math.round((j.score / 5) * 100) : 0);
      return s >= minScore;
    });
  }

  if (experience) {
    if (experience === "internship") {
      jobs = jobs.filter((j) => j.isInternship || /intern|entry|trainee|apprentice/i.test(j.title || ""));
    } else if (experience === "senior") {
      jobs = jobs.filter((j) => /senior|lead|principal|architect|staff/i.test(j.title || ""));
    }
  }

  if (workType === "remote") {
    jobs = jobs.filter((j) => /remote|anywhere|worldwide|wfh/i.test(String(j.location || "")));
  }

  // Sorting
  jobs.sort((a, b) => {
    const scoreA = a.combinedScore ?? (a.score ? Math.round((a.score / 5) * 100) : 0);
    const scoreB = b.combinedScore ?? (b.score ? Math.round((b.score / 5) * 100) : 0);

    if (sortBy === "score_desc") return scoreB - scoreA;
    if (sortBy === "score_asc") return scoreA - scoreB;
    if (sortBy === "newest") return (b.postedAt || 0) - (a.postedAt || 0);
    if (sortBy === "company") return String(a.company || "").localeCompare(String(b.company || ""));
    return scoreB - scoreA;
  });

  const total = jobs.length;
  const start = (page - 1) * limit;
  const paginated = jobs.slice(start, start + limit);

  return NextResponse.json({
    jobs: paginated,
    total,
    page,
    limit,
    totalPages: Math.ceil(total / limit),
    scannedAt: pipeline.scannedAt,
    stats: pipeline.stats,
    source: "local_cache",
    engineOnline: false,
  });
}
