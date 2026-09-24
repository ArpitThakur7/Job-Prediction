/**
 * Typed API Client for Salvo Companion Engine
 */

export const SALVO_API_URL = process.env.NEXT_PUBLIC_SALVO_API || "http://127.0.0.1:4173";

export interface SalvoJob {
  url: string;
  company: string;
  title: string;
  location?: string;
  description?: string;
  postedAt?: number;
  source?: string;
  ats?: string;
  score?: number;
  relevanceScore?: number;
  predictionScore?: number;
  combinedScore?: number;
  reasons?: string[];
  blocked?: boolean;
  verdict?: string;
  isInternship?: boolean;
}

export interface SalvoStats {
  total: number;
  stale: number;
  title: number;
  location: number;
  experience: number;
  kept: number;
}

export interface ApplicationRecord {
  status: "discovered" | "prepared" | "applied" | "interview" | "offer" | "rejected" | "closed";
  company: string;
  title: string;
  score: number;
  location: string;
  source: string;
  resumeFile?: string;
  resumeFileLink?: string;
  coverFile?: string;
  coverFileLink?: string;
  atsMatch?: string;
  firstSeen: string;
  lastSeen: string;
  appliedOn?: string;
  notes?: string;
  url: string;
}

export interface DailyLogEntry {
  date: string;
  tracked: number;
  discovered: number;
  prepared: number;
  applied: number;
  interview: number;
  rejected: number;
}

export interface TailorResult {
  ok: boolean;
  meta?: {
    url: string;
    company: string;
    title: string;
    slug: string;
    tailoredAt: string;
    resumePdfPath: string;
    coverPdfPath: string;
    pageCount: number;
    keywordReport: { matched: string[]; missing: string[] };
    projectsUsed: string[];
    diff?: Array<{ type: string; description: string }>;
    truthReport?: { verified: boolean; violations: string[] };
  };
  mode?: string;
  status?: string;
  systemPrompt?: string;
  jdText?: string;
  instructions?: string;
  error?: string;
}

export const salvoClient = {
  async getHealth() {
    try {
      const res = await fetch(`${SALVO_API_URL}/api/health`);
      if (!res.ok) return { status: "offline" };
      return await res.json();
    } catch {
      return { status: "offline" };
    }
  },

  async startScan(mode: "global" | "india" = "global") {
    const res = await fetch(`${SALVO_API_URL}/api/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
    return await res.json();
  },

  createScanStream(scanId: string, onMessage: (data: any) => void, onError?: (err: any) => void) {
    const es = new EventSource(`${SALVO_API_URL}/api/scan/${scanId}/stream`);
    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (err) {
        console.error("Scan stream parse error", err);
      }
    };
    if (onError) es.onerror = onError;
    return es;
  },

  async getJobs(params: {
    mode?: "global" | "india";
    query?: string;
    source?: string;
    minScore?: number;
    page?: number;
    limit?: number;
  } = {}) {
    const query = new URLSearchParams();
    if (params.mode) query.set("mode", params.mode);
    if (params.query) query.set("query", params.query);
    if (params.source) query.set("source", params.source);
    if (params.minScore) query.set("minScore", String(params.minScore));
    if (params.page) query.set("page", String(params.page));
    if (params.limit) query.set("limit", String(params.limit));

    const res = await fetch(`${SALVO_API_URL}/api/jobs?${query.toString()}`);
    return await res.json();
  },

  async getJob(idOrUrl: string) {
    const encoded = encodeURIComponent(idOrUrl);
    const res = await fetch(`${SALVO_API_URL}/api/jobs/${encoded}`);
    return await res.json();
  },

  async tailorJob(jobUrl: string, options: { mode: "api" | "manual"; manualJson?: any }): Promise<TailorResult> {
    const encoded = encodeURIComponent(jobUrl);
    const res = await fetch(`${SALVO_API_URL}/api/jobs/${encoded}/tailor`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });
    return await res.json();
  },

  async prepJob(jobUrl: string) {
    const encoded = encodeURIComponent(jobUrl);
    const res = await fetch(`${SALVO_API_URL}/api/jobs/${encoded}/prep`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm: true }),
    });
    return await res.json();
  },

  async getApplications(): Promise<{ sheets: Record<string, ApplicationRecord[]>; dailyLog: DailyLogEntry[] }> {
    const res = await fetch(`${SALVO_API_URL}/api/applications`);
    return await res.json();
  },

  async patchApplication(url: string, field: "status" | "notes" | "appliedOn", value: any, sheet = "Applications") {
    const res = await fetch(`${SALVO_API_URL}/api/applications`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, field, value, sheet }),
    });
    return await res.json();
  },

  getExportUrl(format: "xlsx" | "csv") {
    return `${SALVO_API_URL}/api/applications?format=${format}`;
  },

  async getProfile() {
    const res = await fetch(`${SALVO_API_URL}/api/profile`);
    return await res.json();
  },

  async updateProfile(profile: any) {
    const res = await fetch(`${SALVO_API_URL}/api/profile`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile }),
    });
    return await res.json();
  },

  async getPortfolio() {
    const res = await fetch(`${SALVO_API_URL}/api/portfolio`);
    return await res.json();
  },

  async updatePortfolio(portfolio: any) {
    const res = await fetch(`${SALVO_API_URL}/api/portfolio`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ portfolio }),
    });
    return await res.json();
  },

  async getResume() {
    const res = await fetch(`${SALVO_API_URL}/api/resume`);
    return await res.json();
  },

  async updateResume(content: string) {
    const res = await fetch(`${SALVO_API_URL}/api/resume`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    return await res.json();
  },
};
