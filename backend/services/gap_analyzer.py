"""
Phase 4 — Gap Analysis & Recommendations - JOB-AI Platform
Diffs candidate skills against target job description, identifies adjacent/transferable skills,
and generates specific bullet rewrite suggestions and learning tracks.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.config import settings
from backend.services.structured_extractor import StructuredResumeSchema

logger = logging.getLogger("backend.services.gap_analyzer")

# Adjacent / Transferable skill mapping matrix
ADJACENT_SKILLS_MAP = {
    "vue.js": ["react", "angular", "frontend development"],
    "vue": ["react", "angular"],
    "react": ["vue.js", "angular", "next.js", "mern"],
    "postgresql": ["mysql", "sqlite", "oracle", "sql"],
    "mysql": ["postgresql", "mariadb", "sql"],
    "mongodb": ["dynamodb", "couchbase", "nosql", "mern"],
    "fastapi": ["flask", "django", "express.js", "python"],
    "flask": ["fastapi", "django", "python"],
    "django": ["fastapi", "flask", "python"],
    "express": ["node.js", "fastapi", "nestjs", "mern"],
    "node.js": ["express", "javascript", "typescript", "mern"],
    "mern": ["react", "node.js", "express", "mongodb", "javascript", "typescript"],
    "c#": [".net", ".net core", "asp.net", "java", "object-oriented programming"],
    ".net": ["c#", ".net core", "asp.net", "asp.net core", "entity framework"],
    ".net core": [".net", "c#", "asp.net core", "entity framework"],
    "asp.net": [".net", "asp.net core", "c#", "web api"],
    "asp.net core": [".net core", ".net", "c#", "entity framework"],
    "entity framework": [".net", "c#", "orm", "sql server"],
    "aws": ["gcp", "azure", "cloud infrastructure"],
    "gcp": ["aws", "azure"],
    "azure": ["aws", "gcp", ".net"],
    "docker": ["podman", "containerization", "kubernetes"],
    "kubernetes": ["docker swarm", "helm", "k8s"],
    "python": ["fastapi", "django", "pandas", "pytorch", "scripting"],
    "typescript": ["javascript", "react", "node.js", "flow"],
}


class AdjacentSkillMatch(BaseModel):
    required_skill: str = ""
    candidate_skill: str = ""
    explanation: str = ""


class BulletRewriteSuggestion(BaseModel):
    original_bullet: str = ""
    suggested_rewrite: str = ""
    reasoning: str = ""


class LearningTrackRecommendation(BaseModel):
    missing_skill: str = ""
    learning_category: str = ""
    actionable_roadmap: str = ""


class SkillGapAnalysisResult(BaseModel):
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    adjacent_skills: List[AdjacentSkillMatch] = Field(default_factory=list)
    bullet_rewrites: List[BulletRewriteSuggestion] = Field(default_factory=list)
    learning_tracks: List[LearningTrackRecommendation] = Field(default_factory=list)


def perform_skill_gap_analysis(
    structured: StructuredResumeSchema,
    job_required_skills: List[str],
    groq_api_key: Optional[str] = None,
) -> SkillGapAnalysisResult:
    """
    Perform skill diffing, adjacent skill detection, bullet rewrite generation, and learning path recommendations.
    """
    candidate_skills_lower = set(
        s.lower().strip() for s in (structured.skills.technical + structured.skills.soft + structured.skills.tools)
    )

    matched: List[str] = []
    missing_raw: List[str] = []
    adjacent_matches: List[AdjacentSkillMatch] = []

    for req in job_required_skills:
        req_lower = req.lower().strip()
        if req_lower in candidate_skills_lower:
            matched.append(req.title())
        else:
            # Check for adjacent/transferable skill
            found_adj = False
            for cand_skill in candidate_skills_lower:
                adj_list = ADJACENT_SKILLS_MAP.get(cand_skill, [])
                if req_lower in adj_list or any(a in req_lower for a in adj_list):
                    adjacent_matches.append(
                        AdjacentSkillMatch(
                            required_skill=req.title(),
                            candidate_skill=cand_skill.title(),
                            explanation=f"Your experience with '{cand_skill.title()}' is highly transferable to '{req.title()}'.",
                        )
                    )
                    found_adj = True
                    break

            if not found_adj:
                missing_raw.append(req.title())

    # Build Bullet Rewrite Suggestions for weak unquantified bullets
    rewrites: List[BulletRewriteSuggestion] = []
    for exp in structured.experience:
        for bullet in exp.bullets:
            if not exp.has_quantified_impact and not re.search(r"(\d+%\s*|\$\s*\d+|\b\d{2,}\b)", bullet):
                if len(bullet.strip()) > 15 and len(rewrites) < 4:
                    words = bullet.strip().split()
                    verb = words[0].title() if words else "Spearheaded"
                    rewrites.append(
                        BulletRewriteSuggestion(
                            original_bullet=bullet,
                            suggested_rewrite=f"{verb} key project deliverables, boosting operational efficiency by 25% and reducing execution time across team workflows.",
                            reasoning="Add a quantified metric (% improvement, team size, throughput) to demonstrate measurable business value.",
                        )
                    )

    # Build Learning Tracks for missing skills
    learning_tracks: List[LearningTrackRecommendation] = []
    for m in missing_raw[:4]:
        learning_tracks.append(
            LearningTrackRecommendation(
                missing_skill=m,
                learning_category=f"Core Competency — {m}",
                actionable_roadmap=f"Build a hands-on portfolio project incorporating {m} and complete official documentation tutorials to demonstrate proficiency on your resume.",
            )
        )

    # Attempt LLM bullet rewrite enhancements if Groq key available
    key = groq_api_key or settings.GROQ_API_KEY
    if key and len(key.strip()) > 10 and len(rewrites) > 0:
        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(api_key=key, model="llama-3.1-8b-instant", temperature=0.2)
            prompt_text = (
                "Transform the following weak resume bullet point into a strong, quantified, action-oriented bullet point.\n"
                f"Original: {rewrites[0].original_bullet}\n"
                "Return ONLY a single improved bullet string starting with a strong action verb and including a percentage or metric metric placeholder."
            )
            res = llm.invoke([("system", "You are an expert resume writer."), ("human", prompt_text)])
            suggested_text = res.content.strip() if hasattr(res, "content") else str(res).strip()
            if suggested_text and len(suggested_text) > 15:
                rewrites[0].suggested_rewrite = suggested_text.strip('"').strip()
        except Exception as exc:
            logger.debug("Groq bullet rewrite enhancement skipped: %s", exc)

    return SkillGapAnalysisResult(
        matched_skills=matched,
        missing_skills=missing_raw,
        adjacent_skills=adjacent_matches,
        bullet_rewrites=rewrites,
        learning_tracks=learning_tracks,
    )
