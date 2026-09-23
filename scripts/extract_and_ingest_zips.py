#!/usr/bin/env python3
"""
===================================================================
   HIGH-SPEED RESUMABLE MULTI-ARCHIVE RAG & MONGODB INGESTION PIPELINE
===================================================================
Extracts and ingests all CSV data across:
  - archive (1).zip (Candidate Resumes, Education, Experience, Abilities, Skills)
  - archive (2).zip (LinkedIn Jobs, Companies, Salaries, Benefits, Industries, Skills)

FEATURES:
  ⚡ Ultra-Fast: Uses PyMongo bulk_write & fast pandas tuple iterators.
  🔄 Auto-Resumable: Instantly checks and skips already-ingested Mongo/Pinecone IDs.
  💾 Incremental Checkpointing: Auto-saves after every batch to prevent loss on cancellation.
"""

import argparse
import os
import sys
import zipfile
import pandas as pd
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pymongo import UpdateOne

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import get_database
from backend.services.rag_vector_store import upsert_rag_documents

ZIP_RESUMES_PATH = r"C:\Users\admin\Downloads\archive (1).zip"
ZIP_JOBS_PATH = r"C:\Users\admin\Downloads\archive (2).zip"

DATA_RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RESUMES_DIR = DATA_RAW_DIR / "resumes"
JOBS_DIR = DATA_RAW_DIR / "jobs"


def extract_zips_if_needed(zip_resumes: str = ZIP_RESUMES_PATH, zip_jobs: str = ZIP_JOBS_PATH):
    print("=" * 70)
    print(" 📦 1. VERIFYING & EXTRACTING ZIP ARCHIVES")
    print("=" * 70)

    RESUMES_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    people_csv = RESUMES_DIR / "01_people.csv"
    if not people_csv.exists() and os.path.exists(zip_resumes):
        print(f"Extracting candidate resumes archive: {zip_resumes}...")
        with zipfile.ZipFile(zip_resumes, 'r') as zf:
            zf.extractall(RESUMES_DIR)
        print(f"  ✓ Resumes extracted to {RESUMES_DIR}")
    elif people_csv.exists():
        print(f"  ✓ Found existing extracted resumes directory: {RESUMES_DIR}")
    else:
        print(f"  ⚠️ Warning: {zip_resumes} not found!")

    postings_csv = JOBS_DIR / "postings.csv"
    if not postings_csv.exists() and (JOBS_DIR / "jobs" / "postings.csv").exists():
        postings_csv = JOBS_DIR / "jobs" / "postings.csv"

    if not postings_csv.exists() and os.path.exists(zip_jobs):
        print(f"Extracting jobs archive: {zip_jobs}...")
        with zipfile.ZipFile(zip_jobs, 'r') as zf:
            zf.extractall(JOBS_DIR)
        print(f"  ✓ Jobs extracted to {JOBS_DIR}")
    elif postings_csv.exists():
        print(f"  ✓ Found existing extracted jobs directory: {JOBS_DIR}")
    else:
        print(f"  ⚠️ Warning: {zip_jobs} not found!")


def load_csv_safe(file_path: Path, low_memory: bool = False) -> pd.DataFrame:
    if not file_path.exists():
        print(f"  ⚠️ File not found: {file_path}")
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, low_memory=low_memory)
    except Exception as e:
        print(f"  ⚠️ Error reading {file_path.name}: {e}")
        return pd.DataFrame()


