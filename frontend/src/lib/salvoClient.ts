/**
 * Typed API Client for Salvo Companion Engine
 * All methods check res.ok and throw SalvoApiError on failures.
 */

export const SALVO_API_URL = process.env.NEXT_PUBLIC_SALVO_API || "http://127.0.0.1:4173";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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

export interface ScoringConfig {
  weights: {
    relevance: number;
    prediction: number;
  };
  thresholds: {
    apply_min: number;
    high_confidence: number;
    max_per_company?: number;
  };
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

export interface EngineHealth {
  status: "online" | "offline";
  engine?: string;
  version?: string;
  port?: number;
  providersCount?: number;
  excelStoreConnected?: boolean;
  playwrightAvailable?: boolean;
  activeScanId?: string | null;
  timestamp?: string;
}

// ---------------------------------------------------------------------------
// Error class
// ---------------------------------------------------------------------------

export class SalvoApiError extends Error {
  public status: number;
  public endpoint: string;
  public body: any;

  constructor(message: string, status: number, endpoint: string, body?: any) {
    super(message);
    this.name = "SalvoApiError";
    this.status = status;
    this.endpoint = endpoint;
    this.body = body;
  }

  get isOffline() {
    return this.status === 0;
  }

  get isConflict() {
    return this.status === 409;
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function safeFetch(endpoint: string, init?: RequestInit): Promise<any> {
  let res: Response;
  try {
    res = await fetch(`${SALVO_API_URL}${endpoint}`, init);
  } catch (err: any) {
    throw new SalvoApiError(
      `Engine unreachable at ${SALVO_API_URL}. Is the Salvo engine running?`,
      0,
      endpoint,
    );
  }

  if (!res.ok) {
    let body: any = null;
    try {
      body = await res.json();
    } catch {}
    throw new SalvoApiError(
      body?.error || `Request failed: ${res.status} ${res.statusText}`,
      res.status,
      endpoint,
      body,
    );
  }

  return await res.json();
}

async function safeFetchRaw(endpoint: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`${SALVO_API_URL}${endpoint}`, init);
  } catch (err: any) {
    throw new SalvoApiError(
      `Engine unreachable at ${SALVO_API_URL}. Is the Salvo engine running?`,
      0,
      endpoint,
    );
  }
  if (!res.ok) {
    let body: any = null;
    try { body = await res.json(); } catch {}
    throw new SalvoApiError(
      body?.error || `Request failed: ${res.status} ${res.statusText}`,
      res.status,
      endpoint,
      body,
    );
  }
  return res;
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

export const salvoClient = {
  async getHealth(): Promise<EngineHealth> {
    try {
      const res = await fetch(`${SALVO_API_URL}/api/health`, { signal: AbortSignal.timeout(3000) });
      if (!res.ok) return { status: "offline" };
      return await res.json();
    } catch {
      return { status: "offline" };
    }
  },

  async startScan(mode: "global" | "india" = "global") {
    return safeFetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
  },

  /**
   * Creates an SSE stream with automatic reconnection and exponential backoff.
   * Returns a controller object to close the stream.
   */
  createScanStream(
    scanId: string,
    onMessage: (data: any) => void,
    onError?: (err: any) => void,
    options?: { maxRetries?: number },
  ) {
    const maxRetries = options?.maxRetries ?? 3;
    let retries = 0;
    let es: EventSource | null = null;
    let closed = false;

    function connect() {
      if (closed) return;
      es = new EventSource(`${SALVO_API_URL}/api/scan/${scanId}/stream`);

      es.onmessage = (event) => {
        retries = 0; // reset on successful message
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
          // Auto-close on terminal events
          if (data.type === "done" || data.type === "error") {
            controller.close();
          }
        } catch (err) {
          console.error("[SalvoSSE] Parse error:", err);
        }
      };

      es.onerror = (err) => {
        es?.close();
        if (closed) return;
        if (retries < maxRetries) {
          retries++;
          const delay = Math.min(1000 * Math.pow(2, retries), 8000);
          console.warn(`[SalvoSSE] Reconnecting in ${delay}ms (attempt ${retries}/${maxRetries})...`);
          onMessage({ type: "reconnecting", attempt: retries, maxRetries });
          setTimeout(connect, delay);
        } else {
          console.error("[SalvoSSE] Max retries exhausted.");
          if (onError) onError(err);
          onMessage({ type: "error", error: "SSE connection lost after max retries." });
        }
      };
    }

    const controller = {
      close: () => {
        closed = true;
        es?.close();
      },
    };

    connect();
    return controller;
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

    return safeFetch(`/api/jobs?${query.toString()}`);
  },

  async getJob(idOrUrl: string) {
    const encoded = encodeURIComponent(idOrUrl);
    try {
      return await safeFetch(`/api/jobs?url=${encoded}`);
    } catch {
      return await safeFetch(`/api/jobs/${encoded}`);
    }
  },

  async tailorJob(jobUrl: string, options: { mode: "api" | "manual"; manualJson?: any }): Promise<TailorResult> {
    const encoded = encodeURIComponent(jobUrl);
    return safeFetch(`/api/jobs/${encoded}/tailor`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });
  },

  async prepJob(jobUrl: string) {
    const encoded = encodeURIComponent(jobUrl);
    return safeFetch(`/api/jobs/${encoded}/prep`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm: true }),
    });
  },

  async getApplications(): Promise<{ sheets: Record<string, ApplicationRecord[]>; dailyLog: DailyLogEntry[] }> {
    return safeFetch("/api/applications");
  },

  async patchApplication(url: string, field: "status" | "notes" | "appliedOn", value: any, sheet = "Applications") {
    return safeFetch("/api/applications", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, field, value, sheet }),
    });
  },

  getExportUrl(format: "xlsx" | "csv") {
    return `${SALVO_API_URL}/api/applications?format=${format}`;
  },

  async getProfile() {
    return safeFetch("/api/profile");
  },

  async updateProfile(profile: any) {
    return safeFetch("/api/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile }),
    });
  },

  async getPortfolio() {
    return safeFetch("/api/portfolio");
  },

  async updatePortfolio(portfolio: any) {
    return safeFetch("/api/portfolio", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ portfolio }),
    });
  },

  async getResume() {
    return safeFetch("/api/resume");
  },

  async updateResume(content: string) {
    return safeFetch("/api/resume", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
  },

  async getProviderHealth() {
    return safeFetch("/api/providers/health");
  },

  async getScoringConfig(): Promise<{ scoring: ScoringConfig }> {
    return safeFetch("/api/scoring");
  },

  async updateScoringConfig(scoring: ScoringConfig) {
    return safeFetch("/api/scoring", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scoring }),
    });
  },
};
