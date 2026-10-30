"""Small text helpers shared by dataset prep and serve-time feature computation."""

from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text: object) -> str:
    """Remove HTML tags / entities but KEEP punctuation (needed for C++, C#, Node.js, CI/CD)."""
    if not isinstance(text, str):
        return ""
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def clean_text(text: object) -> str:
    """
    Aggressive cleaner used for stored dataset text and for anything fed to the
    TF-IDF / embedding similarity (identical at train and serve time).
    """
    if not isinstance(text, str):
        return ""
    text = _TAG_RE.sub(" ", text)
    text = re.sub(r"[^a-zA-Z0-9\s,.\-]", " ", text)
    return _WS_RE.sub(" ", text).strip()
