from __future__ import annotations

import re
from typing import Dict, List, Optional

import spacy

from backend.services.pdf_parser import parse_resume_file, extract_experience_years

# 80 skills list (must match the one used in pdf_parser for consistent skill extraction)
SKILLS: List[str] = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "React",
    "Node.js",
    "Express",
    "Django",
    "Flask",
    "FastAPI",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "GraphQL",
    "REST",
    "Microservices",
    "AWS",
    "Google Cloud",
    "Azure",
    "Docker",
    "Kubernetes",
    "Linux",
    "Git",
    "CI/CD",
    "Jenkins",
    "Terraform",
    "Ansible",
    "Shell",
    "Pandas",
    "NumPy",
    "Scikit-learn",
    "XGBoost",
    "LightGBM",
    "PyTorch",
    "TensorFlow",
    "Transformers",
    "SpaCy",
    "NLP",
    "LLMs",
    "LangChain",
    "Groq",
    "Pinecone",
    "Vector Search",
    "ElasticSearch",
    "Kafka",
    "Spark",
    "Airflow",
    "Hadoop",
    "Databricks",
    "Data Engineering",
    "Data Modeling",
    "ETL",
    "BigQuery",
    "Snowflake",
    "Tableau",
    "Power BI",
    "Statistics",
    "Data Visualization",
    "System Design",
    "OOP",
    "Design Patterns",
    "Agile",
    "Scrum",
    "Unit Testing",
    "Test Automation",
    "Selenium",
    "Playwright",
    "C#",
    "C++",
    "Go",
    "Ruby",
    "PHP",
    "R",
    ".NET",
    ".NET Core",
    "ASP.NET",
    "ASP.NET Core",
    "Entity Framework",
    "Blazor",
    "MERN",
    "MERN Stack",
    "Next.js",
]


try:
    _NLP = spacy.load("en_core_web_sm")
except Exception:
    # If model isn't installed, load a blank pipeline to keep API functional.
    # Note: NER quality will degrade, but endpoints still work.
    _NLP = spacy.blank("en")


_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
_PHONE_RE = re.compile(r"(\+?\d{1,3}[\s-]?)?(\(?\d{3}\)?[\s-]?)\d{3}[\s-]?\d{4}")


def extract_skills_from_text(text: str) -> List[str]:
    """
    Extract skills from text by matching against a predefined skill list.
    Supports special aliases like .NET, dotnet, and MERN.

    Args:
        text: Resume text.

    Returns:
        List of matched skills (original casing from SKILLS).
    """
    lower = text.lower()
    matched: List[str] = []
    
    # Pre-check for special tokens / aliases
    has_dotnet = bool(re.search(r"(\.net|dotnet|\basp\.net)\b", lower))
    has_mern = bool(re.search(r"\bmern(\s+stack)?\b", lower))

    for skill in SKILLS:
        s_lower = skill.lower()
        if skill == ".NET":
            if has_dotnet and ".NET" not in matched:
                matched.append(".NET")
            continue
        if skill in ("MERN", "MERN Stack"):
            if has_mern and skill not in matched:
                matched.append(skill)
            continue
        if s_lower in lower:
            matched.append(skill)
    return matched


def _extract_experience_years(text: str) -> float:
    """
    Extract experience years from text while excluding age and DOB numbers.

    Returns:
        Parsed experience years, or 0.0.
    """
    return extract_experience_years(text)


def _extract_education_level(text: str) -> str:
    """
    Extract education level using lightweight regex.

    Returns:
        Education level string or "Unknown".
    """
    education_match = re.search(
        r"\b(Bachelor|B\.Tech|B\.Tech|M\.Tech|Master|Master's|PhD|Doctor|University|College)\b",
        text,
        flags=re.IGNORECASE,
    )
    return education_match.group(0) if education_match else "Unknown"


def extract_entities(text: str) -> Dict[str, object]:
    """
    Extract structured resume entities using spaCy NER with regex fallbacks.

    Extracts:
    - name, email, phone, skills
    - experience_years, education, location

    Args:
        text: Resume text.

    Returns:
        Structured dict of extracted fields.
    """
    cleaned = text or ""
    email = _EMAIL_RE.search(cleaned)
    phone = _PHONE_RE.search(cleaned)

    doc = _NLP(cleaned)

    name: Optional[str] = None
    location: Optional[str] = None
    skills_from_ner: List[str] = []

    for ent in doc.ents:
        if ent.label_ == "PERSON" and name is None:
            name = ent.text
        elif ent.label_ in {"GPE", "LOC"} and location is None:
            location = ent.text
        elif ent.label_ == "ORG":
            # Sometimes org entities appear near skills; keep as weak signal.
            continue

    skills = extract_skills_from_text(cleaned)
    # Ensure we still provide something even if spaCy name extraction fails:
    if name is None:
        first_line = cleaned.splitlines()[0].strip() if cleaned.splitlines() else ""
        name = first_line if first_line else "Unknown"

    experience_years = _extract_experience_years(cleaned)
    education = _extract_education_level(cleaned)

    return {
        "name": name or "Unknown",
        "email": email.group(0) if email else "Unknown",
        "phone": phone.group(0) if phone else "Unknown",
        "skills": skills,
        "experience_years": experience_years,
        "education": education,
        "location": location or "Unknown",
    }


def parse_resume_text_fallback(text: str) -> Dict[str, object]:
    """
    Compatibility helper to extract entities when PDF parsing already produced raw text.

    Args:
        text: Resume raw text.

    Returns:
        Structured dict compatible with extraction output.
    """
    return extract_entities(text)
