from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage, HumanMessage

try:
    from langchain_core.memory import BaseMemory
except ImportError:
    try:
        from langchain.memory import BaseMemory  # type: ignore
    except ImportError:
        from pydantic import BaseModel as BaseMemory  # type: ignore

from backend.config import settings
from backend.redis_client import get_redis  # type: ignore[attr-defined]
from backend.services.embedder import generate_embedding as _generate_embedding
from backend.services.rag_vector_store import query_rag_context

logger = logging.getLogger("backend.llm_chain")

# In-memory session history fallback when Redis is offline
_in_memory_chat_history: Dict[str, List[Dict[str, str]]] = {}


class _EmbeddingAdapter(Embeddings):
    def embed_query(self, text: str) -> List[float]:
        return _generate_embedding(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [list(v) for v in _generate_batch(texts)]


def _generate_batch(texts: List[str]) -> List[List[float]]:
    from backend.services.embedder import generate_batch_embeddings

    return generate_batch_embeddings(texts)


class _DualLayerConversationMemory(BaseMemory):
    """
    Dual-layer conversation memory:
    1. Tries Redis cache ('chat:{session_id}:history')
    2. Fallback to process in-memory dict if Redis is offline/unreachable
    """
    session_id: str
    k: int = 6

    @property
    def memory_variables(self) -> List[str]:
        return ["chat_history"]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        messages: List[Any] = []
        loaded_raw: List[Dict[str, str]] = []

        # 1. Try Redis
        try:
            redis = get_redis()
            if redis is not None:
                key = f"chat:{self.session_id}:history"
                raw = redis.lrange(key, -self.k * 2, -1)  # type: ignore[attr-defined]
                for item in raw:
                    try:
                        obj = json.loads(item)
                        loaded_raw.append(obj)
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("Redis memory load fallback to in-memory dict: %s", e)

        # 2. If Redis returned empty, load from in-memory fallback
        if not loaded_raw and self.session_id in _in_memory_chat_history:
            loaded_raw = _in_memory_chat_history[self.session_id][-self.k * 2:]

        for obj in loaded_raw:
            role = obj.get("role")
            content = obj.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        return {"chat_history": messages}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        u_text = inputs.get("question") or inputs.get("input") or ""
        a_text = outputs.get("answer") or outputs.get("output") or ""

        # Limit in-memory fallback capacity to 500 sessions max to prevent memory leak
        if len(_in_memory_chat_history) > 500:
            first_key = next(iter(_in_memory_chat_history))
            _in_memory_chat_history.pop(first_key, None)

        if self.session_id not in _in_memory_chat_history:
            _in_memory_chat_history[self.session_id] = []
        
        if u_text:
            _in_memory_chat_history[self.session_id].append({"role": "user", "content": u_text})
        if a_text:
            _in_memory_chat_history[self.session_id].append({"role": "assistant", "content": a_text})
        
        # Trim memory history
        _in_memory_chat_history[self.session_id] = _in_memory_chat_history[self.session_id][-self.k * 2:]

        # Try saving to Redis with 24-hour TTL
        try:
            redis = get_redis()
            if redis is not None:
                key = f"chat:{self.session_id}:history"
                if u_text:
                    redis.rpush(key, json.dumps({"role": "user", "content": u_text}))  # type: ignore[attr-defined]
                if a_text:
                    redis.rpush(key, json.dumps({"role": "assistant", "content": a_text}))  # type: ignore[attr-defined]
                redis.ltrim(key, -self.k * 2, -1)  # type: ignore[attr-defined]
                redis.expire(key, 86400)  # 24-hour TTL to prevent stale session growth
        except Exception as e:
            logger.debug("Redis memory save fallback active: %s", e)

    def clear(self) -> None:
        if self.session_id in _in_memory_chat_history:
            _in_memory_chat_history[self.session_id] = []
        try:
            redis = get_redis()
            if redis is not None:
                key = f"chat:{self.session_id}:history"
                redis.delete(key)  # type: ignore[attr-defined]
        except Exception:
            pass


def get_conversation_history_text(session_id: str, max_turns: int = 4) -> str:
    """Helper to extract formatted conversation history text for fallback prompts."""
    mem = _DualLayerConversationMemory(session_id=session_id, k=max_turns)
    vars_dict = mem.load_memory_variables({})
    msgs = vars_dict.get("chat_history", [])
    if not msgs:
        return ""
    lines = []
    for m in msgs:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        lines.append(f"{role}: {m.content}")
    return "\n".join(lines)


def build_llm_instance(
    provider_name: str,
    groq_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
) -> tuple[Any, str]:
    """
    Instantiate LLM for a specified provider. Returns (llm_instance, display_name).
    """
    provider = provider_name.lower().strip()

    if provider == "groq":
        if ChatGroq is None:
            raise ValueError("langchain-groq package not installed")
        key = groq_api_key or settings.GROQ_API_KEY
        if not key or len(key.strip()) < 5:
            raise ValueError("Groq API key missing")
        return (
            ChatGroq(
                api_key=key,
                model="llama-3.1-8b-instant",
                temperature=0.2,
            ),
            "Groq (LLaMA 3.1 8B)",
        )

    elif provider == "gemini":
        if ChatGoogleGenerativeAI is None:
            raise ValueError("langchain-google-genai package not installed")
        key = gemini_api_key or settings.GEMINI_API_KEY
        if not key or len(key.strip()) < 5:
            raise ValueError("Gemini API key missing")
        return (
            ChatGoogleGenerativeAI(
                api_key=key,
                model="gemini-1.5-flash",
                temperature=0.2,
            ),
            "Google Gemini 1.5 Flash",
        )

    elif provider == "openrouter":
        if ChatOpenAI is None:
            raise ValueError("langchain-openai package not installed")
        key = openrouter_api_key or settings.OPENROUTER_API_KEY
        if not key or len(key.strip()) < 5:
            raise ValueError("OpenRouter API key missing")
        return (
            ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=key,
                model="meta-llama/llama-3.1-8b-instruct:free",
                temperature=0.2,
            ),
            "OpenRouter (Llama 3.1 Free)",
        )

    elif provider == "openai":
        if ChatOpenAI is None:
            raise ValueError("langchain-openai package not installed")
        key = openai_api_key or settings.OPENAI_API_KEY
        if not key or len(key.strip()) < 5:
            raise ValueError("OpenAI API key missing")
        return (
            ChatOpenAI(
                api_key=key,
                model="gpt-4o-mini",
                temperature=0.2,
            ),
            "OpenAI (GPT-4o mini)",
        )

    elif provider == "anthropic":
        if ChatAnthropic is None:
            raise ValueError("langchain-anthropic package not installed")
        key = anthropic_api_key or settings.ANTHROPIC_API_KEY
        if not key or len(key.strip()) < 5:
            raise ValueError("Anthropic API key missing")
        return (
            ChatAnthropic(
                api_key=key,
                model="claude-3-5-sonnet-20241022",
                temperature=0.2,
            ),
            "Anthropic (Claude 3.5 Sonnet)",
        )

    else:
        raise ValueError(f"Unknown provider: {provider_name}")