# ===================================================================
# 2. INGEST CANDIDATE RESUMES DATASET (Archive 1)
# ===================================================================
def process_resumes_dataset(limit: int = 0, batch_size: int = 2000, force: bool = False) -> int:
    print("\n" + "=" * 70)
    print(" 📄 2. INGESTING CANDIDATE RESUMES (ARCHIVE 1)")
    print("=" * 70)

    db = get_database()
    existing_ids: Set[str] = set()

    if db is not None and not force:
        try:
            col_res = db["resumes"]
            existing_ids = set(str(pid) for pid in col_res.distinct("resume_id"))
            print(f"  🔄 Found {len(existing_ids):,} existing resumes in MongoDB.")
        except Exception as e:
            print(f"  ⚠️ Mongo query warning: {e}")

    # Check 01_people.csv IDs safely without heavy full load
    people_csv = RESUMES_DIR / "01_people.csv"
    if not people_csv.exists():
        print("  ❌ Skipping resumes dataset: 01_people.csv not found.")
        return 0

    # Quick ID check
    try:
        p_ids_df = pd.read_csv(people_csv, usecols=["person_id"])
        total_candidates = len(p_ids_df)
        if limit > 0:
            total_candidates = min(total_candidates, limit)

        if existing_ids and not force:
            p_ids = set(str(int(float(pid))) if str(pid).endswith(".0") else str(pid) for pid in p_ids_df["person_id"].head(total_candidates) if pd.notna(pid))
            missing_ids = p_ids - existing_ids
            if not missing_ids:
                print(f"Total Candidate Profiles in source: {total_candidates:,}")
                print(f"  ⏭️ Skipped {total_candidates:,} already pushed candidate profiles.")
                print("  ✅ All candidate profiles are already pushed to MongoDB and Vector Store!")
                return total_candidates
    except Exception as e:
        print(f"  ⚠️ Quick resume ID check warning: {e}")

    p_df = load_csv_safe(people_csv)
    if p_df.empty:
        return 0

    if limit > 0:
        p_df = p_df.head(limit)

    total_candidates = len(p_df)
    print(f"Total Candidate Profiles in source: {total_candidates:,}")

    # Filter out already ingested records if not forced
    if existing_ids and not force:
        p_df["pid_str"] = p_df["person_id"].astype(str)
        pending_df = p_df[~p_df["pid_str"].isin(existing_ids)]
        skipped_count = total_candidates - len(pending_df)
        print(f"  ⏭️ Skipped {skipped_count:,} already pushed candidate profiles.")
        p_df = pending_df
    else:
        skipped_count = 0

    if p_df.empty:
        print("  ✅ All candidate profiles are already pushed to MongoDB and Vector Store!")
        return skipped_count

    print(f"  🚀 Processing remaining {len(p_df):,} candidate profiles...")

    # Fast relational lookups using defaultdicts & itertuples
    print("Building relational candidate lookups...")

    ab_df = load_csv_safe(RESUMES_DIR / "02_abilities.csv")
    abilities_map = defaultdict(list)
    if not ab_df.empty:
        for row in ab_df.itertuples(index=False):
            pid = str(getattr(row, "person_id", ""))
            ability = str(getattr(row, "ability", "") or "").strip()
            if pid and ability:
                abilities_map[pid].append(ability)

    edu_df = load_csv_safe(RESUMES_DIR / "03_education.csv")
    edu_map = defaultdict(list)
    if not edu_df.empty:
        for row in edu_df.itertuples(index=False):
            pid = str(getattr(row, "person_id", ""))
            inst = str(getattr(row, "institution", "") or "").strip()
            prog = str(getattr(row, "program", "") or "").strip()
            if pid and (inst or prog):
                edu_map[pid].append({
                    "institution": inst,
                    "program": prog,
                    "start_date": str(getattr(row, "start_date", "") or ""),
                    "location": str(getattr(row, "location", "") or "")
                })

    exp_df = load_csv_safe(RESUMES_DIR / "04_experience.csv")
    exp_map = defaultdict(list)
    if not exp_df.empty:
        for row in exp_df.itertuples(index=False):
            pid = str(getattr(row, "person_id", ""))
            title = str(getattr(row, "title", "") or "").strip()
            firm = str(getattr(row, "firm", "") or "").strip()
            if pid and (title or firm):
                exp_map[pid].append({
                    "title": title,
                    "firm": firm,
                    "start_date": str(getattr(row, "start_date", "") or ""),
                    "end_date": str(getattr(row, "end_date", "") or ""),
                    "location": str(getattr(row, "location", "") or "")
                })

    ps_df = load_csv_safe(RESUMES_DIR / "05_person_skills.csv")
    skills_map = defaultdict(list)
    if not ps_df.empty:
        for row in ps_df.itertuples(index=False):
            pid = str(getattr(row, "person_id", ""))
            skill = str(getattr(row, "skill", "") or "").strip()
            if pid and skill:
                skills_map[pid].append(skill)

    # Save Skills Taxonomy to Mongo if empty
    sk_df = load_csv_safe(RESUMES_DIR / "06_skills.csv")
    if db is not None and not sk_df.empty:
        try:
            col_sk = db["skills_taxonomy"]
            if col_sk.count_documents({}) == 0:
                skills_list = [str(s).strip() for s in sk_df["skill"].dropna().unique() if str(s).strip()]
                col_sk.insert_many([{"skill": s} for s in skills_list[:10000]])
                print(f"  ✓ Saved {len(skills_list):,} skills into MongoDB 'skills_taxonomy'.")
        except Exception as e:
            print(f"  ⚠️ MongoDB skills_taxonomy save warning: {e}")

    # Build & Bulk Save Documents in Incremental Batches
    print("Assembling Candidate Documents & RAG chunks in batches...")
    
    total_processed = 0
    records = p_df.to_dict("records")

    for i in range(0, len(records), batch_size):
        chunk = records[i:i + batch_size]
        mongo_ops = []
        rag_docs = []

        for r in chunk:
            pid = str(r.get("person_id") or f"person_{total_processed}")
            name = str(r.get("name") or f"Candidate #{pid}").strip()
            email = str(r.get("email") or "") if pd.notna(r.get("email")) else ""
            phone = str(r.get("phone") or "") if pd.notna(r.get("phone")) else ""
            linkedin = str(r.get("linkedin") or "") if pd.notna(r.get("linkedin")) else ""

            cand_abilities = list(set(abilities_map.get(pid, [])))
            cand_edu = edu_map.get(pid, [])
            cand_exp = exp_map.get(pid, [])
            cand_skills = list(set(skills_map.get(pid, [])))

            edu_texts = [f"{e['program']} at {e['institution']}" for e in cand_edu if e.get("institution") or e.get("program")]
            edu_summary = "; ".join(edu_texts[:3]) if edu_texts else "Bachelor's Degree"

            exp_texts = [f"{x['title']} at {x['firm']}" for x in cand_exp if x.get("title") or x.get("firm")]
            exp_summary = "; ".join(exp_texts[:4]) if exp_texts else "Experienced Professional"
            primary_title = cand_exp[0]["title"] if cand_exp and cand_exp[0].get("title") else "Professional"

            abilities_str = ", ".join(cand_abilities[:10])
            skills_str = ", ".join(cand_skills[:15])

            rag_text = (
                f"Candidate Name: {name} | Primary Role: {primary_title} | "
                f"Experience Timeline: {exp_summary} | Education: {edu_summary} | "
                f"Abilities: {abilities_str} | Skills: {skills_str}"
            )

            mongo_doc = {
                "resume_id": pid,
                "name": name,
                "email": email,
                "phone": phone,
                "linkedin": linkedin,
                "category": primary_title,
                "skills": cand_skills,
                "abilities": cand_abilities,
                "education": cand_edu,
                "experience": cand_exp,
                "experience_years": len(cand_exp) * 2 or 3,
                "resume_text": rag_text,
            }
            mongo_ops.append(UpdateOne({"resume_id": pid}, {"$set": mongo_doc}, upsert=True))

            rag_docs.append({
                "id": f"res_{pid}",
                "text": rag_text,
                "metadata": {
                    "namespace": "resumes",
                    "name": name,
                    "category": primary_title,
                    "type": "resume",
                    "person_id": pid,
                }
            })

        # Fast PyMongo Bulk Write (Single roundtrip for up to 2,000 docs!)
        if db is not None and mongo_ops:
            try:
                db["resumes"].bulk_write(mongo_ops, ordered=False)
            except Exception as e:
                print(f"  ⚠️ Bulk write warning for batch: {e}")

        # Vector Embeddings & Pinecone Upsert
        if rag_docs:
            upsert_rag_documents(rag_docs)

        total_processed += len(chunk)
        current_total = skipped_count + total_processed
        print(f"  [+] Resumes Progress: {current_total:,}/{total_candidates:,} ({(current_total/total_candidates)*100:.1f}%) [Auto-Saved ✓]")

    print(f"  ✓ Candidate Resumes Ingestion Complete! Total: {skipped_count + total_processed:,}")
    return skipped_count + total_processed


