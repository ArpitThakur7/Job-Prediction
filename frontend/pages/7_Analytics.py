"""
JOB-AI-PLATFORM - Analytics Page
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import json
import os

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Analytics - JOB-AI-PLATFORM", page_icon="📊", layout="wide")

st.markdown("# 📊 Platform Analytics")
st.divider()

# Load summary if available
summary = {}
summary_path = "data/processed/dataset_summary.json"
if os.path.exists(summary_path):
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

# Top row metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Jobs",    summary.get("jobs",    {}).get("total_rows", 0))
col2.metric("Total Resumes", summary.get("resumes", {}).get("total_rows", 0))
col3.metric("Match Records", summary.get("labels",  {}).get("total_rows", 0))
col4.metric("Avg Match Score",
            f"{summary.get('features', {}).get('avg_match_score', 0):.0%}")

st.divider()

row1_col1, row1_col2 = st.columns(2)

# Top Skills in Demand
with row1_col1:
    st.markdown("#### Top Skills In Demand")
    top_skills = summary.get("jobs", {}).get("top_skills", {})
    if top_skills:
        df_skills = pd.DataFrame(list(top_skills.items()),
                                  columns=["Skill", "Count"]).sort_values("Count", ascending=True)
        fig = px.bar(df_skills, x="Count", y="Skill", orientation="h",
                     color="Count", color_continuous_scale="teal")
        fig.update_layout(showlegend=False, height=400, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Run prepare_dataset.py first to see analytics.")

# Top Job Categories
with row1_col2:
    st.markdown("#### Job Categories Distribution")
    top_cats = summary.get("jobs", {}).get("top_categories", {})
    if top_cats:
        df_cats = pd.DataFrame(list(top_cats.items()), columns=["Category", "Count"])
        fig = px.pie(df_cats, values="Count", names="Category", hole=0.4)
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No category data available.")

st.divider()
row2_col1, row2_col2 = st.columns(2)

# Education Distribution
with row2_col1:
    st.markdown("#### Candidate Education Levels")
    edu = summary.get("resumes", {}).get("education_distribution", {})
    if edu:
        df_edu = pd.DataFrame(list(edu.items()), columns=["Education", "Count"])
        fig = px.bar(df_edu, x="Education", y="Count",
                     color="Count", color_continuous_scale="purples")
        fig.update_layout(showlegend=False, height=350, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No education data available.")

# Top Locations
with row2_col2:
    st.markdown("#### Top Job Locations")
    locs = summary.get("jobs", {}).get("top_locations", {})
    if locs:
        df_locs = pd.DataFrame(list(locs.items()),
                                columns=["Location", "Count"]).sort_values("Count", ascending=False)
        fig = px.bar(df_locs, x="Location", y="Count",
                     color="Count", color_continuous_scale="blues")
        fig.update_layout(showlegend=False, height=350,
                          xaxis_tickangle=-30, margin=dict(l=0, r=0, t=20, b=60))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No location data available.")

st.divider()

# Match ratio
st.markdown("#### Match Distribution")
labels_data = summary.get("labels", {})
pos = labels_data.get("positive_matches", 0)
neg = labels_data.get("negative_matches", 0)
if pos or neg:
    df_match = pd.DataFrame({"Type": ["Positive Match", "No Match"], "Count": [pos, neg]})
    fig = px.pie(df_match, values="Count", names="Type",
                 color_discrete_sequence=["#28a745", "#dc3545"], hole=0.3)
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)
