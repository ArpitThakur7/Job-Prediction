"""
JOB-AI-PLATFORM - Main Streamlit Entry Point
Run: streamlit run frontend/app.py
"""

import streamlit as st
import requests
import uuid

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="JOB-AI-PLATFORM",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state init
for key, default in {
    "token": None,
    "user": None,
    "resume_id": None,
    "session_id": str(uuid.uuid4()),
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Sidebar
with st.sidebar:
    st.markdown("## 💼 JOB-AI-PLATFORM")
    st.markdown("*AI-Powered Job Matching*")
    st.divider()

    st.page_link("pages/1_Home.py",            label="🏠 Home")
    st.page_link("pages/2_Login.py",           label="🔐 Login / Register")
    st.page_link("pages/3_Upload_Resume.py",   label="📄 Upload Resume")
    st.page_link("pages/4_Browse_Jobs.py",     label="🔍 Browse Jobs")
    st.page_link("pages/5_Match_Results.py",   label="🎯 My Matches")
    st.page_link("pages/6_Chatbot.py",         label="🤖 AI Chatbot")
    st.page_link("pages/7_Analytics.py",       label="📊 Analytics")

    st.divider()
    if st.session_state.user:
        st.success(f"Logged in as\n**{st.session_state.user.get('full_name','User')}**")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.user  = None
            st.rerun()
    else:
        st.info("Not logged in")
        st.page_link("pages/2_Login.py", label="👉 Login / Register")

# Home page
st.markdown("# 💼 JOB-AI-PLATFORM")
st.markdown("### AI-Powered Job Matching Platform")
st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.info("### 📄 Resume Parsing\nUpload your PDF resume and let AI extract your skills, experience, and education automatically.")
with col2:
    st.success("### 🎯 Smart Matching\nOur XGBoost ML model matches your profile to the most relevant job listings with accuracy scores.")
with col3:
    st.warning("### 🤖 AI Chatbot\nAsk our Groq-powered AI assistant career questions using RAG over real job data.")

st.divider()
try:
    res = requests.get(f"{API_BASE}/health", timeout=3)
    if res.status_code == 200:
        st.success("✅ Backend API is online")
    else:
        st.error("❌ Backend API returned error")
except Exception:
    st.error("❌ Backend API is offline — run: uvicorn backend.main:app --reload")
