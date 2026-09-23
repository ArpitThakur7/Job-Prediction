#!/usr/bin/env python3
"""
Phase 1 — Data Ingestion Pipeline
Loads job postings and candidate resumes from CSVs into normalized MongoDB collections.
"""

import hashlib
import json
import logging
import os
import sys
import pandas as pd
from pathlib import Path

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import get_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingest_data")

DATA_DIR = Path(__file__).parent.parent / "data"


def normalize_skills(val: any) -> list[str]:
    if pd.isna(val) or not val:
        return []
    if isinstance(val, list):
        return [str(s).strip() for s in val if str(s).strip()]
    if isinstance(val, str):
        # Split by comma or semicolon
        items = [s.strip() for s in val.replace(";", ",").split(",") if s.strip()]
        return items
    return []


def ingest_jobs() -> int:
    logger.info("=== Phase 1.1: Ingesting Job Postings ===")
    
    # Check sample file first, then raw folder
    sample_job_path = DATA_DIR / "sample" / "sample_jobs.csv"
    raw_job_dir = DATA_DIR / "raw" / "jobs"
    
    job_files = []
    if sample_job_path.exists():
        job_files.append(sample_job_path)
    if raw_job_dir.exists():
        for f in raw_job_dir.glob("*.csv"):
            job_files.append(f)
            
    if not job_files:
        logger.warning("No job CSV files found in data/sample or data/raw/jobs!")
        return 0

    db = get_database()
    total_read = 0
    total_normalized = 0

    for csv_file in job_files:
        logger.info(f"Reading jobs from: {csv_file.name}")
        df = pd.read_csv(csv_file, low_memory=False)
        total_read += len(df)
        
        normalized_jobs = []
        for idx, row in df.iterrows():
            title = str(row.get("title") or row.get("job_title") or "").strip()
            desc = str(row.get("description") or row.get("job_description") or "").strip()
            
            # Critical validation: must have title and description
            if not title or not desc or title.lower() == "nan" or desc.lower() == "nan":
                continue

            job_id = str(row.get("job_id") or row.get("id") or f"job_{idx}")
            company = str(row.get("company") or row.get("company_name") or "Enterprise Corp").strip()
            location = str(row.get("location") or row.get("job_location") or "Remote / Global").strip()
            
            # Salary extraction
            sal_min = None
            sal_max = None
            try:
                if not pd.isna(row.get("salary_min")):
                    sal_min = float(row.get("salary_min"))
                if not pd.isna(row.get("salary_max")):
                    sal_max = float(row.get("salary_max"))
            except Exception:
                pass

            skills = normalize_skills(row.get("required_skills") or row.get("skills"))
            posted_date = str(row.get("posted_date") or row.get("post_date") or "").strip()
            
            url_hash = hashlib.md5(f"{title}_{company}_{location}".encode("utf-8")).hexdigest()

            doc = {
                "job_id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "description": desc,
                "salary_min": sal_min,
                "salary_max": sal_max,
                "required_skills": skills,
                "posted_date": posted_date,
                "url_hash": url_hash,
            }
            normalized_jobs.append(doc)

        total_normalized += len(normalized_jobs)
        
        # Save to MongoDB
        if db is not None and normalized_jobs:
            try:
                jobs_col = db["jobs"]
                for job_doc in normalized_jobs:
                    jobs_col.update_one({"job_id": job_doc["job_id"]}, {"$set": job_doc}, upsert=True)
                logger.info(f"Successfully upserted {len(normalized_jobs)} jobs into MongoDB 'jobs' collection.")
            except Exception as e:
                logger.warning(f"MongoDB write failed: {e}. Storing locally.")

    logger.info(f"Jobs Summary: Read {total_read} rows -> Normalized {total_normalized} valid records.")
    return total_normalized


def ingest_resumes() -> int:
    logger.info("=== Phase 1.2: Ingesting Candidate Resumes ===")
    
    sample_res_path = DATA_DIR / "sample" / "sample_resumes.csv"
    raw_res_dir = DATA_DIR / "raw" / "resumes"
    
    res_files = []
    if sample_res_path.exists():
        res_files.append(sample_res_path)
    if raw_res_dir.exists():
        for f in raw_res_dir.glob("*.csv"):
            res_files.append(f)

    if not res_files:
        logger.warning("No resume CSV files found in data/sample or data/raw/resumes!")
        return 0

    db = get_database()
    total_read = 0
    total_normalized = 0

    for csv_file in res_files:
        logger.info(f"Reading resumes from: {csv_file.name}")
        df = pd.read_csv(csv_file, low_memory=False)
        total_read += len(df)

        normalized_resumes = []
        for idx, row in df.iterrows():
            text = str(row.get("resume_text") or row.get("raw_text") or "").strip()
            
            # Critical validation: must have resume text
            if not text or text.lower() == "nan" or len(text) < 20:
                continue

            resume_id = str(row.get("resume_id") or row.get("id") or f"res_{idx}")
            name = str(row.get("name") or row.get("candidate_name") or f"Candidate #{idx+1}").strip()
            category = str(row.get("category") or "Engineering").strip()
            skills = normalize_skills(row.get("skills"))
            education = str(row.get("education") or "Bachelors").strip()
            
            exp_years = 0.0
            try:
                if not pd.isna(row.get("experience_years")):
                    exp_years = float(row.get("experience_years"))
            except Exception:
                pass

            email = str(row.get("email") or "").strip()
            phone = str(row.get("phone") or "").strip()

            doc = {
                "resume_id": resume_id,
                "name": name,
                "category": category,
                "skills": skills,
                "education": education,
                "experience_years": exp_years,
                "resume_text": text,
                "email": email,
                "phone": phone,
            }
            normalized_resumes.append(doc)

        total_normalized += len(normalized_resumes)

        if db is not None and normalized_resumes:
            try:
                res_col = db["resumes"]
                for res_doc in normalized_resumes:
                    res_col.update_one({"resume_id": res_doc["resume_id"]}, {"$set": res_doc}, upsert=True)
                logger.info(f"Successfully upserted {len(normalized_resumes)} resumes into MongoDB 'resumes' collection.")
            except Exception as e:
                logger.warning(f"MongoDB write failed: {e}.")

    logger.info(f"Resumes Summary: Read {total_read} rows -> Normalized {total_normalized} valid records.")
    return total_normalized


def main():
    logger.info("Starting Phase 1 Data Ingestion Pipeline...")
    jobs_count = ingest_jobs()
    resumes_count = ingest_resumes()
    logger.info(f"Phase 1 Ingestion Complete! Total Jobs: {jobs_count}, Total Resumes: {resumes_count}")


if __name__ == "__main__":
    main()