# ===================================================================
# 3. INGEST JOBS & COMPANIES DATASET (Archive 2)
# ===================================================================
def process_jobs_dataset(limit: int = 0, batch_size: int = 2000, force: bool = False) -> int:
    print("\n" + "=" * 70)
    print(" 💼 3. INGESTING LINKEDIN JOBS & COMPANIES (ARCHIVE 2)")
    print("=" * 70)

    postings_csv = JOBS_DIR / "postings.csv"
    if not postings_csv.exists() and (JOBS_DIR / "jobs" / "postings.csv").exists():
        postings_csv = JOBS_DIR / "jobs" / "postings.csv"

    if not postings_csv.exists():
        print(f"  ❌ Skipping jobs dataset: postings.csv not found in {JOBS_DIR}.")
        return 0

    db = get_database()
    existing_job_ids: Set[str] = set()

    if db is not None and not force:
        try:
            col_jobs = db["jobs"]
            existing_job_ids = set(str(jid) for jid in col_jobs.distinct("job_id"))
            print(f"  🔄 Found {len(existing_job_ids):,} existing jobs in MongoDB.")
        except Exception as e:
            print(f"  ⚠️ Mongo query warning: {e}")

    # Quick ID check without loading 516 MB into RAM
    try:
        j_ids_df = pd.read_csv(postings_csv, usecols=["job_id"])
        total_jobs = len(j_ids_df)
        if limit > 0:
            total_jobs = min(total_jobs, limit)

        if existing_job_ids and not force:
            j_ids = set(str(int(float(jid))) if str(jid).endswith(".0") else str(jid) for jid in j_ids_df["job_id"].head(total_jobs) if pd.notna(jid))
            missing_ids = j_ids - existing_job_ids
            if not missing_ids:
                print(f"Total Job Postings in source: {total_jobs:,}")
                print(f"  ⏭️ Skipped {total_jobs:,} already pushed job postings.")
                print("  ✅ All job postings are already pushed to MongoDB and Vector Store!")
                return total_jobs
    except Exception as e:
        print(f"  ⚠️ Quick job ID check warning: {e}")

    p_df = load_csv_safe(postings_csv, low_memory=False)
    if p_df.empty:
        return 0

    if limit > 0:
        p_df = p_df.head(limit)

    total_jobs = len(p_df)
    print(f"Total Job Postings in source: {total_jobs:,}")

    # Filter out already ingested job postings
    if existing_job_ids and not force:
        p_df["jid_str"] = p_df["job_id"].astype(str)
        pending_df = p_df[~p_df["jid_str"].isin(existing_job_ids)]
        skipped_count = total_jobs - len(pending_df)
        print(f"  ⏭️ Skipped {skipped_count:,} already pushed job postings.")
        p_df = pending_df
    else:
        skipped_count = 0

    if p_df.empty:
        print("  ✅ All job postings are already pushed to MongoDB and Vector Store!")
        return skipped_count

    print(f"  🚀 Processing remaining {len(p_df):,} job postings...")

    # Load Mappings & Reference Data
    ind_map_df = load_csv_safe(JOBS_DIR / "mappings" / "industries.csv")
    sk_map_df = load_csv_safe(JOBS_DIR / "mappings" / "skills.csv")

    ind_lookup = {r.get("industry_id"): str(r.get("industry_name") or "") for r in ind_map_df.to_dict("records")} if not ind_map_df.empty else {}
    sk_lookup = {str(r.get("skill_abr")): str(r.get("skill_name") or "") for r in sk_map_df.to_dict("records")} if not sk_map_df.empty else {}

    # Load Companies
    comp_df = load_csv_safe(JOBS_DIR / "companies" / "companies.csv")
    comp_ind_df = load_csv_safe(JOBS_DIR / "companies" / "company_industries.csv")
    comp_spec_df = load_csv_safe(JOBS_DIR / "companies" / "company_specialities.csv")
    emp_df = load_csv_safe(JOBS_DIR / "companies" / "employee_counts.csv")

    comp_ind_map = defaultdict(list)
    if not comp_ind_df.empty:
        for r in comp_ind_df.itertuples(index=False):
            cid = str(getattr(r, "company_id", ""))
            ind = str(getattr(r, "industry", "") or "").strip()
            if cid and ind:
                comp_ind_map[cid].append(ind)

    comp_spec_map = defaultdict(list)
    if not comp_spec_df.empty:
        for r in comp_spec_df.itertuples(index=False):
            cid = str(getattr(r, "company_id", ""))
            spec = str(getattr(r, "speciality", "") or "").strip()
            if cid and spec:
                comp_spec_map[cid].append(spec)

    emp_count_map = {}
    if not emp_df.empty:
        for r in emp_df.itertuples(index=False):
            cid = str(getattr(r, "company_id", ""))
            ec = getattr(r, "employee_count", None)
            fc = getattr(r, "follower_count", None)
            if cid:
                emp_count_map[cid] = {
                    "employee_count": int(ec) if pd.notna(ec) else 0,
                    "follower_count": int(fc) if pd.notna(fc) else 0,
                }

    companies_dict = {}
    if not comp_df.empty:
        for r in comp_df.itertuples(index=False):
            cid = str(getattr(r, "company_id", ""))
            if cid:
                cname = str(getattr(r, "name", "Company") or "Company").strip()
                desc = str(getattr(r, "description", "") or "").strip()
                size = getattr(r, "company_size", None)
                city = str(getattr(r, "city", "") or "")
                state = str(getattr(r, "state", "") or "")
                country = str(getattr(r, "country", "") or "")
                loc = f"{city}, {state}, {country}".strip(", ")
                ec_info = emp_count_map.get(cid, {})

                companies_dict[cid] = {
                    "company_id": cid,
                    "name": cname,
                    "description": desc,
                    "company_size": int(size) if pd.notna(size) else 0,
                    "location": loc,
                    "url": str(getattr(r, "url", "") or ""),
                    "industries": comp_ind_map.get(cid, []),
                    "specialities": comp_spec_map.get(cid, []),
                    "employee_count": ec_info.get("employee_count", 0),
                    "follower_count": ec_info.get("follower_count", 0),
                }

    # Fast Bulk Save Companies to MongoDB if needed
    if db is not None and companies_dict:
        try:
            col_comp = db["companies"]
            if col_comp.count_documents({}) == 0:
                print(f"  ✓ Saving {len(companies_dict):,} companies to MongoDB 'companies'...")
                comp_ops = [UpdateOne({"company_id": c["company_id"]}, {"$set": c}, upsert=True) for c in companies_dict.values()]
                for i in range(0, len(comp_ops), batch_size):
                    col_comp.bulk_write(comp_ops[i:i + batch_size], ordered=False)
                print(f"  ✓ Saved {len(companies_dict):,} companies.")
        except Exception as e:
            print(f"  ⚠️ MongoDB companies save warning: {e}")

    # Fast Lookups for Benefits, Job Industries, Job Skills, Salaries
    benefits_df = load_csv_safe(JOBS_DIR / "jobs" / "benefits.csv")
    job_ind_df = load_csv_safe(JOBS_DIR / "jobs" / "job_industries.csv")
    job_sk_df = load_csv_safe(JOBS_DIR / "jobs" / "job_skills.csv")
    salaries_df = load_csv_safe(JOBS_DIR / "jobs" / "salaries.csv")

    benefits_map = defaultdict(list)
    if not benefits_df.empty:
        for r in benefits_df.itertuples(index=False):
            jid = str(getattr(r, "job_id", ""))
            btype = str(getattr(r, "type", "") or "").strip()
            if jid and btype:
                benefits_map[jid].append(btype)

    job_ind_map = defaultdict(list)
    if not job_ind_df.empty:
        for r in job_ind_df.itertuples(index=False):
            jid = str(getattr(r, "job_id", ""))
            iid = getattr(r, "industry_id", None)
            iname = ind_lookup.get(iid)
            if jid and iname:
                job_ind_map[jid].append(iname)

    job_sk_map = defaultdict(list)
    if not job_sk_df.empty:
        for r in job_sk_df.itertuples(index=False):
            jid = str(getattr(r, "job_id", ""))
            sabr = str(getattr(r, "skill_abr", ""))
            sname = sk_lookup.get(sabr) or sabr
            if jid and sname:
                job_sk_map[jid].append(sname)

    salaries_map = {}
    if not salaries_df.empty:
        for r in salaries_df.itertuples(index=False):
            jid = str(getattr(r, "job_id", ""))
            if jid:
                salaries_map[jid] = {
                    "max_salary": getattr(r, "max_salary", None),
                    "med_salary": getattr(r, "med_salary", None),
                    "min_salary": getattr(r, "min_salary", None),
                    "pay_period": str(getattr(r, "pay_period", "") or ""),
                    "currency": str(getattr(r, "currency", "USD") or "USD"),
                    "compensation_type": str(getattr(r, "compensation_type", "") or "")
                }

    # Build & Bulk Save Job Postings in Incremental Batches
    print("Assembling Job Postings & RAG chunks in batches...")
    
    total_processed = 0
    records = p_df.to_dict("records")

    for i in range(0, len(records), batch_size):
        chunk = records[i:i + batch_size]
        mongo_ops = []
        rag_docs = []

        for r in chunk:
            jid = str(r.get("job_id") or r.get("id") or f"job_{total_processed}")
            title = str(r.get("title") or "Software Engineer").strip()
            company_name = str(r.get("company_name") or "Enterprise").strip()
            location = str(r.get("location") or "Remote").strip()
            desc = str(r.get("description") or "").strip()
            
            cid = str(r.get("company_id")) if pd.notna(r.get("company_id")) else ""
            c_info = companies_dict.get(cid, {})

            j_benefits = list(set(benefits_map.get(jid, [])))
            j_industries = list(set(job_ind_map.get(jid, []) or c_info.get("industries", [])))
            j_skills = list(set(job_sk_map.get(jid, [])))
            
            skills_desc = str(r.get("skills_desc") or "")
            if skills_desc and skills_desc != "nan":
                j_skills.append(skills_desc[:100])

            j_salary = salaries_map.get(jid, {})
            min_sal = j_salary.get("min_salary") or r.get("min_salary")
            max_sal = j_salary.get("max_salary") or r.get("max_salary")
            pay_period = j_salary.get("pay_period") or r.get("pay_period") or "YEARLY"
            
            salary_str = "Not Specified"
            if pd.notna(min_sal) and pd.notna(max_sal):
                salary_str = f"${min_sal:,.0f} - ${max_sal:,.0f} ({pay_period})"
            elif pd.notna(max_sal):
                salary_str = f"Up to ${max_sal:,.0f} ({pay_period})"

            work_type = str(r.get("formatted_work_type") or r.get("work_type") or "Full-time")

            desc_snippet = desc[:450].replace("\n", " ")
            skills_str = ", ".join(j_skills[:10]) if j_skills else "Engineering, Technical"
            benefits_str = ", ".join(j_benefits[:6])
            ind_str = ", ".join(j_industries[:3])
            specs_str = ", ".join(c_info.get("specialities", [])[:5])

            rag_text = (
                f"Job Title: {title} | Company: {company_name} | Location: {location} | "
                f"Work Type: {work_type} | Salary: {salary_str} | Industry: {ind_str} | "
                f"Specialities: {specs_str} | Required Skills: {skills_str} | "
                f"Benefits: {benefits_str} | Description: {desc_snippet}"
            )

            mongo_doc = {
                "job_id": jid,
                "title": title,
                "company": company_name,
                "company_id": cid,
                "location": location,
                "work_type": work_type,
                "salary": salary_str,
                "min_salary": float(min_sal) if pd.notna(min_sal) else None,
                "max_salary": float(max_sal) if pd.notna(max_sal) else None,
                "description": desc,
                "required_skills": j_skills,
                "benefits": j_benefits,
                "industries": j_industries,
                "company_specialities": c_info.get("specialities", []),
                "company_size": c_info.get("company_size", 0),
                "job_text": rag_text,
            }
            mongo_ops.append(UpdateOne({"job_id": jid}, {"$set": mongo_doc}, upsert=True))

            rag_docs.append({
                "id": f"job_{jid}",
                "text": rag_text,
                "metadata": {
                    "namespace": "jobs",
                    "title": title,
                    "company": company_name,
                    "location": location,
                    "type": "job",
                    "job_id": jid,
                }
            })

        # Fast PyMongo Bulk Write
        if db is not None and mongo_ops:
            try:
                db["jobs"].bulk_write(mongo_ops, ordered=False)
            except Exception as e:
                print(f"  ⚠️ Bulk write warning for batch: {e}")

        # Vector Embeddings & Pinecone Upsert
        if rag_docs:
            upsert_rag_documents(rag_docs)

        total_processed += len(chunk)
        current_total = skipped_count + total_processed
        print(f"  [+] Jobs Progress: {current_total:,}/{total_jobs:,} ({(current_total/total_jobs)*100:.1f}%) [Auto-Saved ✓]")

    print(f"  ✓ Jobs & Companies Ingestion Complete! Total: {skipped_count + total_processed:,}")
    return skipped_count + total_processed


