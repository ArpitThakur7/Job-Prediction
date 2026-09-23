"""
Phase 3 — Enterprise ATS Scoring Engine - JOB-AI Platform
Calculates a 0–100 ATS compatibility score incorporating industry best practices:
1. Recency & Duration Skill Boosting (+15% for active roles <3 yrs, +10%/yr duration multiplier).
2. Configurable Role-Based Category Weight Matrices (Technical, Executive, General).
3. Field-Level Parse Confidence Auditing & Flagging (<75% triggers manual override prompt).
4. Detailed Issues Breakdown with Severity Ratings.
"""

from __future__ import annotations

import datetime
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.services.structured_extractor import StructuredResumeSchema
from backend.services.embedder import generate_embedding

logger = logging.getLogger("backend.services.ats_scorer")

ACTION_VERBS = {
    "achieved", "added", "allocated", "analyzed", "architected", "automated", "boosted",
    "built", "calculated", "championed", "created", "decreased", "delivered", "designed",
    "developed", "directed", "driven", "engineered", "established", "expanded", "executed",
    "generated", "grew", "implemented", "improved", "increased", "initiated", "integrated",
    "launched", "lead", "led", "managed", "maximized", "minimized", "negotiated", "optimized",
    "orchestrated", "overhauled", "pioneered", "reduced", "revamped", "scaled", "spearheaded",
    "streamlined", "transformed", "upgraded"
}

ROLE_WEIGHT_MATRICES = {
    "technical": {
        "skills": 0.50,
        "titles": 0.25,
        "experience": 0.15,
        "education": 0.10,
    },
    "executive": {
        "titles": 0.40,
        "skills": 0.30,
        "experience": 0.20,
        "education": 0.10,
    },
    "general": {
        "skills": 0.35,
        "experience": 0.25,
        "titles": 0.20,
        "education": 0.20,
    },
}


class ATSIssue(BaseModel):
    severity: str = "medium"  # high, medium, low
    category: str = ""        # parseability, keyword_match, section_completeness, content_quality, formatting
    message: str = ""


class ATSScoreBreakdown(BaseModel):
    parseability: float = 0.0         # Max 25 (or weighted)
    keyword_match: float = 0.0        # Max 30 (or weighted)
    section_completeness: float = 0.0 # Max 15 (or weighted)
    content_quality: float = 0.0      # Max 20 (or weighted)
    formatting: float = 0.0           # Max 10 (or weighted)
    recency_boost: float = 0.0        # Bonus points added for recent skill usage


class ATSScoreResult(BaseModel):
    overall_score: int = 0
    parse_confidence_score: float = 100.0
    role_type: str = "technical"
    breakdown: ATSScoreBreakdown = Field(default_factory=ATSScoreBreakdown)
    issues: List[ATSIssue] = Field(default_factory=list)
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    import math
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def _extract_years_from_date_range(start_str: str, end_str: str) -> float:
    """Helper to parse year durations from date strings like '2021', 'Present', 'Jan 2020'."""
    current_year = datetime.datetime.now().year
    
    def parse_year(s: str) -> int:
        if not s or "present" in s.lower() or "current" in s.lower():
            return current_year
        match = re.search(r"\b(20\d{2}|19\d{2})\b", s)
        return int(match.group(1)) if match else current_year

    start_yr = parse_year(start_str)
    end_yr = parse_year(end_str)
    duration = max(0.5, float(end_yr - start_yr + 1))
    return duration


def calculate_parse_confidence(structured: StructuredResumeSchema, raw_text: str) -> float:
    """
    Field-level precision score (0-100%) measuring parser confidence.
    Flags incomplete extractions for recruiter verification.
    """
    confidence = 100.0
    c = structured.contact

    if not c.name or len(c.name.strip()) < 3:
        confidence -= 20.0
    if not c.email or "@" not in c.email:
        confidence -= 25.0
    if not c.phone:
        confidence -= 15.0

    all_skills = structured.skills.technical + structured.skills.soft + structured.skills.tools
    if len(all_skills) == 0:
        confidence -= 20.0

    if len(structured.experience) == 0 and len(structured.education) == 0:
        confidence -= 20.0

    return max(0.0, min(100.0, confidence))


