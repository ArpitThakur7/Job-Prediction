"""
JOB-AI-PLATFORM - Match Results Page
"""

import streamlit as st
import requests

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="My Matches - JOB-AI-PLATFORM", page_icon="🎯", layout="wide")

for key, default in {"token": None, "user": None, "resume_id": None}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown("# 🎯 My Job Matches")
st.divider()

if not st.session_state.token:
    st.warning("Please login first.")
    st.page_link("pages/2_Login.py", label="👉 Go to Login")
    st.stop()

if not st.session_state.resume_id:
    st.warning("Please upload your resume first to see matches.")
    st.page_link("pages/3_Upload_Resume.py", label="👉 Upload Resume")
    st.stop()

top_k = st.slider("Number of matches to show", 5, 20, 10)

if st.button("Find My Best Matches", type="primary", use_container_width=True):
    with st.spinner("AI is finding your best job matches..."):
        try:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            res = requests.post(
                f"{API_BASE}/match/resume-to-jobs",
                json={"resume_id": st.session_state.resume_id, "top_k": top_k},
                headers=headers, timeout=30
            )
            if res.status_code == 200:
                matches = res.json().get("data", [])
                st.success(f"Found **{len(matches)}** matches for your resume!")
                st.divider()

                for i, match in enumerate(matches):
                    score   = match.get("match_score", 0)
                    pct     = int(score * 100)
                    color   = "green" if pct >= 70 else ("orange" if pct >= 40 else "red")

                    col1, col2, col3 = st.columns([1, 3, 2])

                    with col1:
                        st.markdown(f"""
<div style='text-align:center; padding:20px; border-radius:10px;
background-color:{"#d4edda" if pct>=70 else ("#fff3cd" if pct>=40 else "#f8d7da")}'>
<h2 style='color:{color};margin:0'>{pct}%</h2>
<small>Match Score</small>
</div>""", unsafe_allow_html=True)

                    with col2:
                        st.markdown(f"### {match.get('title','N/A')}")
                        st.write(f"**{match.get('company','N/A')}** | 📍 {match.get('location','N/A')}")
                        matched = match.get("matched_skills", [])
                        if isinstance(matched, str):
                            matched = [s.strip() for s in matched.split(",") if s.strip()]
                        if matched:
                            st.write("**Matched Skills:** " + " ".join([f"`{s}`" for s in matched[:6]]))

                    with col3:
                        sal_min = match.get("salary_min", 0)
                        sal_max = match.get("salary_max", 0)
                        sal_str = f"${sal_min:,.0f} - ${sal_max:,.0f}" if sal_max > 0 else "N/A"
                        st.metric("Salary", sal_str)

                        try:
                            rpt = requests.get(
                                f"{API_BASE}/match/report/{st.session_state.resume_id}/{match.get('job_id')}",
                                headers=headers, timeout=10
                            )
                            if rpt.status_code == 200:
                                st.download_button(
                                    "Download Report",
                                    data=rpt.content,
                                    file_name=f"match_report_{i+1}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_{i}"
                                )
                        except Exception:
                            pass

                    st.divider()
            else:
                st.error(f"Matching failed: {res.json().get('detail','Error')}")
        except Exception as e:
            st.error(f"Error: {e}")
