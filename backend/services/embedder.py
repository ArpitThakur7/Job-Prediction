from __future__ import annotations

import hashlib
import logging
import math
from functools import lru_cache
from typing import List, Any

logger = logging.getLogger("backend.services.embedder")

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model: Any = None
_model_failed: bool = False


def _fallback_embedding(text: str, dim: int = 384) -> List[float]:
    """Fallback 384-dim normalized hash vector when SentenceTransformer is unavailable."""
    words = text.lower().split()
    vec = [0.0] * dim
    for word in words:
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _get_model():
    """
    Load and cache the sentence-transformers model.
    Falls back gracefully if torch/transformers versions mismatch.
    """
    global _model, _model_failed
    if _model is None and not _model_failed:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(_MODEL_NAME)
        except Exception as e:
            logger.warning("SentenceTransformer failed to initialize (%s). Using fallback vector encoder.", e)
            _model_failed = True
            _model = None
    return _model


@lru_cache(maxsize=1024)
def _cached_embedding(text: str) -> tuple[float, ...]:
    model = _get_model()
    if model is not None:
        try:
            embedding = model.encode([text], normalize_embeddings=True)[0]
            return tuple(float(x) for x in embedding)
        except Exception as err:
            logger.warning("Model encode failed (%s), using fallback vector.", err)
    return tuple(_fallback_embedding(text))


def generate_embedding(text: str) -> List[float]:
    """
    Generate a 384-dim embedding for a single text (LRU cached).
    """
    return list(_cached_embedding(text))


def generate_batch_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts.
    """
    model = _get_model()
    if model is not None:
        try:
            batch_size = 32
            results: List[List[float]] = []
            for i in range(0, len(texts), batch_size):
                chunk = texts[i : i + batch_size]
                embeddings = model.encode(chunk, normalize_embeddings=True)
                for emb in embeddings:
                    results.append([float(x) for x in emb])
            return results
        except Exception as exc:
            logger.warning("Batch encoding failed (%s), using fallback vectors.", exc)

    return [_fallback_embedding(t) for t in texts]
