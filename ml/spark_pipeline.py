"""
Apache Spark Large-Scale Distributed Matching & Feature Extraction Pipeline - JOB-AI Platform
Processes high-volume job descriptions and candidate resumes using PySpark DataFrames and ML pipelines.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Dict, List, Any

logger = logging.getLogger("ml.spark_pipeline")


def get_spark_session(master_url: str = "local[*]", app_name: str = "JOB-AI-Spark-Engine"):
    """
    Initialize or retrieve PySpark Session.

    Args:
        master_url: Master node URL (e.g. spark://localhost:7077 or local[*])
        app_name: Name of the Spark application.
    """
    try:
        from pyspark.sql import SparkSession # type: ignore

        spark = (
            SparkSession.builder.appName(app_name)
            .master(master_url)
            .config("spark.driver.memory", "2g")
            .config("spark.executor.memory", "2g")
            .getOrCreate()
        )
        logger.info("Spark Session created successfully. Master: %s | App: %s", master_url, app_name)
        return spark
    except Exception as e:
        logger.warning("Failed to initialize PySpark Session (%s). Check Java & PySpark installation.", e)
        return None


def run_batch_spark_matching(
    jobs_data: List[Dict[str, Any]],
    resumes_data: List[Dict[str, Any]],
    master_url: str = "local[*]",
) -> List[Dict[str, Any]]:
    """
    Perform distributed PySpark skill matching over batch data.

    Args:
        jobs_data: List of job dicts.
        resumes_data: List of resume dicts.
        master_url: Spark master URL.

    Returns:
        List of calculated match records.
    """
    spark = get_spark_session(master_url=master_url)

    if spark is None:
        logger.info("Spark unavailable. Executing fallback local python batch matching.")
        results = []
        for r in resumes_data:
            r_skills = set(str(s).lower() for s in r.get("skills", []))
            for j in jobs_data:
                j_skills = set(str(s).lower() for s in j.get("skills", []))
                common = r_skills.intersection(j_skills)
                score = len(common) / max(len(j_skills), 1)
                results.append({
                    "candidate_id": r.get("id") or r.get("resume_id"),
                    "job_id": j.get("id") or j.get("job_id"),
                    "match_score": round(score, 4),
                    "matched_skills": list(common),
                    "execution_engine": "Python Fallback",
                })
        return results

    try:
        from pyspark.sql.functions import col, array_intersect, size, round as spark_round # type: ignore

        jobs_df = spark.createDataFrame([
            {
                "job_id": str(j.get("id", j.get("job_id", ""))),
                "job_title": str(j.get("title", "Untitled Job")),
                "job_skills": [str(s).lower() for s in j.get("skills", [])],
            }
            for j in jobs_data
        ])

        resumes_df = spark.createDataFrame([
            {
                "candidate_id": str(r.get("id", r.get("resume_id", ""))),
                "candidate_name": str(r.get("name", "Candidate")),
                "candidate_skills": [str(s).lower() for s in r.get("skills", [])],
            }
            for r in resumes_data
        ])

        # Cross Join candidates x jobs in Spark for distributed score computation
        cross_df = resumes_df.crossJoin(jobs_df)

        matched_df = cross_df.withColumn(
            "matched_skills", array_intersect(col("candidate_skills"), col("job_skills"))
        ).withColumn(
            "match_score",
            spark_round(size(col("matched_skills")) / size(col("job_skills")), 4)
        )

        rows = matched_df.collect()
        results = []
        for r in rows:
            results.append({
                "candidate_id": r["candidate_id"],
                "candidate_name": r["candidate_name"],
                "job_id": r["job_id"],
                "job_title": r["job_title"],
                "match_score": float(r["match_score"]) if r["match_score"] is not None else 0.0,
                "matched_skills": list(r["matched_skills"]),
                "execution_engine": "Apache Spark Cluster",
            })

        logger.info("Spark Batch Job processed %d total candidate-job pairs.", len(results))
        return results

    except Exception as e:
        logger.error("Spark processing error (%s), returning fallback match list", e)
        return []


def main():
    parser = argparse.ArgumentParser(description="Apache Spark Job Matching Pipeline")
    parser.add_argument("--master", type=str, default="local[*]", help="Spark master connection URL")
    args = parser.parse_args()

    sample_jobs = [
        {"id": "job_101", "title": "Senior Python Backend Engineer", "skills": ["python", "fastapi", "docker", "redis", "kafka"]},
        {"id": "job_102", "title": "React Frontend Architect", "skills": ["react", "typescript", "tailwind", "next.js"]},
    ]
    sample_resumes = [
        {"id": "cand_01", "name": "Alice Developer", "skills": ["python", "fastapi", "docker", "postgres"]},
        {"id": "cand_02", "name": "Bob Designer", "skills": ["react", "typescript", "figma", "css"]},
    ]

    print("=" * 60)
    print(" Running Apache Spark Distributed Batch Matching Pipeline...")
    print("=" * 60)

    matches = run_batch_spark_matching(sample_jobs, sample_resumes, master_url=args.master)
    for m in matches:
        print(f"  [+] Engine: {m['execution_engine']} | Score: {m['match_score'] * 100:.1f}%")
        print(f"      Candidate: {m.get('candidate_name', m['candidate_id'])} -> Job: {m.get('job_title', m['job_id'])}")
        print(f"      Matched Skills: {m['matched_skills']}\n")


if __name__ == "__main__":
    main()
