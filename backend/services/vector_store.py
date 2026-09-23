from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from pinecone import Pinecone

from backend.config import settings

_pinecone_client: Pinecone | None = None


def initialize_pinecone(api_key: Optional[str] = None) -> Pinecone:
    """
    Initialize Pinecone client and ensure index exists.

    Returns:
        Pinecone client instance.
    """
    global _pinecone_client
    active_key = api_key or settings.PINECONE_API_KEY

    if api_key:
        return Pinecone(api_key=api_key)

    if _pinecone_client is not None:
        return _pinecone_client

    if not active_key:
        raise ValueError("Pinecone API key is missing")

    pc = Pinecone(api_key=active_key)

    index_name = settings.PINECONE_INDEX
    existing = [i["name"] for i in pc.list_indexes()]
    if index_name not in existing:
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=pc.describe_index(index_name).get("spec", None)  # type: ignore[arg-type]
            if index_name in existing
            else None,
        )

    _pinecone_client = pc
    try:
        _ = pc.Index(index_name).describe_index_stats()
    except Exception:
        pass

    return _pinecone_client


def _index(api_key: Optional[str] = None) -> Any:
    """
    Get Pinecone index handle.
    """
    pc = initialize_pinecone(api_key=api_key)
    return pc.Index(settings.PINECONE_INDEX)


def upsert_vector(id: str, vector: List[float], metadata: Dict[str, Any], api_key: Optional[str] = None) -> None:
    """
    Upsert a single vector to Pinecone.

    Args:
        id: Vector ID.
        vector: Embedding vector.
        metadata: Metadata dict.
        api_key: Optional API key.
    """
    try:
        _index(api_key=api_key).upsert(vectors=[{"id": id, "values": vector, "metadata": metadata}])
    except Exception:
        return


def upsert_batch(vectors: List[Dict[str, Any]], chunk_size: int = 100) -> None:
    """
    Batch upsert vectors to Pinecone.

    Args:
        vectors: List of dicts in format {"id": str, "values": list[float], "metadata": dict}
        chunk_size: Chunk size for batch upserts.
    """
    if not vectors:
        return
    idx = _index()
    for i in range(0, len(vectors), chunk_size):
        chunk = vectors[i : i + chunk_size]
        payload = [{"id": v["id"], "values": v["values"], "metadata": v.get("metadata", {})} for v in chunk]
        try:
            idx.upsert(vectors=payload)
        except Exception:
            continue


def query_similar(
    vector: List[float],
    top_k: int = 10,
    filter: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Query Pinecone for similar vectors.

    Args:
        vector: Query embedding vector.
        top_k: Top K matches.
        filter: Optional metadata filter.

    Returns:
        List of matches with keys: id, score, metadata.
    """
    try:
        idx = _index(api_key=api_key)
        res = idx.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            filter=filter,
        )
        matches: List[Dict[str, Any]] = []
        for m in res.get("matches", []):
            matches.append(
                {
                    "id": m.get("id"),
                    "score": float(m.get("score", 0.0)),
                    "metadata": m.get("metadata") or {},
                }
            )
        return matches
    except Exception:
        return []


def delete_vector(id: str) -> None:
    """
    Delete a vector from Pinecone by ID.

    Args:
        id: Vector ID.
    """
    try:
        _index().delete(ids=[id])
    except Exception:
        return
