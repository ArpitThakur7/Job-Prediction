"""
Unit Tests for Phase 3 ATS Scoring Engine & Phase 4 Gap Analysis
"""

import pytest
from backend.services.structured_extractor import (
    StructuredResumeSchema,
    ContactInfo,
    SkillsCategorized,
    ExperienceEntry,
    EducationEntry,
)
from backend.services.ats_scorer import score_resume_ats
from backend.services.gap_analyzer import perform_skill_gap_analysis


def test_perfect_resume_ats_score():
    structured = StructuredResumeSchema(
        contact=ContactInfo(
            name="Alice Smith",
            email="alice.smith@example.com",
            phone="555-123-4567",
            location="New York, NY",
            linkedin="linkedin.com/in/alicesmith",
        ),
        summary="Results-driven Senior Software Engineer with 8 years of experience building high-scale distributed systems.",
        skills=SkillsCategorized(
            technical=["Python", "PostgreSQL", "Docker", "Kubernetes", "FastAPI", "React", "Redis"],
            soft=["Leadership", "Agile", "Mentorship"],
            tools=["Git", "Jira", "AWS"],
        ),
        experience=[
            ExperienceEntry(
                title="Senior Backend Engineer",
                company="DataScale Inc",
                location="New York, NY",
                start_date="2020",
                end_date="Present",
                bullets=[
                    "Architected event-driven data streaming pipeline, increasing transaction throughput by 45%.",
                    "Spearheaded cloud migration to AWS EKS, reducing infrastructure cost by $120K annually.",
                ],
                has_quantified_impact=True,
            )
        ],
        education=[
            EducationEntry(
                degree="Bachelor of Science in Computer Science",
                institution="Columbia University",
                graduation_date="2018",
            )
        ],
        sections_detected=["contact", "summary", "experience", "education", "skills"],
        sections_missing=[],
    )

    raw_text = (
        "Alice Smith - Senior Software Engineer\n"
        "Email: alice.smith@example.com | Phone: 555-123-4567 | Location: New York, NY\n"
        "Summary: Results-driven Senior Software Engineer with 8 years of experience building high-scale distributed systems.\n"
        "Skills: Python, PostgreSQL, Docker, Kubernetes, FastAPI, React, Redis, Leadership, Agile, Git, AWS.\n"
        "Work Experience:\n"
        "Senior Backend Engineer at DataScale Inc (2020 - Present)\n"
        "- Architected event-driven data streaming pipeline, increasing transaction throughput by 45%.\n"
        "- Spearheaded cloud migration to AWS EKS, reducing infrastructure cost by $120K annually.\n"
        "Education:\n"
        "Bachelor of Science in Computer Science - Columbia University (2018)"
    )

    res = score_resume_ats(structured, raw_text, job_required_skills=["Python", "PostgreSQL", "Docker", "Kubernetes"])

    assert res.overall_score >= 80
    assert res.breakdown.parseability >= 20.0
    assert len(res.matched_keywords) == 4
    assert len(res.missing_keywords) == 0


def test_student_resume_rebalancing():
    # Student profile: missing experience, but strong education and projects
    structured = StructuredResumeSchema(
        contact=ContactInfo(name="Bob Student", email="bob@university.edu", phone="555-999-0000"),
        summary="Computer Science senior passionate about backend software development.",
        skills=SkillsCategorized(technical=["Python", "C++", "SQL", "Git", "Linux", "Data Structures"]),
        experience=[],
        education=[
            EducationEntry(degree="Bachelor of Science in CS", institution="State University", graduation_date="2026")
        ],
        sections_detected=["contact", "education", "skills"],
        sections_missing=["experience"],
    )

    raw_text = (
        "Bob Student\n"
        "Email: bob@university.edu | Phone: 555-999-0000\n"
        "Summary: Computer Science senior passionate about backend software development.\n"
        "Skills: Python, C++, SQL, Git, Linux, Data Structures.\n"
        "Education: Bachelor of Science in CS, State University (2026)."
    )

    res = score_resume_ats(structured, raw_text)
    # Section completeness should be partially rebalanced (>= 7 out of 15) instead of 0
    assert res.breakdown.section_completeness >= 7.0


def test_gap_analysis_adjacent_skills():
    structured = StructuredResumeSchema(
        skills=SkillsCategorized(technical=["Vue.js", "PostgreSQL", "Python", "FastAPI"])
    )

    res = perform_skill_gap_analysis(structured, job_required_skills=["React", "MySQL", "Python"])

    assert "Python" in res.matched_skills
    adjacent_reqs = [a.required_skill for a in res.adjacent_skills]
    assert "React" in adjacent_reqs or "Mysql" in adjacent_reqs
