from __future__ import annotations

import re
from typing import Dict, List, Optional

import spacy

from backend.services.pdf_parser import parse_resume_file, extract_experience_years
from ml.skills import TECH_SKILLS, extract_skills as shared_extract_skills

# 80 skills list (same list as pdf_parser; lives in ml/skills.py, the single shared matcher)
SKILLS: List[str] = list(TECH_SKILLS)


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
    # Shared token-boundary extractor (ml/skills.py): "R" no longer matches every
    # word containing an r, "Go" no longer matches "good", aliases (JS, k8s, ...) map
    # to canonical names. Same matcher as the ML training data.
    return shared_extract_skills(text or "", SKILLS)


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


def _clean_candidate_name(raw_name: Optional[str], full_text: str) -> str:
    """Sanitize candidate name, filtering out URLs, pipes, emails, and phone numbers."""
    if raw_name:
        cleaned = re.sub(r"^[|\-•*–\s]+", "", raw_name).strip()
        cleaned = re.sub(r"[|\-•*–\s]+$", "", cleaned).strip()
        if not re.search(r"(\.com|\.in|\.org|@|linkedin|github|http|\+\d{2})", cleaned, re.I):
            if 2 <= len(cleaned) <= 35 and not any(char.isdigit() for char in cleaned):
                return cleaned.title()

    # Fallback: scan first 5 lines for a clean 2-3 word capitalized person name
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    for line in lines[:5]:
        tokens = re.split(r"[|/•\t]", line)
        for token in tokens:
            cand = token.strip()
            cand = re.sub(r"^[|\-•*–\s]+", "", cand).strip()
            if not cand or len(cand) < 3 or len(cand) > 35:
                continue
            if re.search(r"(\.com|\.in|\.org|@|linkedin|github|http|\+\d|\b(resume|curriculum|vitae|profile)\b)", cand, re.I):
                continue
            words = cand.split()
            if 1 <= len(words) <= 4 and all(w.isalpha() for w in words):
                return " ".join(words).title()

    return ""


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
            cleaned_ent = ent.text.strip()
            if not re.search(r"(\.com|\.in|linkedin|github|http|@)", cleaned_ent, re.I):
                name = cleaned_ent
        elif ent.label_ in {"GPE", "LOC"} and location is None:
            location = ent.text
        elif ent.label_ == "ORG":
            # Sometimes org entities appear near skills; keep as weak signal.
            continue

    skills = extract_skills_from_text(cleaned)
    final_name = _clean_candidate_name(name, cleaned)

    experience_years = _extract_experience_years(cleaned)
    education = _extract_education_level(cleaned)

    return {
        "name": final_name,
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
