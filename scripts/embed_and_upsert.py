#!/usr/bin/env python3
"""
Phase 1 — Vector Embedding & Dual-Namespace Pinecone Upsert
Embeds job postings and candidate resumes into Pinecone under 'jobs' and 'resumes' namespaces.
Caches embeddings by content hash in MongoDB 'embedding_cache' collection.
"""

import hashlib
import logging
import os
import sys
import pandas as pd
from pathlib import Path

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config import settings
from backend.database import get_database
from backend.services.embedder import generate_batch_embeddings, generate_embedding
from backend.services.rag_vector_store import upsert_rag_documents

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("embed_and_upsert")

DATA_DIR = Path(__file__).parent.parent / "data"


def get_content_hash(text: str) -> str:
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()


def build_job_embedding_text(job: dict) -> str:
    if job.get("job_text"):
        return job["job_text"]
    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    work_type = job.get("work_type", "Full-time")
    salary = job.get("salary", "Not Specified")
    skills = job.get("required_skills") or []
    skills_str = ", ".join(skills[:10]) if isinstance(skills, list) else str(skills)
    benefits = job.get("benefits") or []
    benefits_str = ", ".join(benefits[:5]) if isinstance(benefits, list) else str(benefits)
    industries = job.get("industries") or []
    ind_str = ", ".join(industries[:3]) if isinstance(industries, list) else str(industries)
    desc = str(job.get("description") or "")[:400].replace("\n", " ")
    return f"Job Title: {title} | Company: {company} | Location: {location} | Work Type: {work_type} | Salary: {salary} | Industry: {ind_str} | Required Skills: {skills_str} | Benefits: {benefits_str} | Description: {desc}"


def build_resume_embedding_text(res: dict) -> str:
    if res.get("resume_text"):
        return res["resume_text"]
    name = res.get("name", "Candidate")
    category = res.get("category", "")
    skills = res.get("skills") or []
    skills_str = ", ".join(skills[:15]) if isinstance(skills, list) else str(skills)
    abilities = res.get("abilities") or []
    abilities_str = ", ".join(abilities[:10]) if isinstance(abilities, list) else str(abilities)
    edu = res.get("education", "")
    if isinstance(edu, list):
        edu = "; ".join([f"{e.get('program', '')} at {e.get('institution', '')}" for e in edu[:3] if isinstance(e, dict)])
    exp = res.get("experience", "")
    if isinstance(exp, list):
        exp = "; ".join([f"{x.get('title', '')} at {x.get('firm', '')}" for x in exp[:4] if isinstance(x, dict)])
    return f"Candidate Name: {name} | Primary Role: {category} | Experience Timeline: {exp} | Education: {edu} | Abilities: {abilities_str} | Skills: {skills_str}"



def get_cached_embeddings(db, texts: list[str]) -> tuple[dict[str, list[float]], list[str]]:
    cached = {}
    missing = []
    if db is None:
        return cached, texts

    try:
        cache_col = db["embedding_cache"]
        hashes = [get_content_hash(t) for t in texts]
        cursor = cache_col.find({"hash": {"$in": hashes}})
        for doc in cursor:
            cached[doc["hash"]] = doc["vector"]
    except Exception as e:
        logger.warning(f"Failed to query embedding_cache: {e}")

    for t in texts:
        h = get_content_hash(t)
        if h not in cached:
            missing.append(t)

    return cached, missing


def save_embeddings_to_cache(db, text_vector_pairs: list[tuple[str, list[float]]]):
    if db is None or not text_vector_pairs:
        return
    try:
        cache_col = db["embedding_cache"]
        docs = [
            {"hash": get_content_hash(text), "vector": vec, "text": text[:200]}
            for text, vec in text_vector_pairs
        ]
        for doc in docs:
            cache_col.update_one({"hash": doc["hash"]}, {"$set": doc}, upsert=True)
    except Exception as e:
        logger.warning(f"Failed to save embeddings to cache: {e}")


