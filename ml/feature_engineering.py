from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Union

import numpy as np

from ml.skills import canonical_skill_set, extract_skills
from ml.text_utils import strip_html

logger = logging.getLogger(__name__)


def compute_skill_overlap(resume_skills: List[str], job_skills: List[str]) -> float:
    """
    Compute Jaccard similarity between resume and job skill sets.

    Skills are normalised through the shared alias map (ml/skills.py), so
    "JS" and "JavaScript" or "k8s" and "Kubernetes" count as the same skill.

    Args:
        resume_skills: List of skills extracted from the resume.
        job_skills: List of required skills from the job listing.

    Returns:
        Jaccard similarity in [0.0, 1.0].
    """
    resume_set = canonical_skill_set(resume_skills)
    job_set = canonical_skill_set(job_skills)

    if not resume_set and not job_set:
        logger.debug("Both skill sets are empty — returning 0.0")
        return 0.0

    intersection = resume_set.intersection(job_set)
    union = resume_set.union(job_set)
    score = len(intersection) / len(union) if union else 0.0
    logger.debug("Skill overlap: %.4f (%d matched / %d union)", score, len(intersection), len(union))
    return score


def compute_experience_gap(resume_years: Union[float, int, str], required_years: Union[float, int, str]) -> float:
    """
    Compute normalized experience gap:
      (resume - required) / max(required, 1), clipped to [-1, 1].

    Positive = overqualified, Negative = underqualified.

    Args:
        resume_years: Candidate's years of experience.
        required_years: Required years of experience for the job.

    Returns:
        Normalized gap clipped to [-1, 1].
    """
    def _to_float(x: object) -> float:
        try:
            return float(x)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            logger.warning("Could not convert '%s' to float — defaulting to 0.0", x)
            return 0.0

    resume_f = _to_float(resume_years)
    required_f = _to_float(required_years)
    required_safe = max(required_f, 1.0)
    gap = (resume_f - required_f) / required_safe
    clipped = float(np.clip(gap, -1.0, 1.0))
    logger.debug("Experience gap: %.4f (resume=%.1f, required=%.1f)", clipped, resume_f, required_f)
    return clipped


def encode_education_level(degree: str) -> int:
    """
    Encode education degree level into an ordinal integer.

    Mapping:
      unknown / missing : 0
      high school       : 1
      associate         : 2
      bachelor          : 3
      master            : 4
      phd / doctorate   : 5

    Args:
        degree: Education degree string.

    Returns:
        Encoded level integer (0–5).
    """
    if not isinstance(degree, str):
        return 0
    d = degree.strip().lower()

    if "phd" in d or "doctor" in d or "doctorate" in d:
        return 5
    if "master" in d or "msc" in d or "mba" in d or "m.s" in d:
        return 4
    if "bachelor" in d or "b.s" in d or "b.e" in d or "b.tech" in d or "undergraduate" in d:
        return 3
    if "associate" in d:
        return 2
    if "high school" in d or "diploma" in d or "ged" in d or "secondary" in d:
        return 1
    return 0


def encode_location_match(resume_location: str, job_location: str) -> int:
    """
    Encode whether the candidate location matches the job location.

    Rules:
      - "remote" in job_location => 1
      - exact match               => 1
      - partial city/state match  => 1
      - otherwise                 => 0

    Args:
        resume_location: Candidate's location.
        job_location: Job's location.

    Returns:
        1 if match, else 0.
    """
    if not isinstance(resume_location, str) or not isinstance(job_location, str):
        return 0

    r = resume_location.strip().lower()
    j = job_location.strip().lower()

    if not r or not j:
        return 0

    # Remote jobs accept anyone
    if "remote" in j:
        return 1

    # Exact match
    if r == j:
        return 1

    # Partial match — city or state overlap
    r_parts = set(r.replace(",", " ").split())
    j_parts = set(j.replace(",", " ").split())
    if r_parts.intersection(j_parts):
        return 1

    return 0


