"""
Phase 1 — Robust Text Extractor - JOB-AI Platform
Extracts raw text preserving sections, detects scanned PDFs, normalizes whitespace & noise, and computes SHA256 hashes.
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
from typing import Any, Dict

logger = logging.getLogger("backend.services.text_extractor")

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB cap
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def normalize_text_formatting(raw_text: str) -> str:
    """
    Normalize whitespace, smart quotes, bullet characters, and encoding artifacts.
    Preserves line breaks for section parsing downstream.
    """
    if not raw_text:
        return ""

    # Replace smart quotes and special dashes
    text = raw_text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = text.replace("–", "-").replace("—", "-").replace("\xa0", " ")

    # Replace special bullet characters with uniform hyphen
    text = re.sub(r"[•▪►✔▪■⇒\u2022\u2023\u2043\u204c\u204d\u2219]", "-", text)

    # Clean header/footer artifacts like "Page 1 of 3" or standalone page numbers
    text = re.sub(r"(?i)page\s+\d+\s+of\s+\d+", "", text)
    text = re.sub(r"(?i)^\s*page\s+\d+\s*$", "", text, flags=re.MULTILINE)

    # Normalize horizontal spaces per line without stripping newlines
    lines = []
    for line in text.splitlines():
        cleaned_line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(cleaned_line)

    # Collapse more than 2 consecutive blank lines into 2
    cleaned_text = "\n".join(lines)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()
    return cleaned_text


def is_scanned_pdf_heuristic(text: str) -> bool:
    """
    Detect if extracted text indicates a scanned or image-only document.
    Returns True if word count < 50 or alphanumeric character ratio is below threshold.
    """
    if not text or not text.strip():
        return True

    words = text.split()
    word_count = len(words)

    if word_count < 50:
        return True

    alpha_num_chars = sum(c.isalnum() for c in text)
    total_chars = len(text)
    ratio = alpha_num_chars / max(total_chars, 1)

    if ratio < 0.35:
        return True

    return False


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract raw text from PDF preserving layout linebreaks using pdfplumber."""
    extracted_lines = []
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(layout=False) or ""
                if page_text.strip():
                    extracted_lines.append(page_text)
    except Exception as exc:
        logger.warning("pdfplumber extraction failed (%s), attempting pypdf fallback", exc)
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                txt = page.extract_text() or ""
                if txt.strip():
                    extracted_lines.append(txt)
        except Exception as err:
            logger.error("All PDF extraction methods failed: %s", err)

    return "\n\n".join(extracted_lines)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract raw text from DOCX document preserving paragraphs and list items."""
    lines = []
    try:
        import docx

        doc = docx.Document(io.BytesIO(file_bytes))
        for p in doc.paragraphs:
            if p.text and p.text.strip():
                # Format bullet items neatly
                prefix = "- " if p.style.name.startswith("List") else ""
                lines.append(f"{prefix}{p.text.strip()}")

        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    lines.append(" | ".join(row_cells))
    except Exception as exc:
        logger.warning("docx extraction failed (%s), trying basic text decode", exc)
        # Basic decode fallback
        lines.append(file_bytes.decode("utf-8", errors="ignore"))

    return "\n".join(lines)


def extract_resume_text(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Phase 1 Pipeline:
    1. Validate size and file extension
    2. Extract raw text based on format
    3. Run scanned document heuristic
    4. Normalize whitespace and noise
    5. Compute content SHA256 hash

    Returns:
        Dict: {"raw_text": str, "content_hash": str, "word_count": int, "filename": str}
    """
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File size exceeds 5MB limit ({len(file_bytes) / (1024*1024):.1f}MB)")

    filename_lower = filename.lower().strip()
    ext = next((e for e in ALLOWED_EXTENSIONS if filename_lower.endswith(e)), "")
    if not ext:
        raise ValueError(f"Unsupported file extension for '{filename}'. Allowed formats: PDF, DOCX, TXT.")

    raw_text = ""
    if ext == ".pdf":
        raw_text = extract_text_from_pdf(file_bytes)
    elif ext == ".docx":
        raw_text = extract_text_from_docx(file_bytes)
    elif ext == ".txt":
        raw_text = file_bytes.decode("utf-8", errors="ignore")

    normalized_text = normalize_text_formatting(raw_text)

    if is_scanned_pdf_heuristic(normalized_text):
        raise ValueError(
            "This looks like a scanned or image-based document. Please upload a text-based PDF or DOCX file."
        )

    words = normalized_text.split()
    content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

    return {
        "raw_text": normalized_text,
        "content_hash": content_hash,
        "word_count": len(words),
        "filename": filename,
        "extension": ext,
    }
