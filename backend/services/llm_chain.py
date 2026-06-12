from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import Pinecone as PineconeVectorStore
from langchain_groq import ChatGroq
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.memory import BaseMemory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import LLMResult

from backend.config import settings
from backend.embedder import generate_embedding  # type: ignore[attr-defined]
from backend.redis_client import get_redis  # type: ignore[attr-defined]
from backend.services.embedder import generate_embedding as _generate_embedding
from backend.services.vector_store import initialize_pinecone, query_similar

logger = logging.getLogger("backend.llm_chain")


class _EmbeddingAdapter(Embeddings):
    """
    Adapter to let LangChain use our embedding generator.
    """

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query.

        Args:
            text: input query

        Returns:
            embedding vector
        """
        return _generate_embedding(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents.

        Args:
            texts: list of document strings

        Returns:
            list of embedding vectors
        """
        return [list(v) for v in _generate_batch(texts)]

def _generate_batch(texts: List[str]) -> List[List[float]]:
    from backend.services.embedder import generate_batch_embeddings

    return generate_batch_embeddings(texts)


class _RedisConversationMemory(BaseMemory):
    """
    Store last N turns in Redis under a session key.

    This is intentionally lightweight to keep dependencies minimal.
    """

    def __init__(self, session_id: str, k: int = 5) -> None:
        self.session_id = session_id
        self.k = k

    @property
    def memory_variables(self) -> List[str]:
        return ["chat_history"]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load chat history from Redis.

        Returns:
            dict containing "chat_history" as list of messages.
        """
        redis = get_redis()
        key = f"chat:{self.session_id}:history"
        raw = redis.lrange(key, 0, self.k * 2 - 1)  # type: ignore[attr-defined]
        # Each item stored as JSON string
        messages: List[Any] = []
        for item in raw:
            try:
                obj = json.loads(item)
                role = obj.get("role")
                content = obj.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
            except Exception:
                continue
        return {"chat_history": messages}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """
        Save input/output to Redis.
        """
        redis = get_redis()
        key = f"chat:{self.session_id}:history"
        user_q = inputs.get("question") or inputs.get("input") or ""
        assistant_a = outputs.get("answer") or outputs.get("text") or ""

        try:
            redis.rpush(key, json.dumps({"role": "user", "content": user_q}))  # type: ignore[attr-defined]
            redis.rpush(key, json.dumps({"role": "assistant", "content": assistant_a}))  # type: ignore[attr-defined]
            # Trim
            redis.ltrim(key, -self.k * 2, -1)  # type: ignore[attr-defined]
            redis.expire(key, 60 * 60 * 24)  # 24h
        except Exception:
            return

    def clear(self) -> None:
        """
        Clear memory for the session.
        """
        redis = get_redis()
        key = f"chat:{self.session_id}:history"
        try:
            redis.delete(key)
        except Exception:
            return


def build_rag_chain(session_id: str) -> ConversationalRetrievalChain:
    """
    Build ConversationalRetrievalChain using:
    - Groq llama3-8b-8192
    - Pinecone for retrieval
    - Redis for conversation memory (last 5 messages)

    Args:
        session_id: chat session id.

    Returns:
        ConversationalRetrievalChain instance.
    """
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="llama3-8b-8192",
        temperature=0.2,
    )

    # We’ll use Pinecone vector search via our own query_similar function
    # wrapped into a retriever-like callable.
    # LangChain Pinecone integration expects a wrapper; to avoid mismatches we implement
    # a retriever using embeddings + query_similar directly.
    embedding = _EmbeddingAdapter()

    class _Retriever:
        def get_relevant_documents(self, query: str) -> List[Document]:
            vec = embedding.embed_query(query)
            matches = query_similar(vec, top_k=10)
            docs: List[Document] = []
            for m in matches:
                md = m.get("metadata") or {}
                text = md.get("text") or md.get("chunk") or md.get("content") or ""
                docs.append(
                    Document(
                        page_content=text or json.dumps(md),
                        metadata={"id": m.get("id"), **md},
                    )
                )
            return docs

    retriever = _Retriever()
    memory: BaseMemory = _RedisConversationMemory(session_id=session_id, k=5)

    chain: ConversationalRetrievalChain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        return_source_documents=True,
        verbose=False,
    )
    return chain


def ask_question(question: str, session_id: str) -> Dict[str, Any]:
    """
    Ask a question using the RAG chain.

    Args:
        question: user question
        session_id: chat session id

    Returns:
        dict with:
          - answer: string
          - sources: list of metadata dicts (id + metadata)
    """
    chain = build_rag_chain(session_id=session_id)
    try:
        result: Dict[str, Any] = chain({"question": question})
        answer = result.get("answer") or result.get("result") or ""
        source_docs = result.get("source_documents") or []
        sources: List[Dict[str, Any]] = []
        for d in source_docs:
            md = getattr(d, "metadata", None) or {}
            sources.append(md if isinstance(md, dict) else {"source": str(md)})
        return {"answer": str(answer), "sources": sources}
    except Exception as exc:
        logger.exception("ask_question failed: %s", exc)
        return {"answer": "Failed to generate an answer.", "sources": []}