def compute_education_gap(resume_degree: str, job_degree: str) -> int:
    """
    Compute ordinal gap between resume education and job required education.

    Positive = overqualified, Negative = underqualified, 0 = exact match.

    Args:
        resume_degree: Candidate's highest degree.
        job_degree: Job's required degree.

    Returns:
        Integer gap in range [-5, 5].
    """
    resume_level = encode_education_level(resume_degree)
    job_level = encode_education_level(job_degree)
    gap = resume_level - job_level
    logger.debug("Education gap: %d (resume=%d, job=%d)", gap, resume_level, job_level)
    return gap


def compute_salary_match(
    resume_expected: Union[float, int, str],
    job_salary_min: Union[float, int, str],
    job_salary_max: Union[float, int, str],
) -> float:
    """
    Compute how well the candidate's expected salary fits the job's range.

    Returns:
      1.0  — expected salary is within range
      0.5  — expected salary is within 20% above the max (negotiable)
      0.0  — expected salary is way above range or data is missing

    Args:
        resume_expected: Candidate's expected salary.
        job_salary_min: Job's minimum offered salary.
        job_salary_max: Job's maximum offered salary.

    Returns:
        Float score in [0.0, 1.0].
    """
    def _to_float(x: object) -> float:
        try:
            return float(x)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0

    expected = _to_float(resume_expected)
    sal_min = _to_float(job_salary_min)
    sal_max = _to_float(job_salary_max)

    # If any salary data is missing/zero, return neutral score
    if expected <= 0 or sal_max <= 0:
        logger.debug("Salary data missing — returning neutral 0.5")
        return 0.5

    if sal_min <= expected <= sal_max:
        return 1.0
    if sal_max < expected <= sal_max * 1.2:
        return 0.5
    return 0.0


def build_feature_vector(resume_dict: Dict, job_dict: Dict) -> np.ndarray:
    """
    Build a complete feature vector for XGBoost matching.

    Expected keys (all optional — safe defaults applied):
      resume_dict:
        - "skills"           : list[str] or comma-separated str
        - "experience_years" : float | int | str
        - "degree"           : str
        - "location"         : str
        - "expected_salary"  : float | int | str  (optional)

      job_dict:
        - "skills"           : list[str] or comma-separated str
        - "required_years"   : float | int | str
        - "degree"           : str
        - "location"         : str
        - "salary_min"       : float | int | str  (optional)
        - "salary_max"       : float | int | str  (optional)

    Returns:
        Numpy float array of shape (6,):
          [skill_overlap, experience_gap, education_gap,
           location_match, education_level_resume, salary_match]
    """
    # --- Skills ---
    resume_skills = resume_dict.get("skills", [])
    job_skills = job_dict.get("skills", [])

    # Handle comma string from CSV
    if isinstance(resume_skills, str):
        resume_skills = [s.strip() for s in resume_skills.split(",")]
    if isinstance(job_skills, str):
        job_skills = [s.strip() for s in job_skills.split(",")]

    # --- Experience ---
    resume_years = resume_dict.get("experience_years", 0.0)
    required_years = job_dict.get("required_years", 0.0)

    # --- Education ---
    resume_degree = resume_dict.get("degree", "")
    job_degree = job_dict.get("degree", "")

    # --- Location ---
    resume_location = resume_dict.get("location", "")
    job_location = job_dict.get("location", "")

    # --- Salary ---
    expected_salary = resume_dict.get("expected_salary", 0.0)
    salary_min = job_dict.get("salary_min", 0.0)
    salary_max = job_dict.get("salary_max", 0.0)

    # --- Compute features ---
    skill_overlap = compute_skill_overlap(resume_skills, job_skills)
    experience_gap = compute_experience_gap(resume_years, required_years)
    education_gap = compute_education_gap(resume_degree, job_degree)
    location_match = encode_location_match(resume_location, job_location)
    education_level_resume = encode_education_level(resume_degree)
    salary_match = compute_salary_match(expected_salary, salary_min, salary_max)

    feature_vector = np.array(
        [
            skill_overlap,        # float [0, 1]
            experience_gap,       # float [-1, 1]
            education_gap,        # int   [-5, 5]
            location_match,       # int   {0, 1}
            education_level_resume,  # int [0, 5]
            salary_match,         # float {0.0, 0.5, 1.0}
        ],
        dtype=float,
    )

    logger.debug("Feature vector: %s", feature_vector)
    return feature_vector


