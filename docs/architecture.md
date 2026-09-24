# 🏗️ System Architecture: Salvo & Job Prediction 3D Platform

This document describes the high-level architecture of the integrated platform, detailing the local companion runtime model, data flow, scoring pipeline, and security boundaries.

---

## 1. High-Level Architecture Overview

The platform unites an enterprise ML candidate matching platform (Python FastAPI, XGBoost, MongoDB, Redis) with **Salvo** (Zero-Auth Job Discovery, Fit-Scoring, Truth-Bounded Resume Tailoring & Form Pre-filler) and a Next.js 16 3D WebGL user interface.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Next.js 16 Frontend                             │
│                     (React 19 • Three.js WebGL)                        │
│                                                                        │
│   /jobs              /jobs/[id]           /applications     /resume    │
│  (3D Feed)         (Fit Breakdown)       (Excel Tracker)   (Truth Bank)│
└──────────────┬───────────────────────────────────┬─────────────────────┘
               │ HTTP / SSE                        │ HTTP / REST
               ▼                                   ▼
┌──────────────────────────────┐    ┌────────────────────────────────────┐
│      Salvo Engine (Node)     │    │      FastAPI Backend (Python)      │
│         Port 4173            │    │             Port 8000              │
│                              │    │                                    │
│ • Zero-Auth Discovery Engine │    │ • Supervised XGBoost Matcher       │
│ • Deterministic Filter/Score │    │ • SHAP Feature Attributions        │
│ • Truth-Bounded Tailoring    │    │ • MongoDB 7 / Redis Cache          │
│ • Playwright Form Pre-filler │    │ • RAG Career Coach                 │
│ • Canonical ExcelJS Store    │    │ • Kafka Stream & Spark Batches     │
└──────────────┬───────────────┘    └────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Local File System (Privacy Boundary)                 │
│                                                                        │
│  data/applications.xlsx   data/resume/resume.md   config/profile.yaml  │
│  (Primary Tracker)        (Master Truth Source)   (Search Criteria)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Subsystems

### 2.1 Zero-Auth Discovery Engine (`engine/providers/`)
Consumes only unauthenticated public ATS endpoints (no login credentials, no bot-detection risk):
- **Greenhouse API**: `https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true`
- **Lever API**: `https://api.lever.co/v0/postings/{company}?mode=json`
- **Ashby API**: `https://api.ashbyhq.com/posting-api/job-board/{company}`
- **Aggregators**: RemoteOK, Remotive, Hacker News "Who is Hiring", Unstop (`/api/public/*` only).
- **Provider Contract**: Every provider is an independent file exporting `{ id, detect, fetch }`.

### 2.2 Dual-Signal Scoring Pipeline (`engine/lib/scoring.mjs`)
1. **Deterministic Rule Score (0–100)**: `engine/lib/filter.mjs` calculates normalized fit scores against `config/profile.yaml` without LLM calls. Provides explainable reasons (`stack: react, node`, `open globally`, `title match`).
2. **XGBoost ML Score (0–100)**: Evaluates semantic similarity, experience gaps, and skill overlap.
3. **Combined Weighted Score**:
   $$\text{Score}_{\text{combined}} = (w_{\text{relevance}} \times \text{Score}_{\text{det}}) + (w_{\text{prediction}} \times \text{Score}_{\text{ML}})$$
   Configured in `engine/config/scoring.yaml`.

### 2.3 Truth-Bounded Tailoring & Security (`engine/lib/truth-guard.mjs`)
- Inputs are restricted to `data/resume/resume.md` and `config/portfolio.yaml`.
- The job description is wrapped in security boundaries (`<UNTRUSTED_JOB_DESCRIPTION>`) to prevent prompt injection.
- Post-generation verification strips or flags any hallucinated employer, date, skill, or metric before rendering.
- Renders an ATS-parseable single-column PDF with Computer Modern fonts using Playwright.
- Supports automated API mode (Claude / Gemini) and zero-cost Manual mode (prompt copy/paste).

### 2.4 Assisted Form Pre-filler & The Golden Rule (`engine/lib/ats/`)
- Playwright opens a visible browser window, attaches the tailored resume PDF, pre-fills factual contact info and `.env` work authorization answers.
- **The Golden Rule**: The system **NEVER** clicks submit. Custom screening questions and final submission belong to the candidate.
- Automated tests enforce that no submit button selectors exist in filler code.

### 2.5 Storage Layer (`engine/lib/store/xlsx-store.mjs`)
- `data/applications.xlsx` is the canonical single source of truth.
- **Non-destructive re-scan**: Preserves user-owned columns (`status`, `appliedOn`, `notes`) across scans.
- Sanitizes cell content against formula injection.
- Tracks daily metrics in the `Daily Log` sheet for funnel analytics.