"""
JOB-AI-PLATFORM - AI Chatbot Page
"""

import streamlit as st
import requests
import uuid

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="AI Chatbot - JOB-AI-PLATFORM", page_icon="🤖", layout="wide")

for key, default in {"token": None, "user": None,
                     "session_id": str(uuid.uuid4()),
                     "chat_history": []}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown("# 🤖 AI Career Chatbot")
st.caption("Powered by Groq LLaMA3 + RAG over real job data")
st.divider()

if not st.session_state.token:
    st.warning("Please login to use the chatbot.")
    st.page_link("pages/2_Login.py", label="👉 Go to Login")
    st.stop()

# Suggested questions
st.markdown("**Suggested Questions:**")
sc1, sc2, sc3 = st.columns(3)
suggestions = [
    "What Python jobs are available?",
    "What skills do Data Scientists need?",
    "What is the average salary for ML Engineers?",
]
for col, q in zip([sc1, sc2, sc3], suggestions):
    if col.button(q, use_container_width=True):
        st.session_state.chat_history.append({"role": "user", "content": q})

st.divider()

# Chat history display
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
prompt = st.chat_input("Ask me about jobs, careers, salaries...")

if prompt:
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                res = requests.post(
                    f"{API_BASE}/chat/",
                    json={"question": prompt,
                          "session_id": st.session_state.session_id},
                    headers=headers, timeout=30
                )
                if res.status_code == 200:
                    answer = res.json().get("data", {}).get("answer", "No response.")
                    st.write(answer)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": answer}
                    )
                else:
                    st.error("Chatbot error. Make sure Groq API key is set in .env")
            except Exception as e:
                st.error(f"Could not reach backend: {e}")

# Clear chat
st.divider()
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("Clear Chat", use_container_width=True):
        try:
            requests.delete(
                f"{API_BASE}/chat/{st.session_state.session_id}",
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                timeout=5
            )
        except Exception:
            pass
        st.session_state.chat_history = []
        st.session_state.session_id   = str(uuid.uuid4())
        st.rerun()