# ─────────────────────────────────────────────
# FEATURE COLUMN NAMES — keep in sync with
# build_feature_vector() output order above.
# Import this in train.py and evaluate.py.
# ─────────────────────────────────────────────
FEATURE_COLUMNS: List[str] = [
    "skill_overlap",
    "experience_gap",
    "education_gap",
    "location_match",
    "education_level_resume",
    "salary_match",
]

# ─────────────────────────────────────────────
# Fresher-aware Feature Extraction Helpers
# ─────────────────────────────────────────────

DOMAIN_EDU_KEYWORDS: Dict[str, List[str]] = {
    "INFORMATION-TECHNOLOGY": ["computer", "software", "information", "data", "computing", "it ", "technology", "cyber"],
    "ENGINEERING": ["engineer", "mechanical", "electrical", "civil", "electronics", "chemical"],
    "FINANCE": ["finance", "economics", "commerce", "accounting", "business administration"],
    "BUSINESS-DEVELOPMENT": ["business", "management", "mba", "commerce", "marketing"],
    "SALES": ["marketing", "business", "commerce", "retail"],
    "ACCOUNTANT": ["accounting", "commerce", "finance", "chartered"],
    "CHEF": ["culinary", "hospitality", "food"],
    "FITNESS": ["sports", "physical education", "kinesiology", "exercise"],
    "ADVOCATE": ["law", "legal", "jurisprudence", "llb"],
    "AVIATION": ["aviation", "aeronautical", "aerospace", "pilot"],
}

MODERN_SKILLS = {
    "react", "next.js", "vue", "angular", "typescript", "docker", "kubernetes",
    "aws", "azure", "google cloud", "terraform", "fastapi", "graphql",
    "machine learning", "deep learning", "nlp", "computer vision",
    "python", "go", "rust", "kotlin", "swift", "flutter",
    "devops", "ci/cd", "github actions", "mongodb", "redis", "kafka",
    "blockchain", "cybersecurity", "ai",
}


def count_project_keywords(text: str) -> int:
    """Count project-related keywords in resume text (freshers demonstrate skills via projects)."""
    if not isinstance(text, str):
        return 0
    text_lower = text.lower()
    project_kw = [
        "project", "capstone", "thesis", "hackathon", "portfolio",
        "built", "developed", "created", "designed", "implemented",
        "github", "open source", "contribution", "demo", "prototype",
    ]
    return min(10, sum(1 for kw in project_kw if kw in text_lower))


def count_internship_mentions(text: str) -> int:
    """Count internship-related mentions in resume text."""
    if not isinstance(text, str):
        return 0
    text_lower = text.lower()
    intern_kw = ["intern", "internship", "trainee", "apprentice", "co-op", "coop"]
    return min(5, sum(1 for kw in intern_kw if kw in text_lower))


def count_certifications(text: str) -> int:
    """Count certification-related mentions in resume text."""
    if not isinstance(text, str):
        return 0
    text_lower = text.lower()
    cert_kw = [
        "certified", "certification", "certificate", "aws certified",
        "google certified", "azure certified", "pmp", "scrum master",
        "comptia", "cisco", "oracle certified", "coursera", "udemy",
        "edx", "nanodegree", "specialization",
    ]
    return min(5, sum(1 for kw in cert_kw if kw in text_lower))


def compute_education_field_match(text: str, category: str) -> int:
    """Check if education/resume text contains keywords matching the job domain/category."""
    if not isinstance(text, str) or not isinstance(category, str):
        return 0
    text_lower = text.lower()
    cat_upper = category.strip().upper()
    domain_kws = DOMAIN_EDU_KEYWORDS.get(cat_upper, [])
    return 1 if any(kw in text_lower for kw in domain_kws) else 0


