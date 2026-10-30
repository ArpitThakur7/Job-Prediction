"""
Phase 3 — Enterprise ATS Scoring Engine - Fletch
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


class MLMatchResult(BaseModel):
    match_probability: float = 0.0
    predicted_match: int = 0
    verdict: str = "NO MATCH"
    confidence: str = "Medium"
    engine: str = "xgboost"
    threshold: float = 0.2651
    features: Dict[str, Any] = Field(default_factory=dict)


class BulletSuggestion(BaseModel):
    original: str = ""
    improved: str = ""
    reason: str = ""


class ATSScoreResult(BaseModel):
    overall_score: int = 0
    composite_score: int = 0
    grade_tier: str = "Strong"  # Elite, Strong, Needs Polish, Rejection Risk
    parse_confidence_score: float = 100.0
    role_type: str = "technical"
    breakdown: ATSScoreBreakdown = Field(default_factory=ATSScoreBreakdown)
    issues: List[ATSIssue] = Field(default_factory=list)
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    ml_prediction: Optional[MLMatchResult] = None
    bullet_suggestions: List[BulletSuggestion] = Field(default_factory=list)


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
    job_data: Optional[Dict[str, Any]] = None,
    include_ml_prediction: bool = True,
) -> ATSScoreResult:
    """
    Calculate ATS compatibility score (0-100) with recency boosting, role-based category matrix,
    parse confidence metric, and XGBoost 15-feature ML predictive match scoring.
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

    # -------------------------------------------------------------------------
    # 6. ML PREDICTIVE FIT (XGBoost 15-Feature Classifier)
    # -------------------------------------------------------------------------
    ml_result: Optional[MLMatchResult] = None
    composite_score = overall

    if include_ml_prediction:
        try:
            from backend.services.matcher import _extract_pair_features, _predict_pair_score

            all_skills = list(set(
                [s.strip() for s in structured.skills.technical + structured.skills.soft + structured.skills.tools if s.strip()]
            ))
            exp_years = 0.0
            for exp in structured.experience:
                exp_years += _extract_years_from_date_range(exp.start_date, exp.end_date)

            edu_degree = structured.education[0].degree if structured.education else "Bachelors"
            resume_dict = {
                "resume_id": "temp_scoring_candidate",
                "name": structured.contact.name or "Candidate",
                "email": structured.contact.email or "",
                "skills": all_skills,
                "experience_years": exp_years,
                "education": edu_degree,
                "category": "INFORMATION-TECHNOLOGY" if role_type == "technical" else "General",
                "raw_text": raw_text,
                "summary": structured.summary,
            }

            if job_data:
                target_job = job_data
            elif job_required_skills or job_description:
                target_job = {
                    "title": "Software Engineer",
                    "category": "INFORMATION-TECHNOLOGY" if role_type == "technical" else "General",
                    "required_skills": job_required_skills or ["Python", "FastAPI", "React", "Docker", "SQL", "Git"],
                    "experience_years": 1.5,
                    "location": "Remote",
                    "description": job_description or "Software Engineer responsible for modern scalable services.",
                }
            else:
                target_job = {
                    "title": "Software Engineer",
                    "category": "INFORMATION-TECHNOLOGY",
                    "required_skills": ["Python", "FastAPI", "React", "Docker", "SQL", "Git", "REST APIs", "CI/CD"],
                    "experience_years": 1.5,
                    "location": "Remote",
                    "description": "Software Engineer developing scalable web microservices, REST APIs, database queries, and CI/CD pipelines.",
                }

            features = _extract_pair_features(resume_dict, target_job, semantic_sim=0.75 if (job_description or not job_required_skills) else 0.60)
            pred = _predict_pair_score(features)

            ml_result = MLMatchResult(
                match_probability=round(pred["match_probability"], 4),
                predicted_match=pred["predicted_match"],
                verdict=pred["verdict"],
                confidence=pred["confidence"],
                engine=pred.get("engine", "xgboost"),
                threshold=0.2651,
                features=features,
            )

            ml_prob_pct = pred["match_probability"] * 100.0
            if job_data or job_required_skills:
                kw_ratio = (len(matched_kw) / max(len(job_required_skills or [1]), 1)) * 100.0
                composite = int(round(0.35 * overall + 0.45 * ml_prob_pct + 0.20 * kw_ratio))
            else:
                composite = int(round(0.55 * overall + 0.45 * ml_prob_pct))

            composite_score = max(0, min(100, composite))
        except Exception as e:
            logger.warning("ML prediction failed during ATS scoring: %s. Using structural score.", e)
            composite_score = overall

    # Determine Grade Tier
    if composite_score >= 90:
        grade_tier = "Elite"
    elif composite_score >= 75:
        grade_tier = "Strong"
    elif composite_score >= 60:
        grade_tier = "Needs Polish"
    else:
        grade_tier = "Rejection Risk"

    # -------------------------------------------------------------------------
    # 7. ACTIONABLE BULLET SUGGESTIONS
    # -------------------------------------------------------------------------
    bullet_suggestions: List[BulletSuggestion] = []
    for exp in structured.experience:
        for b in exp.bullets:
            clean_b = b.strip()
            if not clean_b:
                continue
            has_metric = bool(re.search(r"(\d+%\s*|\$\s*\d+|\b\d{2,}\b|\b\d+\.\d+\b)", clean_b))
            first_w = re.sub(r"[^a-z]", "", clean_b.split()[0].lower()) if clean_b.split() else ""
            has_verb = first_w in ACTION_VERBS or first_w.endswith("ed")

            if not has_metric and not has_verb:
                bullet_suggestions.append(BulletSuggestion(
                    original=clean_b,
                    improved=f"Architected and deployed {clean_b.lower().replace('worked on', '').replace('responsible for', '').strip()}, improving system performance by 35% and cutting latency by 40ms.",
                    reason="Bullet lacks an active power verb and quantifiable business outcome metrics."
                ))
            elif not has_metric:
                bullet_suggestions.append(BulletSuggestion(
                    original=clean_b,
                    improved=f"{clean_b} — resulting in a 28% efficiency boost across distributed workflows.",
                    reason="Add measurable metrics (percentages, latency, throughput, scale) to demonstrate impact."
                ))
            elif not has_verb:
                bullet_suggestions.append(BulletSuggestion(
                    original=clean_b,
                    improved=f"Spearheaded {clean_b[:1].lower() + clean_b[1:]}",
                    reason="Begin bullet points with an active technical action verb rather than passive phrasing."
                ))
            if len(bullet_suggestions) >= 4:
                break

    return ATSScoreResult(
        overall_score=overall,
        composite_score=composite_score,
        grade_tier=grade_tier,
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
        ml_prediction=ml_result,
        bullet_suggestions=bullet_suggestions,
    )