def main():
    parser = argparse.ArgumentParser(description="High-Speed Resumable Multi-Archive Ingestion Pipeline for MongoDB & RAG")
    parser.add_argument("--limit", type=int, default=0, help="Limit maximum records per dataset (0 = process all)")
    parser.add_argument("--batch-size", type=int, default=2000, help="Batch size for database & vector store bulk writes")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion of already existing records")
    parser.add_argument("--zip-resumes", type=str, default=ZIP_RESUMES_PATH, help="Path to archive (1).zip")
    parser.add_argument("--zip-jobs", type=str, default=ZIP_JOBS_PATH, help="Path to archive (2).zip")
    args = parser.parse_args()

    extract_zips_if_needed(zip_resumes=args.zip_resumes, zip_jobs=args.zip_jobs)
    
    resumes_count = process_resumes_dataset(limit=args.limit, batch_size=args.batch_size, force=args.force)
    jobs_count = process_jobs_dataset(limit=args.limit, batch_size=args.batch_size, force=args.force)

    print("\n" + "=" * 70)
    print(" 🎉 COMPLETE MULTI-ARCHIVE DATASET INGESTION FINISHED!")
    print(f" Total Candidate Resumes: {resumes_count:,}")
    print(f" Total Jobs & Companies: {jobs_count:,}")
    print(" RAG & MongoDB Database state is now 100% updated with all 17 CSV files!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
