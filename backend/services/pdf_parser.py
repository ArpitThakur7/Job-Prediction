from __future__ import annotations

import re
from typing import Any, Dict

import pdfplumber


def _clean_text(text: str) -> str:
    """
    Clean extracted text by normalizing whitespace.

    Args:
        text: Raw text.

    Returns:
        Cleaned text.
    """
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n", text)
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract and clean text from a multi-page PDF.

    Args:
        file_bytes: PDF bytes.

    Returns:
        Cleaned extracted text.
    """
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages = []
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)
        return _clean_text("\n".join(pages))


def parse_resume_file(file_bytes: bytes) -> Dict[str, Any]:
    """
    Parse a PDF resume into structured fields.

    Extraction includes:
    - email, phone
    - name from first line
    - skills (from an 80-skill list)
    - experience_years
    - education level

    Args:
        file_bytes: PDF bytes.

    Returns:
        Dict with resume fields.
    """
    text = extract_text_from_pdf(file_bytes)

    email_match = re.search(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", text)
    phone_match = re.search(
        r"(\+?\d{1,3}[\s-]?)?(\(?\d{3}\)?[\s-]?)\d{3}[\s-]?\d{4}", text
    )

    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    name = first_line if first_line else "Unknown"

    # Same 80-skills list as prior project (consolidated here)
    skills_list = [
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
    ]

    matched_skills = []
    lower_text = text.lower()
    for s in skills_list:
        if s.lower() in lower_text:
            matched_skills.append(s)

    exp_match = re.search(
        r"(\b\d+(\.\d+)?\b)\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience)?",
        text,
        flags=re.IGNORECASE,
    )
    experience_years = float(exp_match.group(1)) if exp_match else 0.0

    education_match = re.search(
        r"\b(Bachelor|B.Tech|B\.Tech|M\.Tech|Master|Master's|PhD|Doctor|University|College)\b",
        text,
        flags=re.IGNORECASE,
    )
    education = education_match.group(0) if education_match else "Unknown"

    # Phone/email cleanup
    email = email_match.group(0) if email_match else "Unknown"
    phone = phone_match.group(0) if phone_match else "Unknown"

    category = "unknown"

    return {
        "candidate_name": name,
        "email": email,
        "phone": phone,
        "skills": matched_skills,
        "experience_years": experience_years,
        "education": education,
        "category": category,
    }