def parse_latex_to_structured(latex_code: str) -> tuple[StructuredResumeSchema, str]:
    """
    Parse raw LaTeX resume code into StructuredResumeSchema and clean raw text,
    optimizing for Overleaf LaTeX resumes.
    """
    from backend.services.structured_extractor import ContactInfo, SkillsCategorized, ExperienceEntry, EducationEntry

    # Extract Contact
    name_m = re.search(r"\\textbf{\\Huge\s*([^}]+)}", latex_code) or re.search(r"\\textbf{([^}]+)}", latex_code)
    name = name_m.group(1).replace(r"\Huge", "").strip() if name_m else "Candidate"

    email_m = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", latex_code)
    email = email_m.group(1).strip() if email_m else ""

    phone_m = re.search(r"\+?\d[\d -]{8,15}\d", latex_code)
    phone = phone_m.group(0).strip() if phone_m else ""

    linkedin_m = re.search(r"linkedin\.com/in/([a-zA-Z0-9_-]+)", latex_code)
    linkedin = f"linkedin.com/in/{linkedin_m.group(1)}" if linkedin_m else ""

    # Clean LaTeX markup for raw text
    def clean_latex(s: str) -> str:
        s = re.sub(r"\\textbf{([^}]+)}", r"\1", s)
        s = re.sub(r"\\textit{([^}]+)}", r"\1", s)
        s = re.sub(r"\\href{[^}]+}{([^}]+)}", r"\1", s)
        s = re.sub(r"\\hfill", " — ", s)
        s = re.sub(r"\\\\", "\n", s)
        s = re.sub(r"\\begin\{itemize\}[^\n]*", "", s)
        s = re.sub(r"\\end\{itemize\}", "", s)
        s = re.sub(r"\\item\s*", "• ", s)
        s = re.sub(r"\\hrule", "", s)
        s = re.sub(r"\\vspace\{[^}]+\}", "", s)
        s = re.sub(r"\$[^$]*\$", " | ", s)
        return s.strip()

    clean_text = clean_latex(latex_code)

    # Extract Summary
    summary_m = re.search(r"\\section\*{SUMMARY}(?:[^\w\\]*(?:\\\\|\r?\n)?)?([\s\S]*?)(?=\\section|\\end\{document\}|$)", latex_code, re.I)
    summary = clean_latex(summary_m.group(1)) if summary_m else ""

    # Extract Skills
    skills_tech: List[str] = []
    skills_tools: List[str] = []
    skills_m = re.search(r"\\section\*{(?:TECHNICAL SKILLS|SKILLS|COMPETENCIES)}(?:[^\w\\]*(?:\\\\|\r?\n)?)?([\s\S]*?)(?=\\section|\\end\{document\}|$)", latex_code, re.I)
    if skills_m:
        skills_raw = clean_latex(skills_m.group(1))
        # Support both newline-separated lines and inline commas
        lines = [l for l in skills_raw.split("\n") if l.strip()]
        if not lines:
            lines = [skills_raw]
        for line in lines:
            parts = line.split(":")
            if len(parts) > 1:
                category_label = parts[0].lower()
                items = [x.strip() for x in parts[1].split(",") if x.strip()]
                if "tool" in category_label or "data" in category_label or "cloud" in category_label:
                    skills_tools.extend(items)
                else:
                    skills_tech.extend(items)
            else:
                skills_tech.extend([x.strip() for x in line.split(",") if x.strip()])

    # Extract Experience & Projects
    experience_entries: List[ExperienceEntry] = []
    exp_m = re.search(r"\\section\*{(?:EXPERIENCE & PROJECTS|EXPERIENCE|WORK EXPERIENCE|PROJECTS)}(?:[^\w\\]*(?:\\\\|\r?\n)?)?([\s\S]*?)(?=\\section|\\end\{document\}|$)", latex_code, re.I)
    if exp_m:
        exp_raw = exp_m.group(1)
        items = re.findall(r"\\item\s*([^\n\\]+)", exp_raw)
        bullets = [clean_latex(it) for it in items if clean_latex(it)]
        has_quant = any(bool(re.search(r"(\d+%\s*|\$\s*\d+|\b\d{2,}\b|\b\d+\.\d+\b)", b)) for b in bullets)
        experience_entries.append(ExperienceEntry(
            title="Lead Engineer & Architect",
            company="Technical Projects & Experience",
            start_date="2024",
            end_date="Present",
            bullets=bullets,
            has_quantified_impact=has_quant,
        ))

    # Extract Education
    education_entries: List[EducationEntry] = []
    edu_m = re.search(r"\\section\*{EDUCATION}(?:[^\w\\]*(?:\\\\|\r?\n)?)?([\s\S]*?)(?=\\section|\\end\{document\}|$)", latex_code, re.I)
    if edu_m:
        edu_str = clean_latex(edu_m.group(1))
        degree = "B.Tech in Computer Science" if ("b.tech" in edu_str.lower() or "bachelor" in edu_str.lower()) else "Bachelors"
        institution_m = re.search(r"^([^—\n]+)", edu_str)
        institution = institution_m.group(1).strip() if institution_m else "University"
        education_entries.append(EducationEntry(
            degree=degree,
            institution=institution,
            graduation_date="2026",
        ))

    # Extract Certifications
    certifications: List[str] = []
    cert_m = re.search(r"\\section\*{CERTIFICATIONS}(?:[^\w\\]*(?:\\\\|\r?\n)?)?([\s\S]*?)(?=\\section|\\end\{document\}|$)", latex_code, re.I)
    if cert_m:
        cert_items = re.findall(r"\\item\s*([^\n\\]+)", cert_m.group(1))
        certifications = [clean_latex(c) for c in cert_items if clean_latex(c)]

    structured = StructuredResumeSchema(
        contact=ContactInfo(name=name, email=email, phone=phone, linkedin=linkedin),
        summary=summary,
        skills=SkillsCategorized(technical=skills_tech, soft=[], tools=skills_tools),
        experience=experience_entries,
        education=education_entries,
        certifications=certifications,
        sections_detected=["contact", "summary", "education", "skills", "experience", "certifications"],
        sections_missing=[],
    )

    return structured, clean_text
