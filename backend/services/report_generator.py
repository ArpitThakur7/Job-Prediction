from __future__ import annotations

from io import BytesIO
from typing import List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _score_color(score: float) -> Tuple[colors.Color, colors.Color]:
    """
    Determine bar and text colors based on score percentage.

    Args:
        score: match score in [0,1]

    Returns:
        (bar_color, label_color)
    """
    pct = score * 100.0
    if pct > 70.0:
        return colors.green, colors.white
    if pct >= 40.0:
        return colors.orange, colors.black
    return colors.red, colors.white


def generate_match_report(
    candidate: dict,
    job: dict,
    score: float,
    matched_skills: List[str],
    missing_skills: List[str],
) -> bytes:
    """
    Generate a styled PDF match report.

    Sections:
    1) Header
    2) Candidate Info
    3) Job Info
    4) Match Score + color bar
    5) Matched Skills (green bullets)
    6) Missing Skills (red bullets)
    7) Recommendation text

    Args:
        candidate: dict with name/email/experience/education
        job: dict with title/company/location/salary
        score: match score in [0,1]
        matched_skills: list of skills
        missing_skills: list of skills

    Returns:
        PDF bytes.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.fontSize = 18

    normal_style = styles["BodyText"]
    normal_style.fontSize = 10

    header_style = ParagraphStyle(
        "Header",
        parent=styles["Heading2"],
        fontSize=12,
        spaceAfter=8,
    )

    pct = score * 100.0
    bar_color, label_color = _score_color(score)

    matched_skill_html = "<br/>".join([f"• <font color='green'>{s}</font>" for s in matched_skills[:25]])
    missing_skill_html = "<br/>".join([f"• <font color='red'>{s}</font>" for s in missing_skills[:25]])

    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    salary_text = "Not specified"
    if isinstance(salary_min, (int, float)) and isinstance(salary_max, (int, float)):
        salary_text = f"{salary_min} - {salary_max}"

    if pct >= 70.0:
        recommendation = "Strong match. Proceed to interview and highlight the top aligned skills."
    elif pct >= 40.0:
        recommendation = "Moderate match. Consider tailoring the resume and emphasizing the missing skills."
    else:
        recommendation = "Low match. You may still apply if you can bridge key missing skills quickly."

    elements = []
    elements.append(Paragraph("JOB-AI-PLATFORM Match Report", title_style))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Candidate Info", header_style))
    elements.append(
        Paragraph(
            f"<b>Name:</b> {candidate.get('candidate_name') or candidate.get('name') or 'Unknown'}<br/>"
            f"<b>Email:</b> {candidate.get('email') or 'Unknown'}<br/>"
            f"<b>Experience:</b> {candidate.get('experience_years') or 0} years<br/>"
            f"<b>Education:</b> {candidate.get('education') or 'Unknown'}",
            normal_style,
        )
    )
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Job Info", header_style))
    elements.append(
        Paragraph(
            f"<b>Title:</b> {job.get('title') or 'Unknown'}<br/>"
            f"<b>Company:</b> {job.get('company') or 'Unknown'}<br/>"
            f"<b>Location:</b> {job.get('location') or 'Unknown'}<br/>"
            f"<b>Salary:</b> {salary_text}",
            normal_style,
        )
    )
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Match Score", header_style))

    # Color bar using a table-like paragraph approach (simple and dependency-free).
    # We'll render a textual bar representation.
    bar_units = 30
    filled = int(round(pct / 100.0 * bar_units))
    bar = "█" * filled + "░" * (bar_units - filled)
    elements.append(
        Paragraph(
            f"<b>Score:</b> {pct:.2f}%<br/>"
            f"<font color='{bar_color.hexval}'><b>{bar}</b></font>",
            normal_style,
        )
    )
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Matched Skills", header_style))
    elements.append(Paragraph(matched_skill_html if matched_skills else "No matched skills found.", normal_style))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Missing Skills", header_style))
    elements.append(
        Paragraph(missing_skill_html if missing_skills else "No missing skills found.", normal_style)
    )
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Recommendation", header_style))
    elements.append(Paragraph(recommendation, normal_style))

    doc.build(elements)
    return buffer.getvalue()
