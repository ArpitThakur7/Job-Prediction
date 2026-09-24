# Architecture & Engineering Decisions (Salvo Integration)

This document tracks all key technical decisions, trade-offs, and rationale made during the integration of **Salvo (Agentic Job Discovery & Application Assistant)** into **Project 1 (Job Prediction 3D Platform)**.

---

## Decision 1: Runtime Model & Companion Engine Architecture
* **Status**: Accepted
* **Context**: Salvo relies on local Node.js capabilities: Playwright headless Chromium for rendering ATS-parseable single-column PDFs, Playwright headed Chromium for assisted form pre-filling, and local ExcelJS operations on `data/applications.xlsx`. Project 1 has a Next.js 16 frontend and a Python FastAPI backend.
* **Options Considered**:
  1. *Pure Next.js Server Actions / App Router API*: Bundle Playwright, ExcelJS, and providers directly into Next.js route handlers.
  2. *Full Python Port*: Rewrite all providers, Playwright scripts, and Excel handlers in Python.
  3. *Local Companion Node Engine (`engine/`)*: Keep Salvo's Node ESM architecture intact in a dedicated `/engine` directory with an HTTP REST/SSE server (running on `http://127.0.0.1:4173`), accessed by Next.js frontend pages directly or via Next.js proxy routes.
* **Decision**: **Option 3 (Companion Node Engine)**.
* **Rationale**:
  - Preserves 100% of Salvo's battle-tested providers, locator scripts, and Playwright DOM handlers without costly rewrite bugs.
  - Keeps Playwright browser automation cleanly isolated from Next.js build/runtime dependencies.
  - Adheres strictly to Salvo's local-first privacy guarantee: the engine binds strictly to `127.0.0.1` and runs on the user's local machine where their resume, `.env` credentials, and browser reside.
  - If the Next.js frontend is deployed to cloud/preview, it can either connect to the local companion engine via configured localhost base URL or operate in view/export mode.

---

## Decision 2: Storage Architecture & The Excel Single-Source-of-Truth
* **Status**: Accepted
* **Context**: Salvo's core philosophy mandates `data/applications.xlsx` as the single source of truth. Users frequently view and edit notes and statuses directly in Excel.
* **Decision**:
  - Implement a clean `Store` interface (`lib/store/interface.mjs`).
  - Provide `XlsxStore` as the primary implementation utilizing ExcelJS.
  - Provide an optional `DbStore` adapter for MongoDB synchronization if desired, while strictly enforcing that `applications.xlsx` remains canonical.
  - Enforce the non-destructive merge rule: on every re-scan or tracking run, user-owned columns (`status`, `appliedOn`, `notes`) are NEVER overwritten by scanner discoveries.
  - Implement external file change detection (using file watchers / mtime checks) so manual edits made in Excel are safely reflected in the web UI.

---

## Decision 3: Dual-Signal Scoring Architecture (Deterministic Rule Score + XGBoost ML)
* **Status**: Accepted
* **Context**: Salvo uses a deterministic 0-100 scoring engine (`lib/filter.mjs`) based on title matching, location/remote gates, skills, and keyword weights. Project 1 has a trained XGBoost ML classification model (`ml/model/xgb_matcher.pkl`) that predicts candidate-to-job match probabilities based on semantic features, experience gaps, and token overlap.
* **Decision**:
  - Maintain both scores as distinct, transparent signals:
    1. `relevanceScore` (0-100): Salvo's deterministic, explainable rule score with clear rationale badges (e.g., "title match", "open globally", "stack: react, node").
    2. `predictionScore` (0-100): Project 1's XGBoost ML model prediction probability.
    3. `combinedScore` (0-100): Configurable weighted blend (default: 60% relevance + 40% ML prediction), configured in `config/profile.yaml`.
  - Zero LLM calls for triage: All filtering and scoring remain 100% deterministic and free.

---

## Decision 4: Truth-Bounded Resume Tailoring & Security Guardrails
* **Status**: Accepted
* **Context**: Automated resume generation often suffers from hallucinations or prompt injection from untrusted job descriptions.
* **Decision**:
  - Inputs strictly bounded to `data/resume/resume.md` and `config/portfolio.yaml`.
  - The job description is strictly treated as untrusted data wrapped in isolation tokens to prevent prompt injection.
  - Add a post-generation verification step (`lib/truth-guard.mjs`): any employer, project metric, skill, or title not present in the master facts is stripped or flagged before PDF generation.
  - Support both API mode (Claude / Gemini, with model parameters configurable via environment variables) and zero-cost Manual mode (copy prompt / paste response).

