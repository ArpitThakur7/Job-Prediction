"""
JOB-AI-PLATFORM - Dataset Preprocessing Script
Run: python scripts/prepare_dataset.py
"""

import os
import re
import sys
import json
import uuid
import time
import random
import logging
import pandas as pd
import numpy as np
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

random.seed(42)
np.random.seed(42)

SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "SQL", "NoSQL", "MongoDB",
    "PostgreSQL", "MySQL", "Redis", "Excel", "PowerPoint", "Word",
    "Communication", "Leadership", "Management", "Sales", "Marketing",
    "Customer Service", "Data Analysis", "Machine Learning", "AI",
    "Deep Learning", "NLP", "Computer Vision", "Project Management",
    "Agile", "Scrum", "React", "Angular", "Vue", "Node.js", "Django",
    "Flask", "FastAPI", "Spring", "AWS", "Azure", "Google Cloud", "Docker",
    "Kubernetes", "Git", "REST API", "GraphQL", "Tableau", "Power BI",
    "R", "MATLAB", "C++", "C#", "PHP", "Ruby", "Swift", "Kotlin", "Go",
    "Rust", "Scala", "Spark", "Hadoop", "Accounting", "Finance", "HR",
    "Recruiting", "Healthcare", "Nursing", "Teaching", "Research",
    "Writing", "Editing", "Photoshop", "AutoCAD", "Engineering",
    "Civil", "Mechanical", "Electrical", "DevOps", "Linux", "Bash",
    "Terraform", "Blockchain", "Cybersecurity", "Networking", "Mobile",
    "Android", "iOS",
]

EDUCATION_MAP = {
    "phd": "PhD", "doctorate": "PhD",
    "master": "Masters", "mba": "Masters", "m.tech": "Masters",
    "m.s.": "Masters", "msc": "Masters",
    "bachelor": "Bachelors", "b.tech": "Bachelors", "b.s.": "Bachelors",
    "b.e.": "Bachelors", "bsc": "Bachelors", "b.com": "Bachelors",
    "associate": "Associate", "diploma": "Associate",
    "high school": "High School", "secondary": "High School",
}

