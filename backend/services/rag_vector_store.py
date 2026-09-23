from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.services.embedder import generate_embedding, generate_batch_embeddings

logger = logging.getLogger("backend.rag_vector_store")

# In-memory local vector store fallback
_local_vector_db: List[Dict[str, Any]] = []


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def upsert_rag_documents(
    docs: List[Dict[str, Any]], api_key: Optional[str] = None
) -> int:
    """
    Upsert RAG document chunks with text, vector, and metadata into Pinecone or Local Store.

    Args:
        docs: List of dicts with 'id', 'text', and 'metadata'.
        api_key: Optional Pinecone API key.

    Returns:
        Number of documents successfully upserted.
    """
    global _local_vector_db
    if not docs:
        return 0

    texts = [d["text"] for d in docs]
    vectors = generate_batch_embeddings(texts)

    active_key = api_key or settings.PINECONE_API_KEY

    # Try Pinecone upsert if key is available
    if active_key and len(active_key.strip()) > 10:
        try:
            from pinecone import Pinecone

            pc = Pinecone(api_key=active_key)
            index_name = settings.PINECONE_INDEX

            existing = [i["name"] for i in pc.list_indexes()]
            if index_name not in existing:
                try:
                    from pinecone import ServerlessSpec
                    spec = ServerlessSpec(cloud="aws", region=settings.PINECONE_ENV or "us-east-1")
                except Exception:
                    spec = None
                pc.create_index(
                    name=index_name,
                    dimension=384,
                    metric="cosine",
                    spec=spec,
                )

            idx = pc.Index(index_name)
            pinecone_vectors = [
                {
                    "id": d.get("id", f"doc_{i}"),
                    "values": vectors[i],
                    "metadata": {
                        "text": d["text"],
                        **(d.get("metadata") or {}),
                    },
                }
                for i, d in enumerate(docs)
            ]
            idx.upsert(vectors=pinecone_vectors)
            logger.info("Upserted %d documents to Pinecone vector store", len(docs))
        except Exception as e:
            logger.warning("Pinecone upsert failed (%s), storing in local memory fallback", e)

    # Always update local memory vector database for instant fallback retrieval
    for i, d in enumerate(docs):
        doc_id = d.get("id", f"doc_{i}")
        entry = {
            "id": doc_id,
            "vector": vectors[i],
            "text": d["text"],
            "metadata": d.get("metadata") or {},
        }
        # Avoid duplicate IDs in memory
        _local_vector_db = [item for item in _local_vector_db if item["id"] != doc_id]
        _local_vector_db.append(entry)

    logger.info("Upserted %d documents into local RAG vector store", len(docs))
    return len(docs)


def query_rag_context(
    query_text: str,
    top_k: int = 4,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search RAG vector store for top-K context chunks given a query string.

    Args:
        query_text: Input text query.
        top_k: Number of context chunks to retrieve.
        api_key: Optional Pinecone API key.

    Returns:
        List of match dicts: {"id": str, "score": float, "text": str, "metadata": dict}
    """
    query_vector = generate_embedding(query_text)
    active_key = api_key or settings.PINECONE_API_KEY

    # 1. Try Pinecone Retrieval
    if active_key and len(active_key.strip()) > 10:
        try:
            from pinecone import Pinecone

            pc = Pinecone(api_key=active_key)
            index_name = settings.PINECONE_INDEX
            idx = pc.Index(index_name)
            res = idx.query(vector=query_vector, top_k=top_k, include_metadata=True)

            matches = []
            for m in res.get("matches", []):
                meta = m.get("metadata") or {}
                matches.append(
                    {
                        "id": m.get("id"),
                        "score": float(m.get("score", 0.0)),
                        "text": meta.get("text", ""),
                        "metadata": meta,
                    }
                )
            if matches:
                return matches
        except Exception as e:
            logger.warning("Pinecone query failed (%s), querying local vector fallback", e)

    # 2. Local In-Memory Cosine Similarity Search
    scored_items = []
    for item in _local_vector_db:
        score = _cosine_similarity(query_vector, item["vector"])
        scored_items.append(
            {
                "id": item["id"],
                "score": score,
                "text": item["text"],
                "metadata": item["metadata"],
            }
        )

    scored_items.sort(key=lambda x: x["score"], reverse=True)
    return scored_items[:top_k]
