"""
Unit Tests for Phase 1 Text Extractor
"""

import pytest
from backend.services.text_extractor import (
    normalize_text_formatting,
    is_scanned_pdf_heuristic,
    extract_resume_text,
)


def test_normalize_text_formatting():
    raw = "John Doe’s Resume\n• Developed app using “Python” and   PostgreSQL.\n\xa0Page 1 of 2\n"
    cleaned = normalize_text_formatting(raw)

    assert "John Doe's Resume" in cleaned
    assert '- Developed app using "Python" and PostgreSQL.' in cleaned
    assert "Page 1 of 2" not in cleaned


def test_scanned_pdf_heuristic():
    # Short text < 50 words
    short_text = "Scan page 1 image context"
    assert is_scanned_pdf_heuristic(short_text) is True

    # High non-alphanumeric text
    garbage_text = "!@#$%^&*() _+~` " * 20
    assert is_scanned_pdf_heuristic(garbage_text) is True

    # Legitimate resume text
    valid_text = (
        "John Doe - Senior Software Engineer\n"
        "Email: john.doe@example.com | Phone: (555) 019-2831 | Location: San Francisco, CA\n"
        "Summary: Experienced software engineer with over 6 years of experience building scalable backend microservices and high-throughput data processing pipelines.\n"
        "Skills: Python, React, PostgreSQL, Docker, AWS, Kubernetes, FastAPI, Redis, Git, CI/CD.\n"
        "Work Experience:\n"
        "Senior Backend Engineer at TechCorp (2021 - Present)\n"
        "- Spearheaded the redesign of the core payment service, reducing API latencies by 35% and handling $4M in daily volume.\n"
        "- Managed a cross-functional team of 5 engineers to deliver microservices architecture on AWS EKS.\n"
        "Education: Bachelor of Science in Computer Science, Stanford University."
    )
    assert is_scanned_pdf_heuristic(valid_text) is False


def test_extract_resume_text_txt():
    content = (
        b"John Doe - Full Stack Software Engineer\n"
        b"Email: john@test.com | Phone: 555-019-2831 | Location: San Francisco, CA\n"
        b"Summary: Experienced software engineer with over 5 years of experience building scalable web applications and distributed systems.\n"
        b"Skills: Python, Docker, React, AWS, SQL, Kubernetes, FastAPI, Redis, Git, CI/CD pipelines.\n"
        b"Work Experience:\n"
        b"Software Engineer at CloudTech (2021 - Present)\n"
        b"- Built REST APIs and microservices, increasing user adoption by 40% across 5 production projects.\n"
        b"- Architected database schemas and optimized SQL queries to reduce latency by 25%.\n"
        b"Education: Bachelor of Science in Computer Science, University of California."
    )
    res = extract_resume_text(content, "resume.txt")

    assert res["extension"] == ".txt"
    assert res["word_count"] > 50
    assert len(res["content_hash"]) == 64
