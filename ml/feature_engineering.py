from __future__ import annotations

import logging
from typing import Dict, List, Union

import numpy as np

logger = logging.getLogger(__name__)


def compute_skill_overlap(resume_skills: List[str], job_skills: List[str]) -> float:
    """
    Compute Jaccard similarity between resume and job skill sets.

    Args:
        resume_skills: List of skills extracted from the resume.
        job_skills: List of required skills from the job listing.

    Returns:
        Jaccard similarity in [0.0, 1.0].
    """
    # Handle comma-separated strings from CSV
    if isinstance(resume_skills, str):
        resume_skills = [s.strip() for s in resume_skills.split(",")]
    if isinstance(job_skills, str):
        job_skills = [s.strip() for s in job_skills.split(",")]

    resume_set = {s.strip().lower() for s in resume_skills if isinstance(s, str) and s.strip()}
    job_set = {s.strip().lower() for s in job_skills if isinstance(s, str) and s.strip()}

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