def score_resume_ats(
    structured: StructuredResumeSchema,
    raw_text: str,
    job_description: Optional[str] = None,
    job_required_skills: Optional[List[str]] = None,
    role_type: str = "technical",
) -> ATSScoreResult:
    """
    Calculate ATS compatibility score (0-100) with recency boosting, role-based category matrix,
    and parse confidence metric.
    """
    issues: List[ATSIssue] = []
    role_type = role_type.lower() if role_type.lower() in ROLE_WEIGHT_MATRICES else "technical"

    # 0. Calculate Parse Confidence Score
    confidence_score = calculate_parse_confidence(structured, raw_text)
    if confidence_score < 75.0:
        issues.append(
            ATSIssue(
                severity="high",
                category="parseability",
                message=f"Parser confidence is low ({confidence_score:.0f}%). Review extracted fields in recruiter edit mode to ensure critical skills and contact details are accurate.",
            )
        )

    # -------------------------------------------------------------------------
    # 1. PARSEABILITY (Base 25 pts)
    # -------------------------------------------------------------------------
    parseability_score = 25.0

    if re.search(r"(\|[ \t]*){2,}", raw_text) or re.search(r"(\t{2,})", raw_text):
        parseability_score -= 5.0
        issues.append(
            ATSIssue(
                severity="high",
                category="parseability",
                message="Resume appears to use multi-column tables or complex tab stops, which can cause ATS parsers to read text out of order.",
            )
        )

    detected = set(s.lower() for s in structured.sections_detected)
    if "experience" not in detected and "education" not in detected:
        parseability_score -= 8.0
        issues.append(
            ATSIssue(
                severity="high",
                category="parseability",
                message="Missing standard section headers (Work Experience / Education). Use clear standard headers so ATS bots recognize your sections.",
            )
        )

    if re.search(r"[^\x00-\x7F\u2013\u2014\u201C\u201D\u2018\u2019\u2022]", raw_text[:1000]):
        parseability_score -= 3.0
        issues.append(
            ATSIssue(
                severity="low",
                category="parseability",
                message="Non-standard characters or icon symbols detected. Stick to standard bullet points and fonts for max ATS parseability.",
            )
        )

    parseability_score = max(0.0, parseability_score)

    # -------------------------------------------------------------------------
    # 2. KEYWORD MATCH & RECENCY/DURATION BOOST (Base 30 pts)
    # -------------------------------------------------------------------------
    keyword_score = 30.0
    recency_boost_pts = 0.0
    matched_kw: List[str] = []
    missing_kw: List[str] = []

    all_candidate_skills = list(set(
        [s.lower().strip() for s in structured.skills.technical + structured.skills.soft + structured.skills.tools]
    ))

    # Recency & Duration analysis across work experience entries
    current_year = datetime.datetime.now().year
    embedded_skills_recency: Dict[str, float] = {}

    for exp in structured.experience:
        duration = _extract_years_from_date_range(exp.start_date, exp.end_date)
        exp_text = (exp.title + " " + exp.company + " " + " ".join(exp.bullets)).lower()
        
        # Check if experience is recent (<3 years ago)
        is_recent = ("present" in exp.end_date.lower() or "current" in exp.end_date.lower() or 
                     (re.search(r"\b20\d{2}\b", exp.end_date) and int(re.search(r"\b20\d{2}\b", exp.end_date).group(0)) >= current_year - 3))

        for skill in all_candidate_skills:
            if skill in exp_text:
                multiplier = 1.15 if is_recent else 1.0
                duration_factor = 1.0 + (min(duration, 5.0) * 0.10)
                embedded_skills_recency[skill] = max(embedded_skills_recency.get(skill, 1.0), multiplier * duration_factor)

    if job_required_skills and len(job_required_skills) > 0:
        req_set = set(s.lower().strip() for s in job_required_skills)
        matched_set = set(all_candidate_skills).intersection(req_set)
        missing_set = req_set - matched_set

        matched_kw = [s.title() for s in matched_set]
        missing_kw = [s.title() for s in missing_set]

        # Base match ratio
        raw_ratio = len(matched_set) / max(len(req_set), 1)
        keyword_score = raw_ratio * 30.0

        # Apply Recency & Duration multipliers for matched skills
        recency_bonus_total = 0.0
        for m_skill in matched_set:
            if m_skill in embedded_skills_recency:
                recency_bonus_total += (embedded_skills_recency[m_skill] - 1.0) * (30.0 / max(len(req_set), 1))

        recency_boost_pts = min(5.0, recency_bonus_total)
        keyword_score = min(30.0, keyword_score + recency_boost_pts)

        if len(missing_kw) > 0:
            issues.append(
                ATSIssue(
                    severity="high" if len(missing_kw) > 3 else "medium",
                    category="keyword_match",
                    message=f"Missing {len(missing_kw)} target job skills: {', '.join(missing_kw[:5])}.",
                )
            )
    elif job_description and len(job_description.strip()) > 30:
        res_vec = generate_embedding(raw_text[:2000])
        job_vec = generate_embedding(job_description[:2000])
        sim = _cosine_similarity(res_vec, job_vec)

        keyword_score = min(30.0, max(10.0, sim * 35.0))
        if sim < 0.50:
            issues.append(
                ATSIssue(
                    severity="medium",
                    category="keyword_match",
                    message="Semantic alignment with target job description is moderate. Incorporate specific technical keywords from the job post.",
                )
            )
    else:
        if len(all_candidate_skills) >= 8:
            keyword_score = 26.0
        elif len(all_candidate_skills) >= 4:
            keyword_score = 20.0
            issues.append(
                ATSIssue(
                    severity="medium",
                    category="keyword_match",
                    message="Consider adding more technical and tool skills to boost ATS keyword indexing density.",
                )
            )
        else:
            keyword_score = 12.0
            issues.append(
                ATSIssue(
                    severity="high",
                    category="keyword_match",
                    message="Very few technical skills extracted. Explicitly list core programming languages, frameworks, and tools.",
                )
            )

    keyword_score = max(0.0, min(30.0, keyword_score))

    # -------------------------------------------------------------------------
    # 3. SECTION COMPLETENESS (Base 15 pts)
    # -------------------------------------------------------------------------
    sec_score = 15.0
    c = structured.contact

    if not c.email or "@" not in c.email:
        sec_score -= 3.0
        issues.append(
            ATSIssue(severity="high", category="section_completeness", message="Missing valid contact email address.")
        )
    if not c.phone:
        sec_score -= 2.0
        issues.append(
            ATSIssue(severity="medium", category="section_completeness", message="Missing phone contact number.")
        )
    if not structured.summary or len(structured.summary.strip()) < 20:
        sec_score -= 2.0
        issues.append(
            ATSIssue(severity="low", category="section_completeness", message="Adding a concise professional summary helps recruiters grasp your value proposition quickly.")
        )

    has_experience = len(structured.experience) > 0 and any(len(e.bullets) > 0 for e in structured.experience)
    has_education = len(structured.education) > 0

    if not has_experience:
        if has_education and (len(all_candidate_skills) >= 5 or len(structured.certifications) > 0):
            sec_score -= 2.0
            issues.append(
                ATSIssue(
                    severity="medium",
                    category="section_completeness",
                    message="No formal work experience detected. Emphasize academic projects, open-source contributions, and certifications.",
                )
            )
        else:
            sec_score -= 5.0
            issues.append(
                ATSIssue(severity="high", category="section_completeness", message="No work experience section found.")
            )

    sec_score = max(0.0, sec_score)

    # -------------------------------------------------------------------------
    # 4. CONTENT QUALITY & VERB STRENGTH (Base 20 pts)
    # -------------------------------------------------------------------------
    content_score = 20.0
    all_bullets = []
    quantified_bullets_count = 0

    for exp in structured.experience:
        for b in exp.bullets:
            all_bullets.append(b)
            if exp.has_quantified_impact or re.search(r"(\d+%\s*|\$\s*\d+|\b\d{2,}\b|\b\d+\.\d+\b)", b):
                quantified_bullets_count += 1

    total_bullets = len(all_bullets)
    if total_bullets > 0:
        quant_ratio = quantified_bullets_count / total_bullets
        if quant_ratio < 0.40:
            penalty = (0.40 - quant_ratio) * 15.0
            content_score -= penalty
            unquantified = total_bullets - quantified_bullets_count
            issues.append(
                ATSIssue(
                    severity="high" if quant_ratio < 0.20 else "medium",
                    category="content_quality",
                    message=f"{unquantified} of {total_bullets} experience bullets lack measurable business outcomes (percentages, metrics, dollar amounts).",
                )
            )

        action_verb_count = 0
        for b in all_bullets:
            first_word = b.strip().split()[0].lower() if b.strip() else ""
            cleaned_word = re.sub(r"[^a-z]", "", first_word)
            if cleaned_word in ACTION_VERBS or cleaned_word.endswith("ed"):
                action_verb_count += 1

        verb_ratio = action_verb_count / total_bullets
        if verb_ratio < 0.50:
            content_score -= 3.0
            issues.append(
                ATSIssue(
                    severity="medium",
                    category="content_quality",
                    message="Use strong, active verbs (e.g., 'Engineered', 'Optimized', 'Spearheaded') at the beginning of bullet points rather than passive phrases.",
                )
            )

    words_count = len(raw_text.split())
    if words_count < 300:
        content_score -= 4.0
        issues.append(
            ATSIssue(
                severity="high",
                category="content_quality",
                message=f"Resume length is very short ({words_count} words). Aim for 400-800 words to adequately detail your accomplishments.",
            )
        )
    elif words_count > 950:
        content_score -= 3.0
        issues.append(
            ATSIssue(
                severity="medium",
                category="content_quality",
                message=f"Resume is lengthy ({words_count} words). Streamline content to 1-2 pages (~500-800 words).",
            )
        )

    content_score = max(0.0, content_score)

    # -------------------------------------------------------------------------
    # 5. FORMATTING HYGIENE (Base 10 pts)
    # -------------------------------------------------------------------------
    fmt_score = 10.0

    if c.email and not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", c.email.strip()):
        fmt_score -= 3.0
        issues.append(
            ATSIssue(severity="medium", category="formatting", message="Email address format appears invalid or contains extra spaces.")
        )

    if re.search(r"\b(\w+)\s+\1\b", raw_text, flags=re.IGNORECASE):
        fmt_score -= 2.0
        issues.append(
            ATSIssue(severity="low", category="formatting", message="Repeated duplicate words detected in text (e.g. 'the the').")
        )

    fmt_score = max(0.0, fmt_score)

    # -------------------------------------------------------------------------
    # ROLE-BASED WEIGHT MATRIX RE-CALCULATION
    # -------------------------------------------------------------------------
    # Base scores out of 100:
    # parseability (25 max), keyword (30 max), sec (15 max), content (20 max), fmt (10 max)
    # Weight matrices re-scale category relative weights per role requirements
    matrix = ROLE_WEIGHT_MATRICES.get(role_type, ROLE_WEIGHT_MATRICES["technical"])
    
    # Scale components
    skill_comp = (keyword_score / 30.0) * (matrix.get("skills", 0.35) * 100)
    exp_comp = (content_score / 20.0) * (matrix.get("experience", 0.25) * 100)
    title_comp = (parseability_score / 25.0) * (matrix.get("titles", 0.20) * 100)
    edu_comp = (sec_score / 15.0) * (matrix.get("education", 0.20) * 100)
    
    weighted_total = skill_comp + exp_comp + title_comp + edu_comp
    overall = int(round(weighted_total))
    overall = max(0, min(100, overall))

    return ATSScoreResult(
        overall_score=overall,
        parse_confidence_score=round(confidence_score, 1),
        role_type=role_type,
        breakdown=ATSScoreBreakdown(
            parseability=round(parseability_score, 1),
            keyword_match=round(keyword_score, 1),
            section_completeness=round(sec_score, 1),
            content_quality=round(content_score, 1),
            formatting=round(fmt_score, 1),
            recency_boost=round(recency_boost_pts, 1),
        ),
        issues=issues,
        matched_keywords=matched_kw,
        missing_keywords=missing_kw,
    )