def process_jobs_namespace(db):
    logger.info("=== Phase 1.3: Embedding & Upserting Jobs (Namespace: 'jobs') ===")
    
    jobs = []
    if db is not None:
        try:
            jobs = list(db["jobs"].find({}))
        except Exception:
            pass

    # Fallback to reading sample file if MongoDB is empty
    if not jobs:
        sample_path = DATA_DIR / "sample" / "sample_jobs.csv"
        if sample_path.exists():
            df = pd.read_csv(sample_path)
            for idx, r in df.iterrows():
                if pd.notna(r.get("title")) and pd.notna(r.get("description")):
                    jobs.append({
                        "job_id": str(r.get("job_id") or f"job_{idx}"),
                        "title": str(r.get("title")),
                        "company": str(r.get("company") or "Corp"),
                        "location": str(r.get("location") or "Remote"),
                        "description": str(r.get("description")),
                        "required_skills": str(r.get("required_skills") or "").split(","),
                    })

    if not jobs:
        logger.warning("No job records available for embedding!")
        return 0

    texts = [build_job_embedding_text(j) for j in jobs]
    cached_map, missing_texts = get_cached_embeddings(db, texts)
    
    logger.info(f"Jobs Cache Stats: Total={len(texts)}, Cached={len(cached_map)}, Need Embedding={len(missing_texts)}")
    
    if missing_texts:
        new_vectors = generate_batch_embeddings(missing_texts)
        pairs = list(zip(missing_texts, new_vectors))
        save_embeddings_to_cache(db, pairs)
        for t, v in pairs:
            cached_map[get_content_hash(t)] = v

    # Prepare vector records for Pinecone & Local Vector Store
    rag_docs = []
    for j, t in zip(jobs, texts):
        h = get_content_hash(t)
        vec = cached_map.get(h)
        if vec:
            rag_docs.append({
                "id": str(j.get("job_id")),
                "text": t,
                "metadata": {
                    "namespace": "jobs",
                    "title": j.get("title", ""),
                    "company": j.get("company", ""),
                    "location": j.get("location", ""),
                    "type": "job",
                }
            })

    # Upsert vectors
    upserted = upsert_rag_documents(rag_docs)
    logger.info(f"Jobs Vector Pipeline Complete: Read={len(jobs)} -> Embedded={len(texts)} -> Upserted={upserted} to 'jobs' namespace.")
    return upserted


def process_resumes_namespace(db):
    logger.info("=== Phase 1.4: Embedding & Upserting Resumes (Namespace: 'resumes') ===")
    
    resumes = []
    if db is not None:
        try:
            resumes = list(db["resumes"].find({}))
        except Exception:
            pass

    if not resumes:
        sample_path = DATA_DIR / "sample" / "sample_resumes.csv"
        if sample_path.exists():
            df = pd.read_csv(sample_path)
            for idx, r in df.iterrows():
                if pd.notna(r.get("raw_text")) or pd.notna(r.get("resume_text")):
                    resumes.append({
                        "resume_id": str(r.get("resume_id") or f"res_{idx}"),
                        "name": str(r.get("name") or f"Candidate #{idx}"),
                        "category": str(r.get("category") or "Engineering"),
                        "skills": str(r.get("skills") or "").split(","),
                        "education": str(r.get("education") or "Bachelors"),
                        "experience_years": r.get("experience_years", 0),
                        "resume_text": str(r.get("resume_text") or r.get("raw_text")),
                    })

    if not resumes:
        logger.warning("No resume records available for embedding!")
        return 0

    texts = [build_resume_embedding_text(r) for r in resumes]
    cached_map, missing_texts = get_cached_embeddings(db, texts)

    logger.info(f"Resumes Cache Stats: Total={len(texts)}, Cached={len(cached_map)}, Need Embedding={len(missing_texts)}")

    if missing_texts:
        new_vectors = generate_batch_embeddings(missing_texts)
        pairs = list(zip(missing_texts, new_vectors))
        save_embeddings_to_cache(db, pairs)
        for t, v in pairs:
            cached_map[get_content_hash(t)] = v

    rag_docs = []
    for r, t in zip(resumes, texts):
        h = get_content_hash(t)
        vec = cached_map.get(h)
        if vec:
            rag_docs.append({
                "id": str(r.get("resume_id")),
                "text": t,
                "metadata": {
                    "namespace": "resumes",
                    "name": r.get("name", ""),
                    "category": r.get("category", ""),
                    "type": "resume",
                }
            })

    upserted = upsert_rag_documents(rag_docs)
    logger.info(f"Resumes Vector Pipeline Complete: Read={len(resumes)} -> Embedded={len(texts)} -> Upserted={upserted} to 'resumes' namespace.")
    return upserted


def main():
    logger.info("Starting Phase 1 Vector Embedding & Dual-Namespace Upsert Pipeline...")
    db = get_database()
    jobs_upserted = process_jobs_namespace(db)
    resumes_upserted = process_resumes_namespace(db)
    logger.info(f"Phase 1 Vector Upsert Complete! Jobs Vectors: {jobs_upserted}, Resumes Vectors: {resumes_upserted}")


if __name__ == "__main__":
    main()
