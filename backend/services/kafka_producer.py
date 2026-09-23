"""
Apache Kafka Producer Service - JOB-AI Platform
Streams real-time events for candidate resume processing, job creation, and match score computation.
Includes graceful fallback logging when Kafka cluster is unreachable.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from backend.config import settings

logger = logging.getLogger("backend.services.kafka_producer")

_kafka_producer = None
_kafka_initialized = False


def _get_producer():
    """Lazily initialize Kafka producer instance with fallback support."""
    global _kafka_producer, _kafka_initialized

    if _kafka_initialized:
        return _kafka_producer

    _kafka_initialized = True

    if not settings.KAFKA_ENABLED:
        logger.info("Kafka is disabled in settings. Event producer operating in offline mode.")
        return None

    try:
        from kafka import KafkaProducer  # type: ignore

        _kafka_producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: str(k).encode("utf-8") if k else None,
            acks="all",
            retries=3,
            max_block_ms=2000,
        )
        logger.info("Kafka Producer initialized successfully connected to %s", settings.KAFKA_BOOTSTRAP_SERVERS)
    except Exception as e:
        logger.warning(
            "Kafka cluster unreachable (%s). Event producer switching to offline memory logging.",
            e,
        )
        _kafka_producer = None

    return _kafka_producer


def publish_event(topic: str, event_data: Dict[str, Any], key: Optional[str] = None) -> bool:
    """
    Publish an event payload to a specified Kafka topic.

    Args:
        topic: Destination Kafka topic name.
        event_data: Dictionary payload of the event.
        key: Optional partition key.

    Returns:
        bool: True if sent to Kafka, False if logged locally via fallback.
    """
    producer = _get_producer()

    if producer is not None:
        try:
            future = producer.send(topic, value=event_data, key=key)
            producer.flush(timeout=1.0)
            logger.info("Published Kafka event to topic '%s' with key '%s'", topic, key)
            return True
        except Exception as exc:
            logger.error("Failed to deliver Kafka event to topic '%s': %s", topic, exc)

    # Offline / Fallback log
    logger.info("[EVENT STREAM FALLBACK] Topic: '%s' | Key: %s | Payload: %s", topic, key, event_data)
    return False


def publish_resume_event(resume_id: str, candidate_name: str, skills: list[str], event_type: str = "RESUME_UPLOADED") -> bool:
    """Publish a resume upload or parsing event."""
    payload = {
        "event_type": event_type,
        "resume_id": resume_id,
        "candidate_name": candidate_name,
        "skills": skills,
    }
    return publish_event(settings.KAFKA_TOPIC_RESUME_EVENTS, payload, key=resume_id)


def publish_job_event(job_id: str, title: str, required_skills: list[str], event_type: str = "JOB_POSTED") -> bool:
    """Publish a job posting or update event."""
    payload = {
        "event_type": event_type,
        "job_id": job_id,
        "title": title,
        "required_skills": required_skills,
    }
    return publish_event(settings.KAFKA_TOPIC_JOB_EVENTS, payload, key=job_id)


def publish_match_event(candidate_id: str, job_id: str, match_score: float, matched_skills: list[str]) -> bool:
    """Publish a real-time candidate-job match calculation event."""
    payload = {
        "event_type": "MATCH_CALCULATED",
        "candidate_id": candidate_id,
        "job_id": job_id,
        "match_score": match_score,
        "matched_skills": matched_skills,
    }
    return publish_event(settings.KAFKA_TOPIC_MATCH_EVENTS, payload, key=f"{candidate_id}_{job_id}")
