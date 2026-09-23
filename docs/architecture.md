# Enterprise Scalable Cloud Architecture Specification

## Overview

The **JOB-AI-PLATFORM** is an enterprise-grade, event-driven microservices architecture built for high-throughput candidate matching, real-time RAG career coaching, and distributed big-data analytics.

```mermaid
flowchart TB
    subgraph Clients["Client & Application Layer"]
        REACT["React 19 / Vite UI<br/>(Port 3000)"]
        DASH["Streamlit Analytics<br/>(Port 8501)"]
    end

    subgraph API_GW["API & Ingress Gateway"]
        FA["FastAPI Backend Cluster<br/>(Port 8000)"]
    end

    subgraph Event_Bus["Event Streaming Layer (Apache Kafka)"]
        ZK["Zookeeper Coordination<br/>(Port 2181)"]
        KAFKA["Kafka Event Broker<br/>(Port 9092)"]
        K_PROD["Kafka Producer Service"]
        K_CONS["Kafka Consumer Worker"]
    end

    subgraph BigData_Engine["Distributed Compute Engine (Apache Spark)"]
        SPARK_M["Spark Master Node<br/>(Port 7077 / 8080)"]
        SPARK_W["Spark Worker Nodes<br/>(Port 8081)"]
    end

    subgraph Data_Stores["Persistence & Vector Stores"]
        MG["MongoDB 7<br/>(Primary Store)"]
        RD["Redis 7<br/>(Cache & Chat Memory)"]
        PC["Pinecone / Local Vector DB<br/>(RAG Knowledge Base)"]
    end

    subgraph ML_Engine["Machine Learning Pipeline"]
        XGB["XGBoost Matcher"]
        SHAP["SHAP Explainer"]
        ST["Sentence Transformers"]
    end

    REACT -->|"HTTPS / REST"| FA
    DASH -->|"HTTP"| FA
    FA -->|"Publish Events"| K_PROD
    K_PROD --> KAFKA
    KAFKA --> K_CONS
    K_CONS --> RD
    FA --> MG
    FA --> RD
    FA --> PC
    FA --> XGB
    FA -->|"Batch Compute"| SPARK_M
    SPARK_M --> SPARK_W
```

---

## Component Architecture

### 1. API & Ingress Gateway (`backend/`)
- **Framework**: FastAPI with Pydantic Settings
- **Role**: Entry point for authentication, job CRUD, resume uploads, and live queries.
- **Port**: `8000`

### 2. Real-Time Event Streaming (`Apache Kafka`)
- **Topics**:
  - `job_ai_resume_events`: Streamed upon PDF upload & NLP parsing.
  - `job_ai_job_events`: Streamed when recruiters post target job requirements.
  - `job_ai_match_events`: High-speed event logs for candidate-job compatibility.
- **Producer / Consumer**: [`backend/services/kafka_producer.py`](file:///c:/Users/admin/Desktop/JOB_PREDICTION/backend/services/kafka_producer.py) & [`backend/services/kafka_consumer.py`](file:///c:/Users/admin/Desktop/JOB_PREDICTION/backend/services/kafka_consumer.py).

### 3. Distributed Big-Data Processing (`Apache Spark`)
- **Engine**: PySpark 3.5.0 cluster (`ml/spark_pipeline.py`).
- **Role**: Bulk cross-matching over millions of job-resume pairs, distributed TF-IDF vectorization, and data pipeline ETL.

### 4. Vector DB & RAG Pipeline
- **Vector DB**: Pinecone Cloud with local in-memory cosine similarity fallback.
- **LLM Engine**: Multi-provider fallback chain (Groq → Gemini → OpenRouter → OpenAI → Anthropic → Local RAG Engine).

### 5. Datastores
- **MongoDB 7**: Document store for candidate profiles, resumes, and job listings.
- **Redis 7**: Session cache, conversation history, and rate limiting.

---

## Production Cloud Deployment Topology (AWS / GCP)

For enterprise Kubernetes (EKS / GKE) production deployment:

```
[ CloudFlare CDN / AWS Route53 ]
               │
               ▼
   [ AWS ALB / NGINX Ingress Controller ]
               │
     ┌─────────┴─────────┐
     ▼                   ▼
 [ FastAPI Pods ]    [ React UI Static Pods ]
     │                   │
     ├───────────────────┼──────────────────┐
     ▼                   ▼                  ▼
[ Managed Kafka ]  [ Apache Spark ]  [ Amazon DocumentDB / MongoDB ]
  (AWS MSK)       (EMR / Databricks)
```

1. **Ingress**: AWS ALB / NGINX Ingress with SSL termination.
2. **Compute**: Autoscaling Kubernetes Pods (EKS) for FastAPI backend (HPA target 70% CPU).
3. **Kafka Bus**: AWS MSK (Managed Streaming for Apache Kafka) or Confluent Cloud.
4. **Spark Cluster**: AWS EMR or Databricks cluster for multi-node PySpark batch scoring.
5. **Caching & DB**: AWS ElastiCache for Redis + MongoDB Atlas Cluster.