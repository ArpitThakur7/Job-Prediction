import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Note: This project is configured to load all values from `.env` via pydantic-settings.
    In this execution environment, you may need to ensure a `.env` file exists locally
    and that variables are available at runtime.
    """

    model_config = SettingsConfigDict(
        # Load .env from the project root regardless of where uvicorn is launched.
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


    GROQ_API_KEY: str
    PINECONE_API_KEY: str
    PINECONE_INDEX: str = "job-ai-index"
    PINECONE_ENV: str = "us-east-1"

    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "job_ai_db"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    SECRET_KEY: str = "supersecretkey"
    DEBUG: bool = True

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


settings = Settings()
