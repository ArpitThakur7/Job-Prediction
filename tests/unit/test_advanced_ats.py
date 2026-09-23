"""
Unit Tests for Enterprise ATS Engine Features:
- Recency Skill Boosting
- Role-Based Weight Matrices
- Parse Confidence Calculation
"""

import pytest
from backend.services.structured_extractor import (
    StructuredResumeSchema,
    ContactInfo,
    SkillsCategorized,
    ExperienceEntry,
    EducationEntry,
)
from backend.services.ats_scorer import score_resume_ats, calculate_parse_confidence


def test_recency_skill_boost():
    # Candidate with Python in an active/recent role (2023-Present)
    recent_resume = StructuredResumeSchema(
        contact=ContactInfo(name="Jane Doe", email="jane@example.com", phone="555-000-1111"),
        skills=SkillsCategorized(technical=["Python", "FastAPI", "Docker"]),
        experience=[
            ExperienceEntry(
                title="Backend Developer",
                company="Tech Co",
                start_date="2023",
                end_date="Present",
                bullets=["Developed Python FastAPI microservices handling 1M daily requests."],
                has_quantified_impact=True,
            )
        ],
        education=[EducationEntry(degree="BS Computer Science")],
        sections_detected=["contact", "experience", "education", "skills"],
    )

    raw_text = "Jane Doe | email: jane@example.com | phone: 555-000-1111\nBackend Developer at Tech Co (2023 - Present)\nDeveloped Python FastAPI microservices handling 1M daily requests.\nSkills: Python, FastAPI, Docker"

    res = score_resume_ats(recent_resume, raw_text, job_required_skills=["Python", "FastAPI", "Docker"])

    assert res.breakdown.recency_boost > 0.0
    assert res.overall_score >= 80


def test_role_based_weight_matrix():
    structured = StructuredResumeSchema(
        contact=ContactInfo(name="Alex Leader", email="alex@company.com", phone="555-222-3333"),
        skills=SkillsCategorized(technical=["Python", "SQL", "Agile", "Roadmapping"]),
        experience=[
            ExperienceEntry(
                title="VP of Engineering",
                company="Enterprise Systems",
                start_date="2018",
                end_date="Present",
                bullets=["Led engineering division of 45 software developers across 4 product teams."],
                has_quantified_impact=True,
            )
        ],
        education=[EducationEntry(degree="MBA")],
        sections_detected=["contact", "experience", "education", "skills"],
    )

    raw_text = "Alex Leader\nVP of Engineering at Enterprise Systems (2018 - Present)\nLed engineering division of 45 software developers.\nEmail: alex@company.com | Phone: 555-222-3333"

    tech_score = score_resume_ats(structured, raw_text, role_type="technical")
    exec_score = score_resume_ats(structured, raw_text, role_type="executive")

    assert tech_score.role_type == "technical"
    assert exec_score.role_type == "executive"


def test_calculate_parse_confidence():
    # Complete resume -> High confidence
    good_resume = StructuredResumeSchema(
        contact=ContactInfo(name="John Alex", email="john@domain.com", phone="555-123-4567"),
        skills=SkillsCategorized(technical=["Python", "SQL"]),
        experience=[ExperienceEntry(title="Dev")],
        education=[EducationEntry(degree="BS")],
    )
    assert calculate_parse_confidence(good_resume, "John Alex john@domain.com 555-123-4567") >= 80.0

    # Incomplete candidate -> Low confidence
    empty_resume = StructuredResumeSchema(
        contact=ContactInfo(name="", email="", phone=""),
        skills=SkillsCategorized(),
        experience=[],
        education=[],
    )
    assert calculate_parse_confidence(empty_resume, "Short text") < 50.0
