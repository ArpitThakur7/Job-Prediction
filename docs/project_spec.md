# 🚀 JOB-AI 3D Platform — Comprehensive Project Brief & Technical Architecture

> **Executive Overview**  
> **JOB-AI** is a state-of-the-art, AI-powered 3D Career Matching and RAG Intelligence Platform. It bridges the gap between candidates and job markets by combining **predictive machine learning (XGBoost)**, **vector similarity search (Pinecone)**, **document databases (MongoDB)**, **interactive 3D WebGL telemetry (Three.js)**, and an **interdependent multi-provider AI fallback chain (Groq, Gemini, OpenRouter, OpenAI, Anthropic)** with continuous context memory.

---

## 📊 1. Dataset & High-Volume Data Pipeline Architecture

The platform processes and indexes large-scale raw industry datasets containing candidate resumes and job postings across 17 CSV files and multiple ZIP archives.

### Ingestion Metrics & Database Scale
| Metric | Volume / Specification | Storage Layer |
| :--- | :--- | :--- |
| **Job Postings & Companies** | **123,999 Records** | MongoDB (`job_ai_db.jobs`) & Pinecone (`jobs` namespace) |
| **Candidate Resumes** | **54,964 Records** | MongoDB (`job_ai_db.resumes`) & Pinecone (`resumes` namespace) |
| **Vector Embedding Model** | `all-MiniLM-L6-v2` (384-dimensional dense vectors) | Local PyTorch Transformer / SentenceTransformers |
| **Vector Database Index** | `job-ai-index` (Cosine similarity, 384-dim) | Pinecone Vector Database |
| **Ingestion Pipeline Script** | `scripts/extract_and_ingest_zips.py` | Multi-archive resumable batch ingestion with MongoDB skip-checking |

---

## 🤖 2. Interdependent Multi-Provider AI RAG & Memory Engine

A key innovation of the platform is its **5-Tier Auto-Failover LLM Pipeline** and **Dual-Layer Context Memory System**, ensuring zero downtime and continuous conversational history.

```
[ User Query ] ──► [ Dual-Layer Memory ] ──► [ RAG Vector Search (Pinecone/Local) ]
                                                        │
┌───────────────────────────────────────────────────────┴───────────────────────────────────────────────────────┐
│                                   AUTOMATIC MULTI-PROVIDER FALLBACK CHAIN                                      │
├───────────────┬───────────────────┬───────────────────────────┬───────────────────┬───────────────────────────┤
│ 1. Primary    │ 2. Groq (Free)    │ 3. Gemini 1.5 (Free)      │ 4. OpenRouter     │ 5. OpenAI / Anthropic     │
│    (Selected) │    (LLaMA 3.1 8B)  │    (Google Free Quota)   │    (20+ Free)    │    (GPT-4o / Claude 3.5)  │
└───────────────┴─────────┬─────────┴─────────────┬─────────────┴─────────┬─────────┴─────────────┬─────────────┘
                          │ (If 429/401/500 Error)│                       │                       │
                          ▼                       ▼                       ▼                       ▼
                                └───► [ Final Fallback: Local RAG Intelligence Engine ]
```

### Key RAG Features:
1. **Multi-Provider Auto-Failover**:
   - Primary LLM provider is configurable via Settings (`Groq`, `Gemini`, `OpenRouter`, `OpenAI`, `Anthropic`).
   - If the primary LLM encounters rate limits (429), authentication errors (401), or server errors (500), execution **automatically advances to the next available provider** in the fallback chain without breaking the user interaction.
   - If all external API keys fail or are omitted, the built-in **Local RAG Intelligence Engine** generates contextual responses.

2. **Dual-Layer Context Memory (`_DualLayerConversationMemory`)**:
   - **Tier 1 (Redis)**: Persists session memory under `chat:{session_id}:history`.
   - **Tier 2 (In-Memory Fallback)**: If Redis is offline, seamlessly stores multi-turn context in `_in_memory_chat_history[session_id]`.
   - Maintains full conversation continuity across all turns and providers.

3. **Active Provider Badging**:
   - Every AI response in the UI features an active provider badge (e.g. `⚡ Groq (LLaMA 3.1 8B)`, `⚡ Google Gemini 1.5 Flash`, `⚡ OpenRouter (Llama 3.1 Free)`).

---

## 🎨 3. 3D WebGL Telemetry & Signature Visualizers

Built with **Three.js** and custom WebGL shaders, the UI provides rich 3D interactions:

