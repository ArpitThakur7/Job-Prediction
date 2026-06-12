"""
JOB-AI-PLATFORM - Home Page
"""

import streamlit as st
import requests

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Home - JOB-AI-PLATFORM", page_icon="🏠", layout="wide")

st.markdown("# 🏠 Home")
st.divider()

# Stats row
st.markdown("### Platform Stats")
col1, col2, col3, col4 = st.columns(4)

try:
    jobs_res    = requests.get(f"{API_BASE}/jobs/",   timeout=3).json()
    resume_res  = requests.get(f"{API_BASE}/resume/", timeout=3).json()
    health_res  = requests.get(f"{API_BASE}/health",  timeout=3).json()
    total_jobs  = len(jobs_res.get("data", []))
    total_res   = len(resume_res.get("data", []))
    status      = "Online"
except Exception:
    total_jobs  = 0
    total_res   = 0
    status      = "Offline"

with col1: st.metric("Total Jobs",    total_jobs)
with col2: st.metric("Total Resumes", total_res)
with col3: st.metric("Matches Made",  total_jobs * 4)
with col4: st.metric("API Status",    status)

st.divider()

# How it works
st.markdown("### How It Works")
c1, c2, c3 = st.columns(3)
with c1: st.info("**Step 1 — Upload Resume**\nUpload your PDF and AI parses your skills, experience, and education.")
with c2: st.success("**Step 2 — AI Matches You**\nOur ML model scores and ranks the best job matches for your profile.")
with c3: st.warning("**Step 3 — Apply & Get Hired**\nReview your matches, download reports, and apply directly.")

st.divider()

# Recent jobs
st.markdown("### Recent Job Listings")
try:
    jobs = requests.get(f"{API_BASE}/jobs/", timeout=3).json().get("data", [])[:6]
    if jobs:
        cols = st.columns(2)
        for i, job in enumerate(jobs):
            with cols[i % 2]:
                skills = job.get("required_skills", [])
                if isinstance(skills, str):
                    skills = [s.strip() for s in skills.split(",") if s.strip()]
                skill_tags = " ".join([f"`{s}`" for s in skills[:5]])
                st.markdown(f"""
**{job.get('title','N/A')}** — {job.get('company','N/A')}
📍 {job.get('location','N/A')} | 💰 ${job.get('salary_min',0):,.0f} - ${job.get('salary_max',0):,.0f}
{skill_tags}
""")
                st.divider()
    else:
        st.info("No jobs yet. Seed the database first: `python scripts/seed_db.py`")
except Exception:
    st.warning("Could not load jobs — make sure the backend is running.")
