"""
JOB-AI-PLATFORM - Browse Jobs Page
"""

import streamlit as st
import requests

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Browse Jobs - JOB-AI-PLATFORM", page_icon="🔍", layout="wide")

for key, default in {"token": None, "user": None}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown("# 🔍 Browse Jobs")
st.divider()

# Sidebar filters
with st.sidebar:
    st.markdown("### Filters")
    location   = st.text_input("Location",  placeholder="e.g. London")
    category   = st.selectbox("Category", ["All", "Engineering", "IT", "Finance",
                               "Healthcare", "Marketing", "Sales", "Education",
                               "Design", "Data Science", "Management", "Other"])
    job_type   = st.selectbox("Job Type",  ["All", "full_time", "part_time",
                                             "contract", "remote"])
    sal_range  = st.slider("Salary Range ($)", 0, 200000, (0, 200000), step=5000)
    search_btn = st.button("Apply Filters", use_container_width=True, type="primary")

# Search bar
search_q = st.text_input("Search jobs by title or keyword",
                          placeholder="e.g. Python Developer, Data Scientist...")
col_s, col_c = st.columns([1, 5])
with col_s:
    do_search = st.button("Search", type="primary")

# Build params
params = {}
if location and location.strip():      params["location"]   = location
if category  != "All":                 params["category"]   = category
if job_type  != "All":                 params["job_type"]   = job_type
if sal_range[0] > 0:                   params["salary_min"] = sal_range[0]
if sal_range[1] < 200000:              params["salary_max"] = sal_range[1]

# Fetch jobs
try:
    if do_search and search_q:
        res  = requests.get(f"{API_BASE}/jobs/search", params={"q": search_q}, timeout=5)
    else:
        res  = requests.get(f"{API_BASE}/jobs/", params=params, timeout=5)
    jobs = res.json().get("data", [])
except Exception:
    jobs = []
    st.error("Could not connect to backend.")

# Pagination
PAGE_SIZE = 10
total     = len(jobs)
page      = st.number_input("Page", min_value=1,
                              max_value=max(1, (total // PAGE_SIZE) + 1),
                              value=1, step=1)
start     = (page - 1) * PAGE_SIZE
paged     = jobs[start:start + PAGE_SIZE]

st.markdown(f"**Showing {len(paged)} of {total} jobs**")
st.divider()

if not paged:
    st.info("No jobs found. Try different filters or seed the database.")
else:
    cols = st.columns(2)
    for i, job in enumerate(paged):
        skills = job.get("required_skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        skill_tags = " ".join([f"`{s}`" for s in skills[:5]])

        with cols[i % 2]:
            sal_min = job.get("salary_min", 0)
            sal_max = job.get("salary_max", 0)
            sal_str = f"${sal_min:,.0f} - ${sal_max:,.0f}" if sal_max > 0 else "Not specified"

            st.markdown(f"""
### {job.get('title','N/A')}
**{job.get('company','N/A')}** | 📍 {job.get('location','N/A')}
💰 {sal_str} | 🏷 `{job.get('job_type','N/A')}`
{skill_tags}
""")
            with st.expander("View Full Description"):
                st.write(job.get("description", "No description available."))

            if st.session_state.token:
                if st.button(f"Apply", key=f"apply_{job.get('job_id',i)}"):
                    st.success("Application submitted!")
            else:
                st.caption("Login to apply")
            st.divider()