EDUCATION_SCORE = {
    "PhD": 5, "Masters": 4, "Bachelors": 3,
    "Associate": 2, "High School": 1, "Not Specified": 0,
}


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^a-zA-Z0-9\s,.\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_skills(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text_lower = text.lower()
    found = [s for s in SKILLS if s.lower() in text_lower]
    return ", ".join(found)


def extract_email(text: str) -> str:
    if not isinstance(text, str):
        return ""
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    if not isinstance(text, str):
        return ""
    match = re.search(r"(\+?\d[\d\s\-\(\)]{7,}\d)", text)
    return match.group(0).strip() if match else ""


def extract_experience_years(text: str) -> int:
    if not isinstance(text, str):
        return 0
    matches = re.findall(r"(\d+)\+?\s*years?\s*(of)?\s*(experience)?", text, re.IGNORECASE)
    if not matches:
        return 0
    return max(int(m[0]) for m in matches)


def extract_education(text: str) -> str:
    if not isinstance(text, str):
        return "Not Specified"
    text_lower = text.lower()
    for keyword, level in EDUCATION_MAP.items():
        if keyword in text_lower:
            return level
    return "Not Specified"


def extract_name(text: str) -> str:
    if not isinstance(text, str):
        return "Candidate"
    first_line = text.strip().split("\n")[0][:50].strip()
    return first_line if first_line else "Candidate"


def safe_float(val) -> float:
    try:
        return float(str(val).replace(",", "").strip())
    except Exception:
        return 0.0


def clean_jobs() -> pd.DataFrame:
    log.info("STEP 2 - Loading jobs dataset...")

    jobs_dir = "data/raw/jobs"
    jobs_path = None
    for f in os.listdir(jobs_dir):
        if f.endswith(".csv"):
            jobs_path = os.path.join(jobs_dir, f)
            break

    if not jobs_path:
        raise FileNotFoundError("No CSV found in data/raw/jobs/")

    df = pd.read_csv(jobs_path, encoding="utf-8", encoding_errors="replace")
    log.info(f"  Loaded {len(df)} rows")

    rows = []
    for _, row in df.iterrows():
        title    = str(row.get("Job Title",       row.get("Title",            ""))).strip()
        desc     = clean_text(str(row.get("Job Description", row.get("FullDescription", ""))))[:1000]
        location = str(row.get("Location",        row.get("LocationNormalized","Remote"))).strip()
        city     = str(row.get("City",            location.split(",")[0].strip()))
        country  = str(row.get("Country",         row.get("Employer Country", "US"))).strip()
        company  = str(row.get("Company Name",    row.get("Company",          "Unknown"))).strip() or "Unknown"
        category = str(row.get("Categories",      row.get("Category",         "General"))).strip() or "General"
        industry = str(row.get("Industry",        "Other")).strip()
        job_type = str(row.get("Job Type",        row.get("ContractType",     "full_time"))).strip() or "full_time"
        sal_min  = safe_float(row.get("Salary From", row.get("SalaryNormalized", 0)))
        sal_max  = safe_float(row.get("Salary To",   sal_min))

        rows.append({
            "job_id":          str(uuid.uuid4()),
            "title":           title,
            "description":     desc,
            "location":        location,
            "city":            city,
            "country":         country,
            "job_type":        job_type,
            "company":         company,
            "category":        category,
            "industry":        industry,
            "salary_min":      sal_min,
            "salary_max":      sal_max,
            "salary_avg":      (sal_min + sal_max) / 2,
            "required_skills": extract_skills(desc),
        })

    result = pd.DataFrame(rows)
    result = result[result["title"].str.strip() != ""]
    result = result[result["description"].str.strip() != ""]
    result = result.reset_index(drop=True)

    os.makedirs("data/processed", exist_ok=True)
    result.to_csv("data/processed/jobs_clean.csv", index=False)
    print(f"[OK] Jobs processed: {len(result)} rows -> data/processed/jobs_clean.csv")
    return result


def clean_resumes() -> pd.DataFrame:
    log.info("STEP 3 - Loading resumes dataset...")

    df = pd.read_csv("data/raw/resumes/Resume.csv", encoding="utf-8", encoding_errors="replace")
    log.info(f"  Loaded {len(df)} rows")

    rows = []
    for _, row in df.iterrows():
        raw = clean_text(str(row.get("Resume_str", "")))
        if not raw.strip():
            continue
        rows.append({
            "resume_id":        str(row.get("ID", uuid.uuid4())),
            "name":             extract_name(raw),
            "email":            extract_email(raw),
            "phone":            extract_phone(raw),
            "raw_text":         raw,
            "category":         str(row.get("Category", "General")).strip(),
            "skills":           extract_skills(raw),
            "experience_years": extract_experience_years(raw),
            "education":        extract_education(raw),
        })

    result = pd.DataFrame(rows)
    result.to_csv("data/processed/resumes_clean.csv", index=False)
    print(f"[OK] Resumes processed: {len(result)} rows -> data/processed/resumes_clean.csv")
    return result


def build_feature_matrix(
    jobs_df: pd.DataFrame,
    resumes_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build feature matrix AND generate is_match labels from real features.
    Labels are NOT random — they are derived from actual skill/experience/education overlap.
    Top 25% scoring pairs = is_match=1, rest = is_match=0.
    """
    log.info("STEP 4 - Building feature matrix with real labels...")

    jobs_idx    = jobs_df.set_index("job_id")
    resumes_idx = resumes_df.set_index("resume_id")

    resume_ids = resumes_df["resume_id"].tolist()
    rows = []

    for _, job_row in jobs_df.iterrows():
        jid = job_row["job_id"]
        assigned = random.sample(resume_ids, min(4, len(resume_ids)))

        for rid in assigned:
            if jid not in jobs_idx.index or rid not in resumes_idx.index:
                continue

            job = jobs_idx.loc[jid]
            res = resumes_idx.loc[rid]

            # Skills
            j_skills = set(s.strip().lower() for s in str(job.get("required_skills", "")).split(",") if s.strip())
            r_skills = set(s.strip().lower() for s in str(res.get("skills", "")).split(",") if s.strip())
            overlap_count = len(j_skills & r_skills)
            overlap_ratio = overlap_count / max(len(j_skills), 1)

            # Experience
            job_exp = extract_experience_years(str(job.get("description", "")))
            res_exp = int(res.get("experience_years", 0))
            exp_gap = float(np.clip(res_exp - job_exp, -10, 10))

            # Education
            edu_score = EDUCATION_SCORE.get(str(res.get("education", "Not Specified")), 0)

            # Location
            res_loc = str(res.get("category", "")).lower()
            job_loc = str(job.get("location", "")).lower()
            location_match = 1 if "remote" in job_loc or res_loc in job_loc else 0

            # Category
            res_cat  = str(res.get("category", "")).lower()
            job_cat  = str(job.get("category", "")).lower()
            category_match = 1 if res_cat == job_cat else 0

            # Title relevance
            job_title_words = set(str(job.get("title", "")).lower().split())
            res_text = str(res.get("raw_text", "")).lower()
            title_relevance = 1 if any(w in res_text for w in job_title_words if len(w) > 3) else 0

            rows.append({
                "match_id":            str(uuid.uuid4()),
                "resume_id":           rid,
                "job_id":              jid,
                "skill_overlap_count": overlap_count,
                "skill_overlap_ratio": round(overlap_ratio, 4),
                "experience_gap":      exp_gap,
                "education_score":     edu_score,
                "location_match":      location_match,
                "category_match":      category_match,
                "title_relevance":     title_relevance,
                "description_length":  round(len(str(job.get("description", ""))) / 1000, 4),
                "skills_count_resume": len(r_skills),
                "skills_count_job":    len(j_skills),
            })

    features_df = pd.DataFrame(rows)

    # ================================================================
    # GENERATE LABELS FROM REAL FEATURES — NO RANDOM ASSIGNMENT
    # is_match = 1 if the pair scores in the top 25% by weighted score
    # This ensures labels reflect actual feature signal, not randomness
    # ================================================================
    skill_ratio   = features_df["skill_overlap_ratio"].fillna(0)
    exp_norm      = (features_df["experience_gap"].clip(0, 10) / 10.0)
    edu_norm      = ((features_df["education_score"] - 1) / 4.0).clip(0, 1)
    loc           = features_df["location_match"].fillna(0)
    skill_cnt_norm = (features_df["skill_overlap_count"] / 10.0).clip(0, 1)
    resume_norm   = (features_df["skills_count_resume"] / 20.0).clip(0, 1)

    match_score = (
        skill_ratio    * 0.40 +
        exp_norm       * 0.25 +
        edu_norm       * 0.15 +
        skill_cnt_norm * 0.10 +
        loc            * 0.05 +
        resume_norm    * 0.05
    ).round(4)

    # Add small noise so the boundary is not perfectly sharp
    noise = np.random.normal(0, 0.02, size=len(match_score))
    match_score_noisy = (match_score + noise).clip(0, 1)

    threshold = match_score_noisy.quantile(0.75)
    features_df["is_match"]    = (match_score_noisy >= threshold).astype(int)
    features_df["match_score"] = match_score_noisy.round(4)

    features_df.to_csv("data/processed/features.csv", index=False)
    print(f"[OK] Feature matrix: {len(features_df)} rows, {len(features_df.columns)} cols -> data/processed/features.csv")

    # Save match_labels.csv from features
    labels_df = features_df[["match_id", "resume_id", "job_id", "is_match", "match_score"]].copy()
    labels_df.to_csv("data/processed/match_labels.csv", index=False)
    print(f"[OK] Match labels: {len(labels_df)} rows -> data/processed/match_labels.csv")

    return features_df, labels_df


def generate_sample_data(jobs_df, resumes_df, features_df) -> None:
    log.info("STEP 5 - Generating sample data...")
    os.makedirs("data/sample", exist_ok=True)
    jobs_df.head(50).to_csv("data/sample/sample_jobs.csv", index=False)
    resumes_df.head(20).to_csv("data/sample/sample_resumes.csv", index=False)
    features_df.head(100).to_csv("data/sample/sample_features.csv", index=False)
    print("[OK] Sample data saved -> data/sample/")


def generate_summary_report(jobs_df, resumes_df, labels_df, features_df) -> None:
    log.info("STEP 6 - Generating summary report...")

    def top_counts(series, n=10):
        return {str(k): int(v) for k, v in series.value_counts().head(n).items()}

    def top_skills(df, col, n=20):
        all_skills = []
        for s in df[col].dropna():
            all_skills.extend([x.strip() for x in str(s).split(",") if x.strip()])
        return {str(k): int(v) for k, v in pd.Series(all_skills).value_counts().head(n).items()}

    summary = {
        "generated_at": datetime.now().isoformat(),
        "jobs": {
            "total_rows":     len(jobs_df),
            "columns":        jobs_df.columns.tolist(),
            "top_categories": top_counts(jobs_df["category"]),
            "top_locations":  top_counts(jobs_df["location"]),
            "avg_salary":     round(float(jobs_df["salary_avg"].mean()), 2),
            "top_skills":     top_skills(jobs_df, "required_skills"),
        },
        "resumes": {
            "total_rows":             len(resumes_df),
            "columns":                resumes_df.columns.tolist(),
            "top_categories":         top_counts(resumes_df["category"]),
            "education_distribution": top_counts(resumes_df["education"]),
            "avg_experience_years":   round(float(resumes_df["experience_years"].mean()), 2),
            "top_skills":             top_skills(resumes_df, "skills"),
        },
        "labels": {
            "total_rows":       len(labels_df),
            "positive_matches": int(labels_df["is_match"].sum()),
            "negative_matches": int((labels_df["is_match"] == 0).sum()),
            "match_ratio":      round(float(labels_df["is_match"].mean()), 4),
        },
        "features": {
            "total_rows":        len(features_df),
            "feature_columns":   features_df.columns.tolist(),
            "avg_skill_overlap": round(float(features_df["skill_overlap_ratio"].mean()), 4),
            "avg_match_score":   round(float(features_df["match_score"].mean()), 4),
        },
    }

    with open("data/processed/dataset_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("[OK] Summary report saved -> data/processed/dataset_summary.json")


def main():
    print("\n" + "=" * 60)
    print("  JOB-AI-PLATFORM - Dataset Preprocessing")
    print("=" * 60 + "\n")

    start = time.time()

    try:
        jobs_df             = clean_jobs()
        resumes_df          = clean_resumes()
        features_df, labels_df = build_feature_matrix(jobs_df, resumes_df)
        generate_sample_data(jobs_df, resumes_df, features_df)
        generate_summary_report(jobs_df, resumes_df, labels_df, features_df)

        elapsed = round(time.time() - start, 2)
        print("\n" + "=" * 60)
        print(f"  ALL DONE in {elapsed} seconds")
        print("=" * 60)
        print("\nFiles created:")
        print("  data/processed/jobs_clean.csv")
        print("  data/processed/resumes_clean.csv")
        print("  data/processed/match_labels.csv")
        print("  data/processed/features.csv")
        print("  data/processed/dataset_summary.json")
        print("  data/sample/sample_jobs.csv")
        print("  data/sample/sample_resumes.csv")
        print("  data/sample/sample_features.csv\n")

    except Exception as e:
        log.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()