"""
JOB-AI-PLATFORM - Login / Register Page
"""

import streamlit as st
import requests

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Login - JOB-AI-PLATFORM", page_icon="🔐", layout="centered")

for key, default in {"token": None, "user": None}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown("# 🔐 Login / Register")
st.divider()

if st.session_state.token:
    st.success(f"Already logged in as **{st.session_state.user.get('full_name','User')}**")
    if st.button("Logout"):
        st.session_state.token = None
        st.session_state.user  = None
        st.rerun()
    st.stop()

tab1, tab2 = st.tabs(["Login", "Register"])

# LOGIN
with tab1:
    st.markdown("### Welcome Back")
    email    = st.text_input("Email",    placeholder="you@example.com",  key="login_email")
    password = st.text_input("Password", placeholder="Your password",     key="login_pass", type="password")

    if st.button("Login", use_container_width=True, type="primary"):
        if not email or not password:
            st.error("Please fill in all fields.")
        else:
            try:
                res = requests.post(
                    f"{API_BASE}/auth/login",
                    data={"username": email, "password": password},
                    timeout=5
                )
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.token = data.get("access_token")
                    # Fetch user info
                    me = requests.get(
                        f"{API_BASE}/auth/me",
                        headers={"Authorization": f"Bearer {st.session_state.token}"},
                        timeout=5
                    ).json()
                    st.session_state.user = me.get("data", {})
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error(f"Login failed: {res.json().get('detail','Invalid credentials')}")
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")

# REGISTER
with tab2:
    st.markdown("### Create Account")
    full_name = st.text_input("Full Name", placeholder="John Doe",         key="reg_name")
    reg_email = st.text_input("Email",     placeholder="you@example.com",  key="reg_email")
    reg_pass  = st.text_input("Password",  placeholder="Choose password",  key="reg_pass",  type="password")
    role      = st.selectbox("I am a",    ["job_seeker", "recruiter"],      key="reg_role")

    if st.button("Register", use_container_width=True, type="primary"):
        if not full_name or not reg_email or not reg_pass:
            st.error("Please fill in all fields.")
        else:
            try:
                res = requests.post(
                    f"{API_BASE}/auth/register",
                    json={"full_name": full_name, "email": reg_email,
                          "password": reg_pass, "role": role},
                    timeout=5
                )
                if res.status_code == 200:
                    st.success("Account created! Please login.")
                else:
                    st.error(f"Registration failed: {res.json().get('detail','Error')}")
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")
