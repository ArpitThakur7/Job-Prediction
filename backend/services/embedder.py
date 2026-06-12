from __future__ import annotations

from typing import List

from sentence_transformers import SentenceTransformer

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """
    Load and cache the sentence-transformers model.

    Returns:
        SentenceTransformer: model instance.
    """
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def generate_embedding(text: str) -> List[float]:
    """
    Generate a 384-dim embedding for a single text.

    Args:
        text: Input text.

    Returns:
        List[float]: embedding vector.
    """
    model = _get_model()
    embedding = model.encode([text], normalize_embeddings=True)[0]
    return [float(x) for x in embedding]


def generate_batch_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts, processed in chunks of 32.

    Args:
        texts: List of input texts.

    Returns:
        List[List[float]]: embeddings per input text.
    """
    model = _get_model()
    batch_size = 32
    results: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        embeddings = model.encode(chunk, normalize_embeddings=True)
        for emb in embeddings:
            results.append([float(x) for x in emb])
    return results