1. **`CareerPathHorizon3D` (Signature Career Visualizer)**:
   - Renders a glowing 3D indigo curved WebGL road stretching into the horizon with floating octahedron crystal milestones.
   - **Real-Time Data Driven**:
     - **Step 01 (Verified Skills)**: Renders candidate skill tags parsed directly from their resume.
     - **Step 02 (Skill Gap Analysis)**: Dynamically computes missing skill requirements compared to target market postings.
     - **Step 03 (Predicted Dream Role)**: Automatically highlights the #1 highest-matching job title, company, salary range, and similarity score.
2. **`SkillTagCloud3D`**:
   - Interactive 3D spherical particle cloud rendering candidate technical skills in motion.
3. **`HolographicGlobe3D`**:
   - Floating WebGL holographic globe symbolizing global market job data telemetry.
4. **`AI3DAvatarOrb`**:
   - Pulsing 3D sphere with dynamic vertex displacement reflecting AI thinking states.
5. **`Card3DTilt`**:
   - Physical 3D tilt mechanics adjusting perspective (`rotateX`/`rotateY`) based on cursor position.

---

## 💻 4. Core Web Application Pages

The frontend is built on **Next.js 14 (App Router)** with a custom CSS design system supporting HSL-tailored dark modes (`luminary`, `cyberpunk`, `aurora`, `gold`, `emerald`).

```
frontend/src/app/
├── page.tsx          # Dashboard: Hero 3D workspace, global metrics, top job market feed
├── job-board/        # 3D Job Board: 123k+ job explorer with ML Match mode & confetti alerts
├── analyzer/         # Resume Analyzer: Interactive 3-Step Pipeline
├── coach/            # 3D AI Career Coach: Multi-provider RAG chat with continuous memory
├── settings/         # API Key Credentials, Primary LLM Selector, Live Diagnostics
└── account/          # Candidate profile settings & system preferences
```

### Detailed Flow of Key Pages:
- **Resume Analyzer (`/analyzer`)**:
  - **Step 1 (Select PDF Resume)**: Drag-and-drop 3D platform with paper plane flying animations.
  - **Step 2 (Inspect Credentials)**: Comprehensive inspection displaying candidate name, email, experience years, education rating, and skill pills.
  - **Step 3 (3D Match Prediction)**: Runs vector search via Pinecone/MongoDB, displays top matched job cards, renders `CareerPathHorizon3D` with real data, and generates RAG AI career insights.
- **3D Job Board (`/job-board`)**:
  - Paginated, high-performance job browser handling 123,999 postings without system lag.
  - **AI ML Match Mode**: Executes neural matching (`/match/resume-to-jobs`) and triggers celebratory confetti when match scores exceed 85%.

---

## ⚙️ 5. Backend Optimization & Infrastructure Safety

To support over 123,000 database records and machine learning models without overloading host hardware:

1. **Query Pagination & Capping (`backend/routes/jobs.py`)**:
   - Added `.limit()` caps and `skip` pagination parameters to `list_jobs` and `search_jobs` endpoints to prevent dumping multi-megabyte payloads in a single request.
2. **Resource Environment Constraints (`run.bat`)**:
   - `NODE_OPTIONS=--max-old-space-size=2048` limits Node.js heap to 2GB max.
   - `OMP_NUM_THREADS=2`, `TORCH_NUM_THREADS=2`, `MKL_NUM_THREADS=2` constrain PyTorch CPU background threads to prevent 100% RAM / Disk thrashing.
3. **One-Click Process Control (`run.bat` & `stop.bat`)**:
   - `run.bat`: Launches FastAPI backend (Port 8000) and Next.js frontend (Port 3000) concurrently.
   - `stop.bat`: Instantly terminates background `node.exe` and `uvicorn` processes and frees ports 8000 & 3000.

---

## 🛠️ Summary of Technologies Used

- **Frontend**: Next.js 14, TypeScript, Three.js, React Three Fiber, Lucide Icons, Canvas 2D/3D, Vanilla CSS Design System.
- **Backend API**: FastAPI (Python 3.10+), Uvicorn, Pydantic v2, LangChain.
- **Databases & Vector Stores**: MongoDB (`pymongo`), Pinecone Vector Database (`pinecone-client`), Redis (`redis-py` / Mongo fallback).
- **Machine Learning & NLP**: PyTorch, SentenceTransformers (`all-MiniLM-L6-v2`), XGBoost, PyPDF2 / pdfplumber.
- **LLM Integrations**: Groq, Google Gemini, OpenRouter, OpenAI, Anthropic Claude.