def ask_question(
    question: str,
    session_id: str,
    groq_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
    primary_provider: Optional[str] = "groq",
    pinecone_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute RAG chat query with automatic multi-provider fallback and context memory.
    
    Fallback Order: Primary Provider -> Groq -> Gemini -> OpenRouter -> OpenAI -> Anthropic -> Local RAG Engine
    """
    primary = (primary_provider or "groq").lower().strip()
    
    # Priority candidate sequence (deduplicated)
    all_providers = ["groq", "gemini", "openrouter", "openai", "anthropic"]
    candidate_chain = [primary] + [p for p in all_providers if p != primary]

    embedding = _EmbeddingAdapter()

    from langchain_core.retrievers import BaseRetriever
    from langchain_core.callbacks import CallbackManagerForRetrieverRun

    class CustomRetriever(BaseRetriever):
        embedding: Any
        pinecone_api_key: Optional[str] = None

        def _get_relevant_documents(
            self, query: str, *, run_manager: CallbackManagerForRetrieverRun
        ) -> List[Document]:
            matches = query_rag_context(query, top_k=4, api_key=self.pinecone_api_key)
            docs: List[Document] = []
            for m in matches:
                md = m.get("metadata") or {}
                text = m.get("text") or md.get("text") or ""
                docs.append(
                    Document(
                        page_content=text,
                        metadata={"id": m.get("id"), "score": m.get("score"), **md},
                    )
                )
            return docs

    retriever = CustomRetriever(embedding=embedding, pinecone_api_key=pinecone_api_key)

    # Load conversation history and RAG context ONCE (shared across provider attempts)
    memory = _DualLayerConversationMemory(session_id=session_id, k=5)
    history_vars = memory.load_memory_variables({})
    chat_history_msgs = history_vars.get("chat_history", [])

    # Format conversation history for prompt injection
    history_lines: List[str] = []
    for m in chat_history_msgs:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        history_lines.append(f"{role}: {m.content}")
    history_text = "\n".join(history_lines) if history_lines else "(No prior conversation)"

    # Retrieve relevant RAG documents
    source_docs = retriever.invoke(question)
    context_text = "\n\n".join(d.page_content for d in source_docs if d.page_content.strip())
    if not context_text:
        context_text = "(No relevant documents found)"

    sources: List[Dict[str, Any]] = []
    for d in source_docs:
        md = getattr(d, "metadata", None) or {}
        sources.append(md if isinstance(md, dict) else {"source": str(md)})

    # Build prompt with explicit conversation history + RAG context
    system_prompt = (
        "You are a helpful AI career coach and job search assistant for the JOB-AI Platform. "
        "You have access to relevant document context from the knowledge base and the full "
        "conversation history with the user.\n\n"
        "IMPORTANT RULES:\n"
        "1. Always remember and use information the user has shared in the conversation history.\n"
        "2. If the user told you their name, skills, or preferences, remember and reference them.\n"
        "3. Use the document context to provide data-driven answers when relevant.\n"
        "4. Be concise, helpful, and conversational.\n\n"
        f"=== CONVERSATION HISTORY ===\n{history_text}\n\n"
        f"=== RELEVANT DOCUMENT CONTEXT ===\n{context_text}\n"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}"),
    ])

    # Multi-provider auto-fallback loop
    for provider in candidate_chain:
        try:
            llm, display_name = build_llm_instance(
                provider_name=provider,
                groq_api_key=groq_api_key,
                openai_api_key=openai_api_key,
                anthropic_api_key=anthropic_api_key,
                gemini_api_key=gemini_api_key,
                openrouter_api_key=openrouter_api_key,
            )

            chain = prompt | llm
            result = chain.invoke({"question": question})
            answer = result.content if hasattr(result, "content") else str(result)

            # Save to conversation memory
            memory.save_context({"question": question}, {"answer": answer})

            logger.info("Chat query succeeded using provider: %s", display_name)
            return {
                "answer": str(answer),
                "sources": sources,
                "provider_used": display_name,
                "fallback_triggered": provider != primary,
            }

        except ValueError as ve:
            logger.debug("Provider %s skipped: %s", provider, ve)
            continue
        except Exception as exc:
            logger.warning("Provider %s failed with error (%s). Triggering fallback chain...", provider, exc)
            continue

    # Final Fallback: Local RAG Intelligence Engine (No API key required)
    logger.info("All external LLM providers failed or missing. Triggering Local RAG Intelligence fallback.")
    
    # 1. Fetch relevant vector context with score thresholding (>= 0.40)
    raw_matches = query_rag_context(question, top_k=3, api_key=pinecone_api_key)
    relevant_matches = [m for m in raw_matches if m.get("score", 0.0) >= 0.40]
    
    context_chunks = [m.get("text") or m.get("metadata", {}).get("text", "") for m in relevant_matches if m.get("text")]
    context_str = "\n".join(context_chunks[:2]) if context_chunks else ""

    # 2. Get past conversation history for context memory continuity
    history_str = get_conversation_history_text(session_id=session_id)

    # 3. Intelligent Intent Routing
    ql = question.lower().strip()
    import datetime
    now = datetime.datetime.now()

    local_answer = ""
    if any(k in ql for k in ["date", "today", "time", "day is it", "current date"]):
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        local_answer = f"Today is **{date_str}** ({time_str}).\n\nHow can I help you with your resume analysis, job matching, or career strategy today?"
    elif any(k in ql for k in ["hello", "hi", "hey", "greetings", "who are you", "what can you do", "help"]):
        local_answer = (
            "Hello! I am your **JOB-AI Career Coach & Intelligent Assistant**.\n\n"
            "I can assist you with:\n"
            "• **Resume Optimization**: Tailoring your CV for ATS screening.\n"
            "• **Job Compatibility**: Matching your skills against available positions.\n"
            "• **Interview Prep**: Technical STAR method and system design guidance.\n"
            "• **Salary Advice**: Market compensation and negotiation benchmarks."
        )
    elif "resume" in ql or "cv" in ql:
        local_answer = "To optimize your resume for target positions: Quantify your achievements (e.g. 'boosted throughput by 35%'), ensure core technologies like Python, React, or AWS are explicitly listed in your skills section, and format using clean ATS-friendly headers."
    elif "salary" in ql or "pay" in ql or "compensation" in ql:
        local_answer = "For salary negotiations: Research market benchmarks for your level and location. Postpone giving early numbers, highlight specialized skills, and request compensation breakdown including base, equity, and bonuses."
    elif "interview" in ql or "system design" in ql:
        local_answer = "For technical interviews: Structure answers using the STAR method (Situation, Task, Action, Result). For system design, clarify requirements, state trade-offs, and detail data modeling and scaling strategies."
    else:
        if context_str:
            clean_context = context_str.replace("Required Skills: nan |", "").replace("Required Skills: nan", "")
            local_answer = f"Based on indexed knowledge base:\n\n{clean_context}\n\n**Actionable Advice**: Focus on aligning technical project experience with target job requirements and building domain-specific portfolios."
        else:
            local_answer = "To advance your career journey: Build verifiable projects in high-demand technical areas, keep your online credentials updated, and practice continuous interview preparation. Feel free to ask specific questions about resumes, interview strategies, or job roles!"

    # Save to memory so history context stays intact
    mem = _DualLayerConversationMemory(session_id=session_id, k=5)
    mem.save_context({"question": question}, {"answer": local_answer})

    sources_out = [{"title": m.get("metadata", {}).get("title", "Dataset Context")} for m in relevant_matches if m.get("metadata")]

    return {
        "answer": local_answer,
        "sources": sources_out,
        "provider_used": "Local RAG Engine (Offline Fallback)",
        "fallback_triggered": True,
    }