def compute_experience_adequacy(
    resume_exp: float,
    job_exp: float,
    is_entry_level: bool,
) -> float:
    """
    Compute non-linear experience adequacy score.
    For entry-level roles (<=2 yrs), freshers (0-2 yrs) get full marks (1.0).
    """
    exp_gap = resume_exp - job_exp
    if is_entry_level:
        if resume_exp <= 2.0:
            return 1.0
        elif resume_exp <= 5.0:
            return 0.7
        else:
            return 0.4
    else:
        if exp_gap >= 0.0:
            return 1.0
        elif exp_gap >= -2.0:
            return 0.6
        elif exp_gap >= -4.0:
            return 0.3
        else:
            return 0.1


def compute_skill_recency_score(skills: Union[List[str], str]) -> float:
    """Compute proportion of modern/trending skills among candidate's skills."""
    skill_set = canonical_skill_set(skills)
    if not skill_set:
        return 0.0
    modern_count = len(skill_set & MODERN_SKILLS)
    return round(modern_count / len(skill_set), 4)


# ─────────────────────────────────────────────
# Shared extraction helpers (moved here from scripts/prepare_dataset.py so the
# dataset builder and the serving path compute features identically)
# ─────────────────────────────────────────────

EDUCATION_MAP: Dict[str, str] = {
    "phd": "PhD", "doctorate": "PhD",
    "master": "Masters", "mba": "Masters", "m.tech": "Masters",
    "m.s.": "Masters", "msc": "Masters",
    "bachelor": "Bachelors", "b.tech": "Bachelors", "b.s.": "Bachelors",
    "b.e.": "Bachelors", "bsc": "Bachelors", "b.com": "Bachelors",
    "associate": "Associate", "diploma": "Associate",
    "high school": "High School", "secondary": "High School",
}

EDUCATION_SCORE: Dict[str, int] = {
    "PhD": 5, "Masters": 4, "Bachelors": 3,
    "Associate": 2, "High School": 1, "Not Specified": 0,
}


def extract_experience_years(text: str) -> int:
    """Years of experience mentioned in text (ignores ages / DOB)."""
    if not isinstance(text, str) or not text:
        return 0
    text_clean = re.sub(
        r"(?i)\b(?:age|dob|date\s+of\s+birth|born)\s*[:=\-]?\s*\d+\s*(?:years?|yrs?)?\s*(?:old|of\s+age)?\b",
        " ",
        text,
    )
    text_clean = re.sub(r"(?i)\b\d+\s*(?:years?|yrs?)\s*(?:old|of\s+age)\b", " ", text_clean)
    exp_matches = re.findall(
        r"(?i)\b(\d+)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:work\s+|professional\s+|relevant\s+)?experience\b",
        text_clean,
    )
    if exp_matches:
        valid_vals = [int(v) for v in exp_matches if 0 <= int(v) <= 45]
        if valid_vals:
            return max(valid_vals)
    matches = re.findall(r"(\d+)\+?\s*years?\s*(of)?\s*(experience)?", text_clean, re.IGNORECASE)
    if not matches:
        return 0
    valid_fallback = [int(m[0]) for m in matches if int(m[0]) < 18]
    return max(valid_fallback) if valid_fallback else 0


def extract_education(text: str) -> str:
    """Highest-priority education level keyword found in text (EDUCATION_MAP order)."""
    if not isinstance(text, str):
        return "Not Specified"
    text_lower = text.lower()
    for keyword, level in EDUCATION_MAP.items():
        if keyword in text_lower:
            return level
    return "Not Specified"


def estimate_min_experience_from_title(title: str) -> float:
    """Seniority heuristic used for live (Salvo) jobs that state no years explicitly."""
    t = str(title or "").lower()
    if "intern" in t or "trainee" in t:
        return 0.0
    if "junior" in t or "entry" in t or "associate" in t:
        return 1.0
    if "lead" in t or "principal" in t or "director" in t:
        return 7.0
    if "senior" in t or "sr." in t or "architect" in t:
        return 5.0
    return 2.0


def _as_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def resume_skill_set(resume: Dict[str, Any]) -> Set[str]:
    """Canonical skills of a resume: provided list ∪ skills found in its raw text."""
    skills = canonical_skill_set(resume.get("skills"))
    raw = resume.get("raw_text")
    if isinstance(raw, str) and raw.strip():
        skills |= canonical_skill_set(extract_skills(strip_html(raw)))
    return skills


