"""
dashboard.py
============
Streamlit dashboard for the Job-Candidate Matcher API.

Run
---
    streamlit run dashboard.py

Requires
--------
    pip install streamlit requests pandas plotly
"""

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
import os
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")

st.set_page_config(
    page_title="Job-Candidate Matcher",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"] { background: #161b27; border-right: 1px solid #1e2a3a; }

.metric-row { display: flex; gap: 12px; margin-bottom: 1rem; }
.metric-card {
    flex: 1; background: #161b27; border: 1px solid #1e2a3a;
    border-radius: 10px; padding: 16px 20px;
}
.metric-card .label { font-size: 12px; color: #6b7a99; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }
.metric-card .value { font-size: 28px; font-weight: 600; color: #e2e8f0; }
.metric-card .sub   { font-size: 12px; color: #4a5568; margin-top: 2px; }

.badge-match   { background: #0d3321; color: #34d399; border: 1px solid #065f46; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; }
.badge-nomatch { background: #3b1a1a; color: #f87171; border: 1px solid #7f1d1d; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; }
.badge-high    { background: #0d3321; color: #34d399; border: 1px solid #065f46; padding: 2px 10px; border-radius: 12px; font-size: 12px; }
.badge-medium  { background: #2d2006; color: #fbbf24; border: 1px solid #92400e; padding: 2px 10px; border-radius: 12px; font-size: 12px; }
.badge-low     { background: #3b1a1a; color: #f87171; border: 1px solid #7f1d1d; padding: 2px 10px; border-radius: 12px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api_get(path):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(path, payload):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API. Is `uvicorn api.main:app --port 8000` running?")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e.response.json().get('detail', str(e))}")
        return None


def confidence_badge(conf):
    cls = {"High": "badge-high", "Medium": "badge-medium", "Low": "badge-low"}.get(conf, "badge-low")
    return f'<span class="{cls}">{conf}</span>'


def prob_gauge(prob, threshold):
    color = "#34d399" if prob >= threshold else "#f87171"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(prob * 100, 2),
        number={"suffix": "%", "font": {"size": 40, "color": "#e2e8f0"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#4a5568", "tickfont": {"color": "#4a5568"}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "#161b27",
            "bordercolor": "#1e2a3a",
            "steps": [
                {"range": [0, threshold * 100], "color": "#1a2035"},
                {"range": [threshold * 100, 100], "color": "#0d2a1e"},
            ],
            "threshold": {
                "line": {"color": "#fbbf24", "width": 2},
                "thickness": 0.75,
                "value": threshold * 100,
            },
        },
    ))
    fig.update_layout(
        height=220, margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor="#0f1117", font_color="#e2e8f0",
    )
    return fig


def shap_bar_chart(contributions):
    features = [c["feature"] for c in contributions]
    values   = [c["shap"] for c in contributions]
    colors   = ["#34d399" if v > 0 else "#f87171" for v in values]
    fig = go.Figure(go.Bar(
        x=values, y=features, orientation="h",
        marker_color=colors,
        text=[f"{v:+.4f}" for v in values],
        textposition="outside",
        textfont={"color": "#94a3b8", "size": 11},
    ))
    fig.update_layout(
        height=max(220, len(features) * 44),
        margin=dict(l=10, r=70, t=10, b=10),
        paper_bgcolor="#0f1117", plot_bgcolor="#161b27",
        xaxis=dict(gridcolor="#1e2a3a", zerolinecolor="#2d3748", color="#4a5568"),
        yaxis=dict(gridcolor="#1e2a3a", color="#94a3b8"),
        showlegend=False,
    )
    return fig


def render_result(result):
    prob    = result["match_probability"]
    verdict = result["verdict"]
    conf    = result["confidence"]
    thresh  = result["threshold_used"]

    badge = '<span class="badge-match">MATCH</span>' if verdict == "MATCH" else '<span class="badge-nomatch">NO MATCH</span>'

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="label">Verdict</div>
            <div class="value">{badge}</div>
        </div>
        <div class="metric-card">
            <div class="label">Probability</div>
            <div class="value">{prob:.1%}</div>
            <div class="sub">threshold {thresh:.4f}</div>
        </div>
        <div class="metric-card">
            <div class="label">Confidence</div>
            <div class="value">{confidence_badge(conf)}</div>
            <div class="sub">distance from threshold</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.plotly_chart(prob_gauge(prob, thresh), use_container_width=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🎯 Matcher")
    st.markdown("**API STATUS**")

    health = api_get("/health")
    if health:
        st.success(f"Online · {health.get('loaded_at', '')}")
        info = api_get("/model/info")
        if info:
            st.markdown(f"**Threshold** `{info['threshold']:.4f}`")
            st.markdown(f"**Estimators** `{info['n_estimators']}`")
            st.markdown(f"**Max depth** `{info['max_depth']}`")
            st.markdown("**Features**")
            for f in info["feature_columns"]:
                st.markdown(f"- `{f}`")
    else:
        st.error("API offline")
        st.code("uvicorn api.main:app --reload --port 8000")

    st.markdown("---")
    page = st.radio("View", ["Single pair", "Batch scoring", "Explain a pair"],
                    label_visibility="collapsed")

    st.markdown("---")
    st.markdown("**📖 Feature guide**")
    with st.expander("What does each field mean?", expanded=False):
        st.markdown("""
**`experience_gap`** — years of experience on the resume *(not a gap)*. Use 8–12 for strong matches. Your #1 prediction driver.

**`skill_overlap_ratio`** — share of the job's required skills the candidate has. `0.75` = covers 75% of requirements. Keep above 0.70 for matches.

**`skill_overlap_count`** — raw number of matching skills. A count of 3 at ratio 0.75 means the job needs 4 skills total.

**`education_score`** — degree alignment (integer):
- `1` = High school
- `2` = Bachelor's
- `3` = Master's
- `4` = PhD / equivalent

**`location_match`** — `1` if same location, `0` if not. Has near-zero weight in this model — training data showed matches regardless of location.

**`skills_count_resume`** — total skills on the resume. Weakly positive — the model mostly relies on the overlap ratio instead.

---
🟢 **For a strong MATCH:** experience_gap ≥ 8, skill_overlap_ratio ≥ 0.70, education_score ≥ 3
        """)

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

for key in ("single_result", "explain_result"):
    if key not in st.session_state:
        st.session_state[key] = None

# ---------------------------------------------------------------------------
# Page: Single pair
# ---------------------------------------------------------------------------

if page == "Single pair":
    st.markdown("## Score a pair")
    st.markdown("Enter feature values for one resume and job, then click **Score this pair**.")
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        resume_id           = st.text_input("Resume ID (optional)")
        skill_overlap_count = st.number_input("Skill overlap count", min_value=0, value=4)
        experience_gap      = st.number_input("Experience gap (years)", value=-1.0, step=0.5)
        location_match      = st.selectbox("Location match", [1, 0])
    with c2:
        job_id              = st.text_input("Job ID (optional)")
        skill_overlap_ratio = st.slider("Skill overlap ratio", 0.0, 1.0, 0.57, 0.01)
        education_score     = st.number_input("Education score", min_value=0, value=2)
        skills_count_resume = st.number_input("Skills on resume", min_value=0, value=7)

    if st.button("Score this pair", type="primary"):
        payload = {
            "resume_id":           resume_id or None,
            "job_id":              job_id or None,
            "skill_overlap_count": int(skill_overlap_count),
            "skill_overlap_ratio": float(skill_overlap_ratio),
            "experience_gap":      float(experience_gap),
            "education_score":     int(education_score),
            "location_match":      float(location_match),
            "skills_count_resume": int(skills_count_resume),
        }
        with st.spinner("Scoring..."):
            st.session_state.single_result = api_post("/match", payload)

    if st.session_state.single_result:
        st.markdown("---")
        render_result(st.session_state.single_result)

# ---------------------------------------------------------------------------
# Page: Batch scoring
# ---------------------------------------------------------------------------

elif page == "Batch scoring":
    st.markdown("## Batch scoring")
    st.markdown("Upload a CSV with feature columns to score all pairs at once.")
    st.markdown("---")

    REQUIRED = ["skill_overlap_count", "skill_overlap_ratio", "experience_gap",
                "education_score", "location_match", "skills_count_resume"]

    uploaded    = st.file_uploader("Upload CSV", type=["csv"])
    use_optimal = st.checkbox("Use optimal threshold (0.7232)", value=True)

    if uploaded:
        df = pd.read_csv(uploaded)
        st.markdown(f"**{len(df)} rows loaded**")

        missing = [c for c in REQUIRED if c not in df.columns]
        if missing:
            st.error(f"Missing columns: {missing}")
        else:
            if st.button("Run batch scoring", type="primary"):
                pairs = []
                for _, row in df.iterrows():
                    pair = {c: float(row[c]) for c in REQUIRED}
                    if "resume_id" in df.columns: pair["resume_id"] = str(row["resume_id"])
                    if "job_id"    in df.columns: pair["job_id"]    = str(row["job_id"])
                    pairs.append(pair)

                with st.spinner(f"Scoring {len(pairs)} pairs..."):
                    result = api_post("/match/batch", {
                        "pairs": pairs,
                        "use_optimal_threshold": use_optimal,
                    })

                if result:
                    total      = result["total"]
                    matched    = result["matched"]
                    match_rate = result["match_rate"]
                    results    = result["results"]

                    st.markdown(f"""
                    <div class="metric-row">
                        <div class="metric-card"><div class="label">Total</div><div class="value">{total}</div></div>
                        <div class="metric-card"><div class="label">Matches</div><div class="value" style="color:#34d399">{matched}</div></div>
                        <div class="metric-card"><div class="label">Match rate</div><div class="value">{match_rate:.1%}</div></div>
                        <div class="metric-card"><div class="label">No matches</div><div class="value" style="color:#f87171">{total - matched}</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    conf_counts = pd.Series([r["confidence"] for r in results]).value_counts()
                    fig = go.Figure(go.Bar(
                        x=conf_counts.index.tolist(),
                        y=conf_counts.values.tolist(),
                        marker_color=["#34d399", "#fbbf24", "#f87171"][:len(conf_counts)],
                    ))
                    fig.update_layout(
                        title="Confidence breakdown", height=260,
                        paper_bgcolor="#0f1117", plot_bgcolor="#161b27",
                        font_color="#94a3b8",
                        xaxis=dict(gridcolor="#1e2a3a"),
                        yaxis=dict(gridcolor="#1e2a3a"),
                        margin=dict(l=10, r=10, t=36, b=10),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown("### Results")
                    results_df = pd.DataFrame([{
                        "resume_id":   r.get("resume_id", ""),
                        "job_id":      r.get("job_id", ""),
                        "probability": r["match_probability"],
                        "verdict":     r["verdict"],
                        "confidence":  r["confidence"],
                    } for r in results])

                    st.dataframe(
                        results_df.sort_values("probability", ascending=False),
                        use_container_width=True,
                        height=400,
                    )

                    st.download_button(
                        "Download results CSV",
                        data=results_df.to_csv(index=False),
                        file_name="match_results.csv",
                        mime="text/csv",
                    )

# ---------------------------------------------------------------------------
# Page: Explain a pair
# ---------------------------------------------------------------------------

elif page == "Explain a pair":
    st.markdown("## Explain a prediction")
    st.markdown("Get per-feature SHAP contributions alongside the match score.")
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        resume_id           = st.text_input("Resume ID (optional)", key="ex_rid")
        skill_overlap_count = st.number_input("Skill overlap count", min_value=0, value=4, key="ex_soc")
        experience_gap      = st.number_input("Experience gap (years)", value=-1.0, step=0.5, key="ex_eg")
        location_match      = st.selectbox("Location match", [1, 0], key="ex_lm")
    with c2:
        job_id              = st.text_input("Job ID (optional)", key="ex_jid")
        skill_overlap_ratio = st.slider("Skill overlap ratio", 0.0, 1.0, 0.57, 0.01, key="ex_sor")
        education_score     = st.number_input("Education score", min_value=0, value=2, key="ex_es")
        skills_count_resume = st.number_input("Skills on resume", min_value=0, value=7, key="ex_scr")

    if st.button("Score + explain", type="primary"):
        payload = {
            "resume_id":           resume_id or None,
            "job_id":              job_id or None,
            "skill_overlap_count": int(skill_overlap_count),
            "skill_overlap_ratio": float(skill_overlap_ratio),
            "experience_gap":      float(experience_gap),
            "education_score":     int(education_score),
            "location_match":      float(location_match),
            "skills_count_resume": int(skills_count_resume),
        }
        with st.spinner("Scoring + computing SHAP..."):
            st.session_state.explain_result = api_post("/match/explain", payload)

    if st.session_state.explain_result:
        result = st.session_state.explain_result
        st.markdown("---")

        col1, col2 = st.columns([1, 1])
        with col1:
            render_result(result)
        with col2:
            st.markdown(f"**Base value** `{result.get('base_value', 0):.4f}` — average model output")
            st.markdown("### Feature contributions")
            st.markdown("🟢 Green = pushes toward match · 🔴 Red = pushes away")
            st.plotly_chart(shap_bar_chart(result["contributions"]), use_container_width=True)

        st.markdown("### Breakdown")
        contrib_df = pd.DataFrame(result["contributions"])
        contrib_df["shap"] = contrib_df["shap"].apply(lambda x: f"{x:+.4f}")
        st.dataframe(contrib_df, use_container_width=True, hide_index=True)
