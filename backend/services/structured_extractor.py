"""
Phase 2 — Structured Extraction (Groq Llama 3.3 70B & Fallback) - JOB-AI Platform
Extracts structured JSON resume attributes matching strict Pydantic schemas.
Calculates bullet quantification and detects present vs missing standard sections.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.config import settings
from backend.services.nlp_extractor import parse_resume_text_fallback

logger = logging.getLogger("backend.services.structured_extractor")


class ContactInfo(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""


class SkillsCategorized(BaseModel):
    technical: List[str] = Field(default_factory=list)
    soft: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: List[str] = Field(default_factory=list)
    has_quantified_impact: bool = False


class EducationEntry(BaseModel):
    degree: str = ""
    institution: str = ""
    graduation_date: str = ""
    gpa: str = ""


class StructuredResumeSchema(BaseModel):
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: str = ""
    skills: SkillsCategorized = Field(default_factory=SkillsCategorized)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    sections_detected: List[str] = Field(default_factory=list)
    sections_missing: List[str] = Field(default_factory=list)


SYSTEM_EXTRACTION_PROMPT = """You are an expert ATS (Applicant Tracking System) parser.
Extract structured JSON from the candidate's resume text below.

STRICT REQUIREMENTS:
1. Return ONLY a valid JSON object matching the EXACT JSON schema provided. No markdown code blocks, no preamble, no explanation.
2. Evaluate each work experience bullet for 'has_quantified_impact': set to TRUE if the bullet contains numbers, percentages, dollar amounts, metrics, or measurable business outcomes (e.g. 'boosted revenue by 25%'); set to FALSE if purely descriptive.
3. Detect which standard resume sections exist in the text vs missing. Standard sections: ["contact", "summary", "experience", "education", "skills", "certifications"].

