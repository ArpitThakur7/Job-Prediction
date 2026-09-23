from __future__ import annotations

import re
from typing import Any, Dict

import io
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


def extract_experience_years(text: str) -> float:
    """
    Extract work experience years from text, ensuring candidate's age or date-of-birth
    is NOT misclassified as work experience.

    Returns:
        Parsed experience years (float), or 0.0.
    """
    if not text or not isinstance(text, str):
        return 0.0

    # Step 1: Pre-clean text by removing explicit age and DOB patterns
    text_clean = re.sub(
        r"(?i)\b(?:age|dob|date\s+of\s+birth|born)\s*[:=\-]?\s*\d+\s*(?:years?|yrs?)?\s*(?:old|of\s+age)?\b",
        " ",
        text
    )
    text_clean = re.sub(
        r"(?i)\b\d+\s*(?:years?|yrs?)\s*(?:old|of\s+age)\b",
        " ",
        text_clean
    )

    # Step 2: High-confidence explicit experience patterns
    exp_patterns = [
        r"(?i)\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:work\s+|professional\s+|relevant\s+|hands-on\s+)?experience\b",
        r"(?i)\b(?:work\s+|total\s+|overall\s+|relevant\s+)?experience\s*[:=\-]?\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
        r"(?i)\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:in|with|as|of)\s+[A-Za-z0-9#\+\.\s]{2,25}\b",
    ]

    for pattern in exp_patterns:
        match = re.search(pattern, text_clean)
        if match:
            try:
                val = float(match.group(1))
                if 0.0 <= val <= 45.0:
                    return round(val, 1)
            except (ValueError, IndexError):
                pass

    # Step 3: Date range fallback in Work Experience section
    current_year = 2026
    year_ranges = re.findall(
        r"\b(20[0-9]{2}|19[9][0-9])\s*(?:-|–|to)\s*(20[0-9]{2}|present|current|now)\b",
        text_clean,
        flags=re.IGNORECASE,
    )
    if year_ranges:
        total_months = 0
        for start_str, end_str in year_ranges:
            start_yr = int(start_str)
            if end_str.lower() in {"present", "current", "now"}:
                end_yr = current_year
            else:
                end_yr = int(end_str)
            if end_yr >= start_yr:
                total_months += (end_yr - start_yr) * 12
        calculated_years = round(total_months / 12.0, 1)
        if 0.0 < calculated_years <= 45.0:
            return calculated_years

    # Step 4: Strict fallback - ONLY match "X years" if value < 18 (unlikely to be age)
    match_fallback = re.search(
        r"(?i)\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
        text_clean,
    )
    if match_fallback:
        val = float(match_fallback.group(1))
        if 0.0 < val < 18.0:
            return round(val, 1)

    return 0.0


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

    matched_skills = []
    lower_text = text.lower()
    has_dotnet = bool(re.search(r"(\.net|dotnet|\basp\.net)\b", lower_text))
    has_mern = bool(re.search(r"\bmern(\s+stack)?\b", lower_text))

    for s in skills_list:
        if s == ".NET":
            if has_dotnet and ".NET" not in matched_skills:
                matched_skills.append(".NET")
            continue
        if s in ("MERN", "MERN Stack"):
            if has_mern and s not in matched_skills:
                matched_skills.append(s)
            continue
        if s.lower() in lower_text:
            matched_skills.append(s)

    experience_years = extract_experience_years(text)

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

