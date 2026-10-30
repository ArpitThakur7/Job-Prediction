"""
ml/skills.py — the ONE shared skill extractor.

Used by:
  * scripts/prepare_dataset.py   (training-data generation)
  * ml/feature_engineering.py     (pair features, train + serve)
  * backend/services/matcher.py   (serve-time features for /match)
  * backend/services/nlp_extractor.py, backend/services/pdf_parser.py (resume parsing)

Why this exists
---------------
The previous extractors did ``skill.lower() in text.lower()`` — a substring test.
That made "R" match every text containing the letter r, "Go" match "good"/"going",
"AI" match "maintain", "Rust" match "trust", "Java" match "JavaScript", etc.
(dataset_summary.json showed "R" in 30002/30002 jobs.)

Rules implemented here
----------------------
* Every pattern is anchored on token boundaries: a skill must not be glued to
  letters/digits on either side (``(?<![A-Za-z0-9])...(?![A-Za-z0-9])``), and
  patterns ending in a symbol ("C++", "C#", "Node.js") get the same guard.
* Ambiguous short / English-word skills are matched CASE-SENSITIVELY:
  "R", "Go", "AI", "ML", "HR", "JS", "Rust", "Swift", "Ruby", "Spark", "React",
  "Excel", "REST", "Snowflake", "Transformers" ... so "go to market", "rust",
  "swift delivery", "spark growth", "react quickly", "excel at" do not count.
* "R" additionally needs programming / statistics context (see ``_R_CONTEXT``)
  or must sit inside a comma/pipe/slash separated list — a bare capital R in a
  sentence (initials, "R&D", "R.", list bullets) is not enough.
* "Go" must not be followed by a hyphen ("Go-to-market", "Go-live").
* A small alias map normalises synonyms to one canonical name
  (JS -> JavaScript, k8s -> Kubernetes, ML -> Machine Learning, Golang -> Go,
  Postgres -> PostgreSQL, sklearn -> Scikit-learn, ...).

Public API
----------
    extract_skills(text, vocab=ALL_SKILLS) -> list[str]     canonical names, vocab order
    canonicalize_skill(name) -> str | None                  alias -> canonical
    canonical_skill_set(skills) -> set[str]                 lower-cased canonical set
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Pattern, Sequence, Set, Tuple, Union

SKILL_EXTRACTOR_VERSION = "token-boundary-v2"

# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------

#: Skill list historically used by scripts/prepare_dataset.py (training data).
DATASET_SKILLS: List[str] = [
    "Python", "Java", "JavaScript", "TypeScript", "SQL", "NoSQL", "MongoDB",
    "PostgreSQL", "MySQL", "Redis", "Excel", "PowerPoint", "Word",
    "Communication", "Leadership", "Management", "Sales", "Marketing",
    "Customer Service", "Data Analysis", "Machine Learning", "AI",
    "Deep Learning", "NLP", "Computer Vision", "Project Management",
    "Agile", "Scrum", "React", "Angular", "Vue", "Node.js", "Django",
    "Flask", "FastAPI", "Spring", "AWS", "Azure", "Google Cloud", "Docker",
    "Kubernetes", "Git", "REST API", "GraphQL", "Tableau", "Power BI",
    "R", "MATLAB", "C++", "C#", "PHP", "Ruby", "Swift", "Kotlin", "Go",
    "Rust", "Scala", "Spark", "Hadoop", "Accounting", "Finance", "HR",
    "Recruiting", "Healthcare", "Nursing", "Teaching", "Research",
    "Writing", "Editing", "Photoshop", "AutoCAD", "Engineering",
    "Civil", "Mechanical", "Electrical", "DevOps", "Linux", "Bash",
    "Terraform", "Blockchain", "Cybersecurity", "Networking", "Mobile",
    "Android", "iOS",
]

#: Technical skill list used by the backend resume parsers (UI-facing).
TECH_SKILLS: List[str] = [
    "Python", "Java", "JavaScript", "TypeScript", "React", "Node.js", "Express",
    "Django", "Flask", "FastAPI", "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "GraphQL", "REST", "Microservices", "AWS", "Google Cloud", "Azure", "Docker",
    "Kubernetes", "Linux", "Git", "CI/CD", "Jenkins", "Terraform", "Ansible",
    "Shell", "Pandas", "NumPy", "Scikit-learn", "XGBoost", "LightGBM", "PyTorch",
    "TensorFlow", "Transformers", "SpaCy", "NLP", "LLMs", "LangChain", "Groq",
    "Pinecone", "Vector Search", "ElasticSearch", "Kafka", "Spark", "Airflow",
    "Hadoop", "Databricks", "Data Engineering", "Data Modeling", "ETL",
    "BigQuery", "Snowflake", "Tableau", "Power BI", "Statistics",
    "Data Visualization", "System Design", "OOP", "Design Patterns", "Agile",
    "Scrum", "Unit Testing", "Test Automation", "Selenium", "Playwright", "C#",
    "C++", "Go", "Ruby", "PHP", "R", ".NET", ".NET Core", "ASP.NET",
    "ASP.NET Core", "Entity Framework", "Blazor", "MERN", "MERN Stack", "Next.js",
]


def _union(*lists: Sequence[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for lst in lists:
        for s in lst:
            if s.lower() not in seen:
                seen.add(s.lower())
                out.append(s)
    return out


#: Vocabulary used for ML features (training AND serving). Union of both lists,
#: minus "REST" which is the same skill as "REST API" (avoids double counting).
ALL_SKILLS: List[str] = [s for s in _union(DATASET_SKILLS, TECH_SKILLS) if s != "REST"]

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
# Each canonical skill -> list of (pattern, case_sensitive).
# Patterns are regex fragments WITHOUT boundaries; boundaries are added by
# _compile(). Skills not listed here get a default case-insensitive literal.

_CS = True   # case-sensitive
_CI = False  # case-insensitive

SKILL_PATTERNS: Dict[str, List[Tuple[str, bool]]] = {
    # --- ambiguous short tokens (case-sensitive) ---
    "R": [(r"R(?![&'.\-/])(?!\s+(?:amp|and)\s+D\b)", _CS), (r"RStudio", _CI), (r"R\s+programming", _CI),
          (r"R\s+language", _CI), (r"Rlang", _CI), (r"tidyverse", _CI), (r"ggplot2?", _CI)],
    "Go": [(r"Go(?![\-'])", _CS), (r"go\s*lang", _CI), (r"Go\s+programming", _CI)],
    "AI": [(r"AI", _CS), (r"A\.I\.", _CS), (r"artificial\s+intelligence", _CI), (r"GenAI", _CI),
           (r"generative\s+AI", _CI)],
    "Machine Learning": [(r"machine[\s\-]+learning", _CI), (r"ML", _CS)],
    "HR": [(r"HR", _CS), (r"human\s+resources?", _CI), (r"HRIS", _CS)],
    "JavaScript": [(r"javascript", _CI), (r"java\s+script", _CI), (r"JS", _CS),
                   (r"ecmascript", _CI), (r"ES6", _CS)],
    "TypeScript": [(r"typescript", _CI)],
    "Java": [(r"java(?!\s*script)", _CI), (r"J2EE", _CI)],
    "C++": [(r"C\+\+", _CS), (r"cplusplus", _CI), (r"cpp", _CI)],
    "C#": [(r"C#", _CS), (r"C\s+sharp", _CI), (r"csharp", _CI)],
    "Rust": [(r"Rust", _CS), (r"rustlang", _CI)],
    "Swift": [(r"Swift", _CS), (r"SwiftUI", _CI)],
    "Ruby": [(r"Ruby", _CS), (r"ruby\s+on\s+rails", _CI), (r"Rails", _CS)],
    "Spark": [(r"Spark", _CS), (r"pyspark", _CI), (r"apache\s+spark", _CI), (r"spark\s+sql", _CI)],
    "React": [(r"React", _CS), (r"react\.?js", _CI), (r"react\s+native", _CI)],
    "Excel": [(r"Excel", _CS), (r"EXCEL", _CS), (r"ms[\s\-]+excel", _CI), (r"microsoft\s+excel", _CI)],
    "Word": [(r"ms[\s\-]+word", _CI), (r"microsoft\s+word", _CI)],
    "PowerPoint": [(r"power\s?point", _CI), (r"ms[\s\-]+ppt", _CI)],
    "Spring": [(r"spring\s+boot", _CI), (r"spring\s+framework", _CI), (r"spring\s+mvc", _CI),
               (r"spring\s+cloud", _CI), (r"springboot", _CI)],
    "REST API": [(r"REST(?:ful)?\s+APIs?", _CI), (r"RESTful", _CI), (r"REST", _CS)],
    "REST": [(r"REST(?:ful)?\s+APIs?", _CI), (r"RESTful", _CI), (r"REST", _CS)],
    "Shell": [(r"shell\s+script(?:ing|s)?", _CI), (r"unix\s+shell", _CI), (r"bash\s+script(?:ing|s)?", _CI)],
    "Express": [(r"express\.?js", _CI), (r"express\s+js", _CI), (r"Express(?=\s*(?:,|/|\||and\s+Node))", _CS)],
    "Transformers": [(r"hugging\s?face", _CI), (r"Transformers", _CS)],
    "Snowflake": [(r"Snowflake", _CS)],
    "Mobile": [(r"mobile\s+(?:app|application|development|developer|engineer)s?", _CI),
               (r"mobile\s+platforms?", _CI)],
    "Civil": [(r"civil\s+engineer(?:ing)?", _CI)],
    "Mechanical": [(r"mechanical\s+engineer(?:ing)?", _CI), (r"mechanical\s+design", _CI)],
    "Electrical": [(r"electrical\s+engineer(?:ing)?", _CI), (r"electrical\s+design", _CI)],
    "Engineering": [(r"engineering", _CI)],
    "Networking": [(r"computer\s+network(?:s|ing)?", _CI), (r"network\s+(?:engineer|admin\w*|security)", _CI),
                   (r"TCP/IP", _CI), (r"CCNA", _CS), (r"Networking", _CS)],
    "Research": [(r"research", _CI)],
    "Writing": [(r"technical\s+writing", _CI), (r"copy\s?writing", _CI), (r"content\s+writing", _CI),
                (r"writing", _CI)],
    "Editing": [(r"editing", _CI)],
    "Teaching": [(r"teaching", _CI)],
    "Finance": [(r"finance", _CI)],
    "Accounting": [(r"accounting", _CI)],
    "Recruiting": [(r"recruit(?:ing|ment)", _CI), (r"talent\s+acquisition", _CI)],
    "Healthcare": [(r"health\s?care", _CI)],
    "Nursing": [(r"nursing", _CI), (r"registered\s+nurse", _CI)],
    "Communication": [(r"communications?(?:\s+skills)?", _CI)],
    "Leadership": [(r"leadership", _CI)],
    "Management": [(r"management", _CI)],
    "Sales": [(r"sales", _CI)],
    "Marketing": [(r"marketing", _CI)],
    "Customer Service": [(r"customer\s+service", _CI), (r"customer\s+support", _CI)],
    "Data Analysis": [(r"data\s+analy(?:sis|tics|st)", _CI)],
    "Deep Learning": [(r"deep[\s\-]+learning", _CI), (r"neural\s+networks?", _CI)],
    "NLP": [(r"NLP", _CI), (r"natural\s+language\s+processing", _CI)],
    "Computer Vision": [(r"computer\s+vision", _CI), (r"OpenCV", _CI)],
    "Project Management": [(r"project\s+management", _CI), (r"PMP", _CS)],
    "Node.js": [(r"node\.?js", _CI), (r"node\s+js", _CI)],
    "Next.js": [(r"next\.?js", _CI), (r"next\s+js", _CI)],
    "Vue": [(r"vue(?:\.?js)?", _CI)],
    "Angular": [(r"angular(?:\.?js)?", _CI)],
    "MongoDB": [(r"mongo\s?db", _CI), (r"mongo", _CI)],
    "PostgreSQL": [(r"postgre\s?sql", _CI), (r"postgres", _CI), (r"psql", _CI)],
    "MySQL": [(r"my\s?sql", _CI)],
    "NoSQL": [(r"no\s?sql", _CI)],
    "SQL": [(r"SQL", _CI), (r"T-SQL", _CI), (r"PL/SQL", _CI)],
    "AWS": [(r"AWS", _CI), (r"amazon\s+web\s+services", _CI)],
    "Azure": [(r"azure", _CI), (r"microsoft\s+azure", _CI)],
    "Google Cloud": [(r"google\s+cloud(?:\s+platform)?", _CI), (r"GCP", _CS)],
    "Kubernetes": [(r"kubernetes", _CI), (r"k8s", _CI)],
    "Docker": [(r"docker", _CI)],
    "Git": [(r"git", _CI), (r"github", _CI), (r"gitlab", _CI), (r"bitbucket", _CI)],
    "CI/CD": [(r"CI\s*/\s*CD", _CI), (r"continuous\s+integration", _CI), (r"github\s+actions", _CI),
              (r"CI\s+CD", _CS)],
    "Power BI": [(r"power\s?bi", _CI)],
    "Scikit-learn": [(r"scikit[\s\-]?learn", _CI), (r"sklearn", _CI)],
    "NumPy": [(r"numpy", _CI)],
    "Pandas": [(r"pandas", _CI)],
    "PyTorch": [(r"pytorch", _CI)],
    "TensorFlow": [(r"tensorflow", _CI), (r"keras", _CI)],
    "SpaCy": [(r"spacy", _CI)],
    "LLMs": [(r"LLMs?", _CI), (r"large\s+language\s+models?", _CI)],
    "LangChain": [(r"lang\s?chain", _CI)],
    "ElasticSearch": [(r"elastic\s?search", _CI)],
    "Vector Search": [(r"vector\s+(?:search|database|db)s?", _CI)],
    "Data Engineering": [(r"data\s+engineer(?:ing)?", _CI)],
    "Data Modeling": [(r"data\s+model(?:l)?ing", _CI)],
    "Data Visualization": [(r"data\s+visuali[sz]ation", _CI)],
    "System Design": [(r"system\s+design", _CI)],
    "OOP": [(r"OOPS?", _CS), (r"object[\s\-]+oriented(?:\s+programming)?", _CI)],
    "Design Patterns": [(r"design\s+patterns?", _CI)],
    "Unit Testing": [(r"unit\s+test(?:ing|s)?", _CI)],
    "Test Automation": [(r"test\s+automation", _CI), (r"automated\s+testing", _CI)],
    "Statistics": [(r"statistics", _CI), (r"statistical\s+analysis", _CI)],
    "Groq": [(r"Groq", _CS)],
    "Pinecone": [(r"pinecone", _CI)],
    "Kafka": [(r"kafka", _CI)],
    "Airflow": [(r"airflow", _CI)],
    "ETL": [(r"ETL", _CI)],
    "BigQuery": [(r"big\s?query", _CI)],
    "Cybersecurity": [(r"cyber[\s\-]?security", _CI), (r"information\s+security", _CI)],
    "iOS": [(r"iOS", _CS), (r"IOS", _CS)],
    "DevOps": [(r"dev\s?ops", _CI)],
    "MATLAB": [(r"matlab", _CI)],
    "AutoCAD": [(r"auto\s?cad", _CI)],
    ".NET": [(r"\.NET", _CI), (r"dotnet", _CI), (r"ASP\.NET", _CI)],
    ".NET Core": [(r"\.NET\s+Core", _CI), (r"dotnet\s+core", _CI)],
    "ASP.NET": [(r"ASP\.NET", _CI)],
    "ASP.NET Core": [(r"ASP\.NET\s+Core", _CI)],
    "MERN": [(r"MERN", _CI)],
    "MERN Stack": [(r"MERN\s+stack", _CI)],
}

#: Free-form alias -> canonical (used to normalise skill strings that arrive as
#: lists, e.g. from Salvo "reasons", Mongo docs or user input).
SKILL_ALIASES: Dict[str, str] = {
    "js": "JavaScript", "javascript": "JavaScript", "ecmascript": "JavaScript", "es6": "JavaScript",
    "k8s": "Kubernetes", "kube": "Kubernetes",
    "ml": "Machine Learning", "machine-learning": "Machine Learning",
    "dl": "Deep Learning",
    "ai": "AI", "artificial intelligence": "AI", "genai": "AI", "generative ai": "AI",
    "golang": "Go", "go lang": "Go",
    "py": "Python", "python3": "Python",
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL", "psql": "PostgreSQL",
    "mongo": "MongoDB", "mongodb": "MongoDB",
    "node": "Node.js", "nodejs": "Node.js", "node js": "Node.js",
    "react.js": "React", "reactjs": "React", "react js": "React", "react native": "React",
    "next": "Next.js", "nextjs": "Next.js", "next js": "Next.js",
    "vue.js": "Vue", "vuejs": "Vue",
    "angularjs": "Angular", "angular.js": "Angular",
    "express.js": "Express", "expressjs": "Express",
    "sklearn": "Scikit-learn", "scikit learn": "Scikit-learn", "scikit-learn": "Scikit-learn",
    "tf": "TensorFlow", "keras": "TensorFlow",
    "torch": "PyTorch",
    "gcp": "Google Cloud", "google cloud platform": "Google Cloud",
    "amazon web services": "AWS",
    "ms excel": "Excel", "microsoft excel": "Excel",
    "ms word": "Word", "microsoft word": "Word",
    "powerbi": "Power BI",
    "c plus plus": "C++", "cpp": "C++", "cplusplus": "C++",
    "c sharp": "C#", "csharp": "C#",
    "dotnet": ".NET", "dot net": ".NET",
    "rest": "REST API", "rest api": "REST API", "restful": "REST API", "rest apis": "REST API",
    "ci cd": "CI/CD", "cicd": "CI/CD", "github actions": "CI/CD",
    "github": "Git", "gitlab": "Git",
    "llm": "LLMs", "llms": "LLMs", "large language models": "LLMs",
    "elastic search": "ElasticSearch", "elasticsearch": "ElasticSearch",
    "pyspark": "Spark", "apache spark": "Spark",
    "nlp": "NLP", "natural language processing": "NLP",
    "cv": "Computer Vision", "opencv": "Computer Vision",
    "human resources": "HR",
    "ruby on rails": "Ruby", "rails": "Ruby",
    "rstudio": "R", "r programming": "R",
    "hugging face": "Transformers", "huggingface": "Transformers",
    "cyber security": "Cybersecurity",
    "spring boot": "Spring", "springboot": "Spring",
    "oops": "OOP", "object oriented programming": "OOP",
}

# Context words that make a bare capital "R" a programming-language mention.
_R_CONTEXT = re.compile(
    r"(?i)(?<![a-z])(python|sas|spss|stata|matlab|sql|statistic\w*|programming|language|"
    r"rstudio|shiny|tidyverse|ggplot\w*|dplyr|cran|data\s+(?:analysis|science|analytics)|"
    r"regression|econometric\w*|julia|scala|tableau|excel|machine\s+learning|analytics)"
)
_R_WINDOW = 80

_TOKEN_BEFORE = r"(?<![A-Za-z0-9_])"
_TOKEN_AFTER = r"(?![A-Za-z0-9_+#])"


def _compile(fragment: str, case_sensitive: bool) -> Pattern[str]:
    flags = 0 if case_sensitive else re.IGNORECASE
    # A leading "." (".NET") must still not be glued to a word char on its left.
    return re.compile(_TOKEN_BEFORE + "(?:" + fragment + ")" + _TOKEN_AFTER, flags)


@lru_cache(maxsize=None)
def _patterns_for(skill: str) -> Tuple[Pattern[str], ...]:
    spec = SKILL_PATTERNS.get(skill)
    if spec is None:
        # default: case-insensitive whole-token literal (multi-word -> flexible whitespace)
        frag = r"\s+".join(re.escape(w) for w in skill.split())
        spec = [(frag, _CI)]
    return tuple(_compile(f, cs) for f, cs in spec)


# Skills whose FIRST pattern is a bare, ambiguous token that only counts when
# programming context is nearby (or it sits in a comma/pipe/slash list).
# Remaining patterns (RStudio, golang, ...) are unambiguous and always count.
_GO_CONTEXT = re.compile(
    r"(?i)(?<![a-z])(golang|python|java|rust|c\+\+|programming|language|backend|back-end|"
    r"microservices?|kubernetes|docker|grpc|developer|engineer\w*|software|concurrency|"
    r"goroutines?|node\.?js|typescript|scala|kotlin|api|services)"
)
_CONTEXT_REQUIRED: Dict[str, Tuple[Pattern[str], Pattern[str]]] = {
    "R": (_R_CONTEXT, re.compile(r"(?:^|[,;|/•(:]\s*)R\s*(?:$|[,;|/•)])")),
    "Go": (_GO_CONTEXT, re.compile(r"(?:^|[,;|/•(:]\s*)Go\s*(?:$|[,;|/•)])")),
}


def _has_contextual(text: str, skill: str) -> bool:
    pats = _patterns_for(skill)
    for pat in pats[1:]:  # explicit aliases (RStudio, golang, ...)
        if pat.search(text):
            return True
    ctx_re, list_re = _CONTEXT_REQUIRED[skill]
    for m in pats[0].finditer(text):
        lo = max(0, m.start() - _R_WINDOW)
        hi = min(len(text), m.end() + _R_WINDOW)
        # exclude the token itself from the context window
        window = text[lo:m.start()] + " " + text[m.end():hi]
        if ctx_re.search(window):
            return True
        line_lo = text.rfind("\n", 0, m.start()) + 1
        line_hi = text.find("\n", m.end())
        line = text[line_lo: line_hi if line_hi != -1 else len(text)]
        if list_re.search(line):
            return True
    return False


def has_skill(text: str, skill: str) -> bool:
    """True if ``skill`` (canonical name) is mentioned in ``text`` as a whole token."""
    if not text:
        return False
    if skill in _CONTEXT_REQUIRED:
        return _has_contextual(text, skill)
    return any(p.search(text) for p in _patterns_for(skill))


def extract_skills(text: Optional[str], vocab: Sequence[str] = ALL_SKILLS) -> List[str]:
    """
    Extract canonical skill names mentioned in ``text``.

    Args:
        text:  Free text (resume / job description). HTML should be stripped first,
               but punctuation (C++, C#, Node.js, CI/CD) should be KEPT.
        vocab: Canonical skill names to look for (default: ALL_SKILLS).

    Returns:
        Matched canonical names, in vocab order, without duplicates.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    return [s for s in vocab if has_skill(text, s)]


def extract_skills_csv(text: Optional[str], vocab: Sequence[str] = ALL_SKILLS) -> str:
    """Comma-joined variant used for CSV columns."""
    return ", ".join(extract_skills(text, vocab))


_CANON_BY_LOWER: Dict[str, str] = {s.lower(): s for s in ALL_SKILLS}


def canonicalize_skill(name: object) -> Optional[str]:
    """
    Map a free-form skill string to its canonical name.

    Unknown skills are returned stripped (original casing) so information is not lost;
    empty / non-string input returns None.
    """
    if not isinstance(name, str):
        return None
    raw = re.sub(r"\s+", " ", name.strip().strip("+").strip())
    if not raw:
        return None
    low = raw.lower()
    if low in _CANON_BY_LOWER:
        return _CANON_BY_LOWER[low]
    if low in SKILL_ALIASES:
        return SKILL_ALIASES[low]
    compact = low.replace(" ", "")
    if compact in SKILL_ALIASES:
        return SKILL_ALIASES[compact]
    return raw


def canonical_skill_set(skills: Union[str, Iterable[object], None]) -> Set[str]:
    """
    Normalise a list (or comma-separated string) of skills into a lower-cased
    canonical set — the representation used for all overlap features.
    """
    if skills is None:
        return set()
    if isinstance(skills, str):
        items: Iterable[object] = [s for s in skills.split(",")]
    else:
        items = skills
    out: Set[str] = set()
    for s in items:
        c = canonicalize_skill(s)
        if c:
            out.add(c.lower())
    return out


__all__ = [
    "ALL_SKILLS",
    "DATASET_SKILLS",
    "TECH_SKILLS",
    "SKILL_ALIASES",
    "SKILL_EXTRACTOR_VERSION",
    "canonical_skill_set",
    "canonicalize_skill",
    "extract_skills",
    "extract_skills_csv",
    "has_skill",
]