---

## Decision 5: Assisted Form Pre-filler & The Golden Rule
* **Status**: Accepted
* **Context**: Automated job application bots risk account bans and inaccurate legal disclosures.
* **Decision**:
  - Playwright opens a visible browser window, navigates to the ATS application page (Greenhouse, Lever, Ashby, or generic fallback), fills basic factual fields (name, email, phone, links, resume PDF), and halts.
  - **The Golden Rule**: The system NEVER clicks Submit under any circumstance.
  - An automated test is established to inspect ATS filler source code and enforce that no submit button selectors or actions exist.
  - All subjective screening questions, demographic fields, and final review remain the user's explicit responsibility.

---

## Decision 6: Resilient Client Error Handling & Typed API Errors
* **Status**: Accepted
* **Context**: The original `salvoClient` methods called `res.json()` without checking `res.ok`, causing cryptic client-side failures.
* **Decision**:
  - Introduce a `SalvoApiError` class with `status`, `endpoint`, and semantic helpers (`isOffline`, `isConflict`).
  - All API calls routed through a shared `safeFetch()` that validates response status before parsing JSON.
  - Engine unreachable errors (`TypeError: fetch failed`) are caught and wrapped as `SalvoApiError(status: 0)`.
  - SSE scan stream now includes automatic reconnection with exponential backoff (max 3 retries, 1-8s intervals).

---

## Decision 7: Engine Connection Guard & Health-Aware UI
* **Status**: Accepted
* **Context**: Users frequently forget to start the companion engine, resulting in blank Salvo pages.
* **Decision**:
  - Implement `SalvoConnectionGuard` wrapper that checks `/api/health` on mount and polls every 10s.
  - When engine is offline: shows a diagnostic banner with the startup command and a "Copy" button.
  - Supports `degradedMode` (default true): still renders page content behind the banner.
  - Auto-recovers when the engine comes online.

---

## Decision 8: Scan Deduplication
* **Status**: Accepted
* **Context**: Double-clicking "Scan Boards Now" or concurrent scan triggers could corrupt `pipeline.json`.
* **Decision**:
  - Track `activeScanId` at module scope in the engine server.
  - New scan requests during an active scan return `409 Conflict` with the current scan ID and source.
  - `activeScanId` is cleared on scan completion or failure.

---

## Decision 9: Global Toast Notification System
* **Status**: Accepted
* **Context**: Status messages used inline state divs that disappear on navigation or re-render.
* **Decision**:
  - Implement `ToastProvider` context with fixed bottom-right container.
  - 4 toast types: `success`, `error`, `info`, `warning` with distinct color themes.
  - Spring-physics entry/exit animations via Framer Motion.
  - Auto-dismiss (4s default, 6s for errors), max 5 visible, manual dismiss button.

---

## Decision 10: Dynamic Scoring Calibration & Live Simulation Sandbox
* **Status**: Accepted
* **Context**: Scoring balance between deterministic rule match and XGBoost ML predictions was only configurable via raw YAML editing.
* **Decision**:
  - Add `/api/scoring` GET and POST endpoints to the engine server.
  - Implement `ScoringWeightsEditor` in Settings with linked dual slider (relevance vs. ML prediction summing to 100%).
  - Include an interactive simulation sandbox allowing users to test scores and preview how weights affect the final composite score and triage verdict in real time.

---

## Decision 11: Live Markdown Preview & Interactive Pipeline Funnel
* **Status**: Accepted
* **Context**: The Resume Hub only had a raw textarea without formatted output, and the application tracker had flat status tiles without stage drop-off telemetry.
* **Decision**:
  - Implement zero-dependency `MarkdownPreview` component with split/preview/edit view modes, word/character counter, and `Ctrl+S` keyboard shortcuts.
  - Implement `PipelineFunnel` with stage-by-stage conversion drop-off percentages, animated fill progress, and click-to-filter capability across Kanban and Table views.

