from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Note: This project is configured to load all values from `.env` via pydantic-settings.
    API keys default to empty strings so the app can boot without a `.env` file;
    features depending on them (Pinecone, Groq) degrade gracefully until configured.
    """

    model_config = SettingsConfigDict(
        # Load .env from the project root regardless of where uvicorn is launched.
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX: str = "job-ai-index"
    PINECONE_ENV: str = "us-east-1"

    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "job_ai_db"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Apache Kafka Event Streaming Settings
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_RESUME_EVENTS: str = "job_ai_resume_events"
    KAFKA_TOPIC_MATCH_EVENTS: str = "job_ai_match_events"
    KAFKA_TOPIC_JOB_EVENTS: str = "job_ai_job_events"
    KAFKA_ENABLED: bool = True

    # Apache Spark Distributed Cluster Settings
    SPARK_MASTER_URL: str = "spark://localhost:7077"
    SPARK_APP_NAME: str = "JOB-AI-Spark-Engine"
    SPARK_ENABLED: bool = True

    # ⚠️ WARNING: Replace this with a random secret for production.
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    SECRET_KEY: str = "supersecretkey"
    DEBUG: bool = True

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


settings = Settings()
