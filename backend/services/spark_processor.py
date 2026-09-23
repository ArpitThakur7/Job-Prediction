"""
Apache Spark Processor Integration Service - JOB-AI Platform
Serves PySpark analytics, large-scale feature extraction, and bulk dataset matching to FastAPI services.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from backend.config import settings
from ml.spark_pipeline import run_batch_spark_matching

logger = logging.getLogger("backend.services.spark_processor")


def trigger_spark_batch_matching(
    jobs: List[Dict[str, Any]],
    resumes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Trigger distributed Spark batch candidate matching across jobs and resumes datasets.

    Args:
        jobs: List of job entities.
        resumes: List of candidate resume entities.

    Returns:
        Dict containing match results, summary stats, and engine metadata.
    """
    if not settings.SPARK_ENABLED:
        logger.info("Spark processing is disabled in configuration. Using standard python execution.")

    results = run_batch_spark_matching(
        jobs_data=jobs,
        resumes_data=resumes,
        master_url=settings.SPARK_MASTER_URL if settings.SPARK_ENABLED else "local[*]",
    )

    high_matches = [r for r in results if r.get("match_score", 0.0) >= 0.5]

    return {
        "status": "success",
        "total_pairs_computed": len(results),
        "high_match_count": len(high_matches),
        "results": results,
        "spark_master": settings.SPARK_MASTER_URL if settings.SPARK_ENABLED else "local[*]",
    }
