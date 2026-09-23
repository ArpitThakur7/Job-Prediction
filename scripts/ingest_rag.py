#!/usr/bin/env python3
"""
RAG Ingestion Script - JOB-AI Platform
Ingests career guidance, resume rules, and technical interview knowledge into RAG vector store.
"""

import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.rag_vector_store import upsert_rag_documents

SAMPLE_KNOWLEDGE_CHUNKS = [
    {
        "id": "rag_resume_ats_01",
        "text": "ATS Resume Optimization: Structure your resume with clear standard headings (Summary, Technical Skills, Professional Experience, Education). Use quantitative metrics for accomplishments (e.g., 'Reduced latency by 40%', 'Handled 5M daily requests'). Match key terms directly from the job description.",
        "metadata": {"category": "resume", "topic": "ATS Optimization", "author": "JOB-AI Career Coach"},
    },
    {
        "id": "rag_resume_skills_02",
        "text": "Technical Skill Categorization: Group your skills into logical buckets: Backend (FastAPI, Python, Node.js), Frontend (React, Next.js, Tailwind), Databases (MongoDB, PostgreSQL, Redis), and DevOps (Docker, Kubernetes, CI/CD).",
        "metadata": {"category": "resume", "topic": "Skill Formatting", "author": "JOB-AI Career Coach"},
    },
    {
        "id": "rag_interview_star_03",
        "text": "Behavioral Interviews STAR Method: Frame behavioral answers using Situation, Task, Action, Result. Focus 60% of your response on the specific Actions you took and the measurable Business Results achieved.",
        "metadata": {"category": "interview", "topic": "STAR Method", "author": "JOB-AI Career Coach"},
    },
    {
        "id": "rag_interview_sysdesign_04",
        "text": "System Design Interview Strategy: Start with requirement clarification (Functional & Non-Functional). Define scale numbers (QPS, storage size), propose high-level architecture (API Gateway, Microservices, DB, Caching), and dive deep into bottlenecks and caching strategies (Redis, CDN).",
        "metadata": {"category": "interview", "topic": "System Design", "author": "JOB-AI Career Coach"},
    },
    {
        "id": "rag_salary_negotiation_05",
        "text": "Salary Negotiation Principles: Never disclose your current salary or state a numeric expectation first. Ask recruiters for the target budget range for the position. Frame negotiations around market benchmarks and specialized skill alignment.",
        "metadata": {"category": "salary", "topic": "Negotiation", "author": "JOB-AI Career Coach"},
    },
    {
        "id": "rag_tech_fastapi_python_06",
        "text": "FastAPI & Python Best Practices: Use Pydantic models for request validation, async def handlers for I/O bound database calls, dependency injection for DB sessions, and structured logging. Use Uvicorn with worker processes for production deployment.",
        "metadata": {"category": "tech_stack", "topic": "FastAPI & Python", "author": "JOB-AI Tech Team"},
    },
    {
        "id": "rag_tech_react_next_07",
        "text": "React 19 & Next.js Best Practices: Use App Router with Server Components for static rendering and Client Components for interactive 3D WebGL canvases. Optimize bundle size and use Tailwind CSS for modular styling.",
        "metadata": {"category": "tech_stack", "topic": "React & Next.js", "author": "JOB-AI Tech Team"},
    },
]


def main():
    print("=" * 60)
    print(" Starting RAG Knowledge Ingestion...")
    print("=" * 60)

    count = upsert_rag_documents(SAMPLE_KNOWLEDGE_CHUNKS)
    print(f"\n Successfully ingested {count} knowledge chunks into RAG Vector Store!")
    print(" RAG Pipeline is ready for queries!\n")


if __name__ == "__main__":
    main()
