"""
ml/semantic.py — resume <-> job semantic similarity, identical at train and serve time.

Backends
--------
* ``minilm``: sentence-transformers ``all-MiniLM-L6-v2`` (CPU only), L2-normalised
  embeddings, cosine similarity. Embeddings are cached on disk in a small SQLite
  file (``ml/cache/minilm_embeddings.sqlite``) keyed by sha1(model + normalised text),
  so the 30k-job training run and repeated serve-time requests only encode a text once.
* ``tfidf``: cosine of the TF-IDF vectors from the vectorizer fitted by
  scripts/prepare_dataset.py (``ml/model/tfidf_vectorizer.pkl``).

Both backends normalise text with :func:`prepare_text` first (same cleaning +
truncation the training data used), so train/serve inputs look alike.
"""

from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import numpy as np

from ml.text_utils import clean_text

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
MINILM_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CACHE_PATH = ROOT / "ml" / "cache" / "minilm_embeddings.sqlite"
DEFAULT_TFIDF_PATH = ROOT / "ml" / "model" / "tfidf_vectorizer.pkl"

#: Max characters fed to either backend. MiniLM truncates at 256 word-pieces
#: (~1000-1200 chars) anyway; the stored job descriptions are capped at 1000.
MAX_CHARS = 1200

_model = None
_model_failed = False
_model_lock = threading.Lock()
_db_lock = threading.Lock()
_tfidf_cache: dict = {}


def prepare_text(text: object, max_chars: int = MAX_CHARS) -> str:
    return clean_text(text)[:max_chars]


# ---------------------------------------------------------------------------
# MiniLM
# ---------------------------------------------------------------------------

def minilm_available() -> bool:
    """True if sentence-transformers can be imported AND the model loads."""
    return _get_model() is not None


def _get_model():
    global _model, _model_failed
    if _model is not None or _model_failed:
        return _model
    with _model_lock:
        if _model is not None or _model_failed:
            return _model
        try:
            from sentence_transformers import SentenceTransformer
            try:
                _model = SentenceTransformer(MINILM_MODEL_NAME, device="cpu", local_files_only=True)
            except Exception:
                _model = SentenceTransformer(MINILM_MODEL_NAME, device="cpu")
            logger.info("Loaded MiniLM (%s) on CPU", MINILM_MODEL_NAME)
        except Exception as exc:  # pragma: no cover - depends on env
            logger.warning("MiniLM unavailable (%s); semantic similarity falls back to TF-IDF.", exc)
            _model_failed = True
            _model = None
    return _model


def _key(text: str) -> str:
    return hashlib.sha1((MINILM_MODEL_NAME + "\x00" + text).encode("utf-8")).hexdigest()


def _connect() -> sqlite3.Connection:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(CACHE_PATH), timeout=30)
    con.execute("CREATE TABLE IF NOT EXISTS emb (k TEXT PRIMARY KEY, v BLOB NOT NULL)")
    return con


def embed_texts(texts: Sequence[str], batch_size: int = 64, show_progress: bool = False) -> np.ndarray:
    """
    Return an (n, 384) float32 array of L2-normalised MiniLM embeddings for ``texts``
    (already passed through :func:`prepare_text`). Uses / fills the disk cache.

    Raises RuntimeError if MiniLM is unavailable.
    """
    model = _get_model()
    if model is None:
        raise RuntimeError("MiniLM model unavailable")
    keys = [_key(t) for t in texts]
    found: dict = {}
    with _db_lock:
        con = _connect()
        try:
            uniq = list(dict.fromkeys(keys))
            for i in range(0, len(uniq), 900):
                chunk = uniq[i:i + 900]
                q = "SELECT k, v FROM emb WHERE k IN (%s)" % ",".join("?" * len(chunk))
                for k, v in con.execute(q, chunk):
                    found[k] = np.frombuffer(v, dtype=np.float32)
        finally:
            con.close()

    missing_idx = {}
    for i, k in enumerate(keys):
        if k not in found and k not in missing_idx:
            missing_idx[k] = i
    if missing_idx:
        miss_texts = [texts[i] for i in missing_idx.values()]
        logger.info("Encoding %d new texts with MiniLM (%d cached)", len(miss_texts), len(found))
        vecs = model.encode(
            miss_texts, batch_size=batch_size, normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=show_progress,
        ).astype(np.float32)
        rows = []
        for k, v in zip(missing_idx.keys(), vecs):
            found[k] = v
            rows.append((k, v.tobytes()))
        with _db_lock:
            con = _connect()
            try:
                con.executemany("INSERT OR REPLACE INTO emb (k, v) VALUES (?, ?)", rows)
                con.commit()
            finally:
                con.close()
    return np.vstack([found[k] for k in keys]) if keys else np.zeros((0, 384), dtype=np.float32)


def minilm_similarity(resume_text: object, job_text: object) -> Optional[float]:
    """Cosine similarity of MiniLM embeddings; None if either text is empty or model missing."""
    a, b = prepare_text(resume_text), prepare_text(job_text)
    if not a or not b or _get_model() is None:
        return None
    try:
        e = embed_texts([a, b])
    except Exception as exc:
        logger.warning("MiniLM similarity failed: %s", exc)
        return None
    return float(np.clip(np.dot(e[0], e[1]), -1.0, 1.0))


def minilm_similarity_many(resume_text: object, job_texts: Iterable[object]) -> List[Optional[float]]:
    """One resume vs many jobs (batched; serve-time ranking)."""
    jt = [prepare_text(t) for t in job_texts]
    a = prepare_text(resume_text)
    if not a or _get_model() is None:
        return [None] * len(jt)
    idx = [i for i, t in enumerate(jt) if t]
    out: List[Optional[float]] = [None] * len(jt)
    if not idx:
        return out
    try:
        e = embed_texts([a] + [jt[i] for i in idx])
    except Exception as exc:
        logger.warning("MiniLM batch similarity failed: %s", exc)
        return out
    sims = e[1:] @ e[0]
    for i, s in zip(idx, sims):
        out[i] = float(np.clip(s, -1.0, 1.0))
    return out


# ---------------------------------------------------------------------------
# TF-IDF
# ---------------------------------------------------------------------------

def load_tfidf(path: Optional[Path] = None):
    p = Path(path) if path else DEFAULT_TFIDF_PATH
    key = str(p)
    if key not in _tfidf_cache:
        try:
            import joblib
            _tfidf_cache[key] = joblib.load(p)
        except Exception as exc:
            logger.warning("TF-IDF vectorizer unavailable at %s (%s)", p, exc)
            _tfidf_cache[key] = None
    return _tfidf_cache[key]


def tfidf_similarity(resume_text: object, job_text: object, vectorizer=None,
                     path: Optional[Path] = None) -> Optional[float]:
    """Cosine of TF-IDF vectors (vectorizer output is L2-normalised, so a dot product)."""
    vec = vectorizer if vectorizer is not None else load_tfidf(path)
    a, b = prepare_text(resume_text, 100_000), prepare_text(job_text, 1000)
    if vec is None or not a or not b:
        return None
    m = vec.transform([a, b])
    return float((m[0] @ m[1].T).toarray()[0, 0])


def clear_tfidf_cache() -> None:
    _tfidf_cache.clear()


__all__ = [
    "CACHE_PATH", "MINILM_MODEL_NAME", "embed_texts", "load_tfidf", "minilm_available",
    "minilm_similarity", "minilm_similarity_many", "prepare_text", "tfidf_similarity",
    "clear_tfidf_cache",
]
