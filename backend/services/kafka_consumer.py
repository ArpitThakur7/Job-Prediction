"""
Apache Kafka Consumer Service - JOB-AI Platform
Listens to event streams from Kafka topics and processes candidate/job updates asynchronously.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Callable, Dict, Any

from backend.config import settings

logger = logging.getLogger("backend.services.kafka_consumer")

_consumer_thread: threading.Thread | None = None
_stop_consumer_event = threading.Event()


def handle_event(topic: str, payload: Dict[str, Any]) -> None:
    """Default handler logic for incoming Kafka events."""
    event_type = payload.get("event_type", "UNKNOWN")
    logger.info("[KAFKA CONSUMED] Topic: '%s' | Event: '%s' | Payload: %s", topic, event_type, payload)

    # Process specific event types
    if event_type == "RESUME_UPLOADED":
        logger.info("Processing background candidate embedding update for resume ID: %s", payload.get("resume_id"))
    elif event_type == "MATCH_CALCULATED":
        logger.info("Match calculated: Candidate %s <-> Job %s (Score: %s)", payload.get("candidate_id"), payload.get("job_id"), payload.get("match_score"))


def start_kafka_consumer(event_callback: Callable[[str, Dict[str, Any]], None] = handle_event) -> bool:
    """
    Start background thread to consume Kafka messages across topics.

    Args:
        event_callback: Function to invoke for each received message.

    Returns:
        bool: True if consumer loop started, False if Kafka is unavailable.
    """
    global _consumer_thread, _stop_consumer_event

    if not settings.KAFKA_ENABLED:
        logger.info("Kafka is disabled in settings. Skipping consumer start.")
        return False

    if _consumer_thread is not None and _consumer_thread.is_alive():
        logger.info("Kafka consumer thread is already running.")
        return True

    _stop_consumer_event.clear()

    def _consumer_loop():
        try:
            from kafka import KafkaConsumer  # type: ignore

            topics = [
                settings.KAFKA_TOPIC_RESUME_EVENTS,
                settings.KAFKA_TOPIC_MATCH_EVENTS,
                settings.KAFKA_TOPIC_JOB_EVENTS,
            ]

            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                group_id="job_ai_consumer_group",
                consumer_timeout_ms=1000,
            )

            logger.info("Kafka Consumer connected to %s listening on topics: %s", settings.KAFKA_BOOTSTRAP_SERVERS, topics)

            while not _stop_consumer_event.is_set():
                for message in consumer:
                    if _stop_consumer_event.is_set():
                        break
                    try:
                        event_callback(message.topic, message.value)
                    except Exception as err:
                        logger.error("Error processing event from topic %s: %s", message.topic, err)
                time.sleep(0.1)

            consumer.close()
            logger.info("Kafka consumer closed gracefully.")

        except Exception as e:
            logger.warning("Kafka Consumer thread failed to initialize (%s). Running in offline mode.", e)

    _consumer_thread = threading.Thread(target=_consumer_loop, daemon=True, name="KafkaConsumerWorker")
    _consumer_thread.start()
    return True


def stop_kafka_consumer():
    """Stop the background Kafka consumer thread."""
    global _stop_consumer_event
    _stop_consumer_event.set()