EXPECTED JSON SCHEMA:
{
  "contact": { "name": "", "email": "", "phone": "", "location": "", "linkedin": "" },
  "summary": "",
  "skills": { "technical": [], "soft": [], "tools": [] },
  "experience": [
    {
      "title": "", "company": "", "location": "", "start_date": "", "end_date": "",
      "bullets": [""], "has_quantified_impact": false
    }
  ],
  "education": [
    { "degree": "", "institution": "", "graduation_date": "", "gpa": "" }
  ],
  "certifications": [],
  "sections_detected": ["contact", "experience", "education", "skills"],
  "sections_missing": ["summary", "certifications"]
}
"""


def _clean_llm_json_response(raw_response: str) -> str:
    """Strip markdown code fences and extraneous text surrounding JSON."""
    text = raw_response.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # Find first { and last }
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return text[start_idx : end_idx + 1]
    return text


def _evaluate_bullet_quantification(bullet: str) -> bool:
    """Rule-based check if bullet contains metrics/numbers/percents."""
    if not bullet:
        return False
    # Check for percentage, currency, or numerical patterns
    pattern = r"(\d+%\s*|\$\s*\d+|\b\d{2,}\b|\b\d+\.\d+\b|\b(?:increased|decreased|boosted|grew|reduced|improved|saved)\b.*?\b\d+)"
    return bool(re.search(pattern, bullet, flags=re.IGNORECASE))


def extract_structured_resume_fallback(raw_text: str) -> StructuredResumeSchema:
    """
    Rule-based deterministic extraction when LLM API is unavailable.
    Uses regex + NLP entity parsing.
    """
    logger.info("Executing rule-based deterministic fallback structured extraction.")
    nlp_data = parse_resume_text_fallback(raw_text)

    contact = ContactInfo(
        name=str(nlp_data.get("name") or nlp_data.get("candidate_name") or ""),
        email=str(nlp_data.get("email") or ""),
        phone=str(nlp_data.get("phone") or ""),
        location=str(nlp_data.get("location") or ""),
        linkedin="",
    )

    all_skills = [str(s) for s in (nlp_data.get("skills") or [])]
    skills = SkillsCategorized(
        technical=all_skills,
        soft=["Communication", "Problem Solving", "Teamwork"],
        tools=["Git", "VS Code", "Docker"] if any(s.lower() in ["docker", "python", "java", "react"] for s in all_skills) else [],
    )

    # Extract bullet points from text
    lines = raw_text.splitlines()
    bullets = [line.strip("-*• ").strip() for line in lines if line.strip().startswith(("-", "*", "•")) and len(line.strip()) > 10]
    if not bullets:
        bullets = [line.strip() for line in lines if len(line.strip()) > 25 and not line.strip().endswith(":")][:6]

    has_impact = any(_evaluate_bullet_quantification(b) for b in bullets)

    exp_entry = ExperienceEntry(
        title=str(nlp_data.get("category") or "Professional Role").title(),
        company="Extracted Experience",
        location=contact.location,
        start_date="Recent",
        end_date="Present",
        bullets=bullets[:6],
        has_quantified_impact=has_impact,
    )

    edu_entry = EducationEntry(
        degree=str(nlp_data.get("education") or "Bachelor's Degree"),
        institution="University / Institute",
        graduation_date="Completed",
    )

    # Detect sections present in raw text
    text_lower = raw_text.lower()
    detected = []
    missing = []

    sections_map = {
        "contact": ["email", "phone", "@", "linkedin", "contact"],
        "summary": ["summary", "objective", "profile", "about me"],
        "experience": ["experience", "employment", "history", "work", "projects"],
        "education": ["education", "degree", "university", "college", "gpa"],
        "skills": ["skills", "technologies", "competencies", "tools"],
        "certifications": ["certification", "certified", "credentials", "licenses"],
    }

    for sec, keywords in sections_map.items():
        if any(kw in text_lower for kw in keywords):
            detected.append(sec)
        else:
            missing.append(sec)

    return StructuredResumeSchema(
        contact=contact,
        summary=raw_text[:300] + "..." if len(raw_text) > 300 else raw_text,
        skills=skills,
        experience=[exp_entry] if bullets else [],
        education=[edu_entry],
        certifications=[],
        sections_detected=detected,
        sections_missing=missing,
    )


def extract_structured_resume(
    raw_text: str,
    groq_api_key: Optional[str] = None,
) -> StructuredResumeSchema:
    """
    Phase 2 Structured Extraction using Groq (Llama 3.3 70B / Llama 3.1 8B).
    Validates output with Pydantic schema and retries on failure before falling back.
    """
    key = groq_api_key or settings.GROQ_API_KEY

    if not key or len(key.strip()) < 10:
        return extract_structured_resume_fallback(raw_text)

    try:
        from langchain_groq import ChatGroq

        llm = ChatGroq(
            api_key=key,
            model="llama-3.3-70b-versatile" if "70b" in key else "llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=2048,
        )

        user_prompt = f"Resume Text:\n\n{raw_text[:6000]}"

        # Attempt 1
        res = llm.invoke([("system", SYSTEM_EXTRACTION_PROMPT), ("human", user_prompt)])
        cleaned = _clean_llm_json_response(res.content if hasattr(res, "content") else str(res))

        try:
            parsed_dict = json.loads(cleaned)
            return StructuredResumeSchema(**parsed_dict)
        except Exception as parse_err:
            logger.warning("Groq structured parse attempt 1 failed (%s). Retrying with strict prompt...", parse_err)

        # Retry Attempt 2 with strict reminder
        retry_prompt = f"CRITICAL: The previous output failed JSON validation. Output strictly valid JSON matching schema only.\n\nResume Text:\n{raw_text[:6000]}"
        res2 = llm.invoke([("system", SYSTEM_EXTRACTION_PROMPT), ("human", retry_prompt)])
        cleaned2 = _clean_llm_json_response(res2.content if hasattr(res2, "content") else str(res2))
        parsed_dict2 = json.loads(cleaned2)
        return StructuredResumeSchema(**parsed_dict2)

    except Exception as exc:
        logger.warning("Groq structured extraction failed (%s). Triggering rule-based fallback parser.", exc)
        return extract_structured_resume_fallback(raw_text)
