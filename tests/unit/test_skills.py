"""Unit tests for the shared token-boundary skill extractor (ml/skills.py)."""

from __future__ import annotations

import pytest

from ml.skills import (
    ALL_SKILLS,
    TECH_SKILLS,
    canonical_skill_set,
    canonicalize_skill,
    extract_skills,
    has_skill,
)


class TestShortAmbiguousSkills:
    @pytest.mark.parametrize("text", [
        "Responsible for marketing and partner relations",   # every word has an 'r'
        "Strong organizational skills; works under pressure",
        "R&D department, budget review",                      # R&D is not R
        "IQVIA R amp D Technologies",                         # html-cleaned R&D
        "Mr. R. Smith, Director",                             # initial
    ])
    def test_r_not_matched_without_context(self, text: str) -> None:
        assert "R" not in extract_skills(text)

    @pytest.mark.parametrize("text", [
        "Skills: Python, R, SQL",
        "Statistical modelling in R and SAS",
        "Built dashboards with RStudio and Shiny",
        "Languages | R | Julia",
    ])
    def test_r_matched_with_context(self, text: str) -> None:
        assert "R" in extract_skills(text)

    @pytest.mark.parametrize("text", [
        "We go above and beyond for our customers",
        "Go-to-market strategy and Go-live support",
        "Good communication, ongoing training, going forward",
        "Let's go!",
    ])
    def test_go_english_word_not_matched(self, text: str) -> None:
        assert "Go" not in extract_skills(text)

    @pytest.mark.parametrize("text", [
        "Backend services in Go and Python",
        "Experience with Golang microservices",
        "Languages: Java, Go, Rust",
    ])
    def test_go_language_matched(self, text: str) -> None:
        assert "Go" in extract_skills(text)

    @pytest.mark.parametrize("text", ["maintain the domain", "said paid detail", "chair"])
    def test_ai_not_substring(self, text: str) -> None:
        assert "AI" not in extract_skills(text)

    def test_ai_matched(self) -> None:
        assert "AI" in extract_skills("Building AI products and artificial intelligence tooling")
        assert "AI" in extract_skills("experience with artificial intelligence")

    def test_rust_trust(self) -> None:
        assert "Rust" not in extract_skills("Build trust with clients; prevent rust on equipment")
        assert "Rust" in extract_skills("Systems programming in Rust")

    def test_case_sensitive_english_words(self) -> None:
        text = "You will react quickly, excel at swift delivery and spark growth; shift hours"
        found = extract_skills(text)
        for s in ("React", "Excel", "Swift", "Spark", "HR"):
            assert s not in found

    def test_hr_vs_hours(self) -> None:
        assert "HR" not in extract_skills("Paid 40 hr per week, 24hr support")
        assert "HR" in extract_skills("HR generalist with payroll experience")
        assert "HR" in extract_skills("Human Resources business partner")


class TestTokenBoundaries:
    def test_java_vs_javascript(self) -> None:
        assert extract_skills("JavaScript developer") == ["JavaScript"]
        assert "Java" in extract_skills("Java and JavaScript")

    def test_symbols(self) -> None:
        found = extract_skills("C++ and C# developer with Node.js and CI/CD")
        for s in ("C++", "C#", "Node.js", "CI/CD"):
            assert s in found

    def test_sql_not_inside_mysql(self) -> None:
        found = extract_skills("MySQL and PostgreSQL")
        assert "MySQL" in found and "PostgreSQL" in found
        assert "SQL" not in found

    def test_git_github(self) -> None:
        assert "Git" in extract_skills("Code on GitHub")
        assert "Git" not in extract_skills("digital marketing")

    def test_empty_and_none(self) -> None:
        assert extract_skills("") == []
        assert extract_skills(None) == []  # type: ignore[arg-type]

    def test_vocab_order_and_dedup(self) -> None:
        out = extract_skills("Python python PYTHON and Docker")
        assert out.count("Python") == 1
        assert out.index("Python") < out.index("Docker")


class TestAliases:
    @pytest.mark.parametrize(("text", "canonical"), [
        ("JS and k8s", "JavaScript"),
        ("JS and k8s", "Kubernetes"),
        ("ML engineer", "Machine Learning"),
        ("postgres and mongo", "PostgreSQL"),
        ("sklearn pipelines", "Scikit-learn"),
        ("deployed on GCP", "Google Cloud"),
    ])
    def test_alias_in_text(self, text: str, canonical: str) -> None:
        assert canonical in extract_skills(text)

    def test_ml_not_milliliters(self) -> None:
        assert "Machine Learning" not in extract_skills("Add 5 ml of solution; HTML pages")

    @pytest.mark.parametrize(("raw", "canonical"), [
        ("js", "JavaScript"), ("JS", "JavaScript"), ("k8s", "Kubernetes"),
        ("ML", "Machine Learning"), ("golang", "Go"), ("ReactJS", "React"),
        ("node js", "Node.js"), ("+typescript", "TypeScript"), ("REST", "REST API"),
        ("SomeNewTool", "SomeNewTool"),
    ])
    def test_canonicalize(self, raw: str, canonical: str) -> None:
        assert canonicalize_skill(raw) == canonical

    def test_canonical_set_merges_aliases(self) -> None:
        a = canonical_skill_set(["JS", "k8s", "Python"])
        b = canonical_skill_set("JavaScript, Kubernetes, python")
        assert a == b == {"javascript", "kubernetes", "python"}

    def test_canonicalize_rejects_empty(self) -> None:
        assert canonicalize_skill("  ") is None
        assert canonicalize_skill(None) is None


def test_vocabularies() -> None:
    assert "REST" not in ALL_SKILLS and "REST API" in ALL_SKILLS
    assert set(TECH_SKILLS) - {"REST"} <= set(ALL_SKILLS)
    assert has_skill("Skills: Python, R", "R")


def test_backend_extractor_uses_shared_matcher() -> None:
    from backend.services.nlp_extractor import extract_skills_from_text
    out = extract_skills_from_text("Experienced engineer working on marketing for great growth")
    assert "R" not in out and "Go" not in out
    assert extract_skills_from_text("Python, Go, Docker") == ["Python", "Docker", "Go"]


def test_pair_features_use_canonical_overlap() -> None:
    from ml.feature_engineering import compute_pair_features
    resume = {"skills": ["JS", "k8s"], "raw_text": "Frontend engineer. Skills: React", "experience_years": 1,
              "education": "B.Tech", "location": ""}
    job = {"required_skills": ["JavaScript", "Kubernetes", "React"], "description": "",
           "title": "Frontend Engineer", "location": "Remote", "category": "INFORMATION-TECHNOLOGY",
           "experience_years": 0}
    f = compute_pair_features(resume, job, semantic_similarity=0.5, tfidf_similarity=0.1)
    assert f["skill_overlap_count"] == 3
    assert f["skill_overlap_ratio"] == 1.0
    assert f["education_score"] == 3
    assert f["location_match"] == 1
    assert f["is_entry_level_job"] == 1