def job_skill_set(job: Dict[str, Any]) -> Set[str]:
    """Canonical skills of a job: provided required_skills ∪ skills found in its description."""
    skills = canonical_skill_set(job.get("required_skills"))
    desc = job.get("description")
    if isinstance(desc, str) and desc.strip():
        skills |= canonical_skill_set(extract_skills(strip_html(desc)))
    return skills


def compute_pair_features(
    resume: Dict[str, Any],
    job: Dict[str, Any],
    semantic_similarity: float = 0.0,
    tfidf_similarity: float = 0.0,
    r_skills: Optional[Set[str]] = None,
    j_skills: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    THE feature function for a resume/job pair — used by scripts/prepare_dataset.py
    (training data), backend/services/matcher.py (serving) and
    ml/retrain_with_feedback.py (feedback rows), so all three agree.

    resume keys: skills, raw_text, experience_years, education, location
    job keys:    required_skills, description, title, location, category,
                 experience_years | min_experience (optional; else parsed from description)

    ``r_skills`` / ``j_skills`` may be passed pre-computed (canonical lower-case sets)
    to avoid re-extracting in tight loops.
    """
    if r_skills is None:
        r_skills = resume_skill_set(resume)
    if j_skills is None:
        j_skills = job_skill_set(job)

    overlap_count = len(r_skills & j_skills)
    overlap_ratio = overlap_count / max(len(j_skills), 1)

    description = str(job.get("description") or "")
    job_exp = _as_float(job.get("experience_years"))
    if job_exp is None:
        job_exp = _as_float(job.get("min_experience"))
    if job_exp is None:
        job_exp = float(extract_experience_years(description))
    res_exp = _as_float(resume.get("experience_years"), 0.0) or 0.0
    exp_gap = float(np.clip(res_exp - job_exp, -10, 10))

    raw_text = str(resume.get("raw_text") or "")
    edu_level = extract_education(str(resume.get("education") or ""))
    if edu_level == "Not Specified" and raw_text:
        edu_level = extract_education(raw_text)
    edu_score = EDUCATION_SCORE.get(edu_level, 0)

    res_loc = str(resume.get("location") or "").lower()  # unknown -> only remote jobs match
    job_loc = str(job.get("location") or "Remote").lower()
    r_parts = set(res_loc.replace(",", " ").split())
    j_parts = set(job_loc.replace(",", " ").split())
    location_match = 1 if "remote" in job_loc or r_parts.intersection(j_parts) else 0

    res_text_lower = raw_text.lower()
    job_title_words = set(str(job.get("title") or "").lower().split())
    title_relevance = 1 if any(w in res_text_lower for w in job_title_words if len(w) > 3) else 0

    is_entry_level_job = 1 if job_exp <= 2 else 0
    job_cat = str(job.get("category") or "").strip().upper()

    return {
        "skill_overlap_count":   overlap_count,
        "skill_overlap_ratio":   round(overlap_ratio, 4),
        "experience_gap":        exp_gap,
        "education_score":       edu_score,
        "location_match":        location_match,
        "title_relevance":       title_relevance,
        "semantic_similarity":   round(float(semantic_similarity or 0.0), 4),
        "tfidf_similarity":      round(float(tfidf_similarity or 0.0), 4),
        "skills_count_resume":   len(r_skills),
        "skills_count_job":      len(j_skills),
        "is_entry_level_job":    is_entry_level_job,
        "project_keyword_count": count_project_keywords(raw_text),
        "internship_mentions":   count_internship_mentions(raw_text),
        "certification_count":   count_certifications(raw_text),
        "education_field_match": compute_education_field_match(raw_text, job_cat),
        "experience_adequacy":   round(compute_experience_adequacy(res_exp, job_exp, bool(is_entry_level_job)), 2),
        "skill_recency_score":   compute_skill_recency_score(list(r_skills)),
        # bookkeeping (not model features)
        "resume_experience_years": res_exp,
        "job_experience_required": job_exp,
    }