# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-13

### Added
- XGBoost-based job-candidate matching engine with SHAP explainability
- FastAPI backend with JWT authentication, job/resume CRUD, and RAG chatbot
- Streamlit dashboard with 7 pages (Home, Login, Upload Resume, Browse Jobs, Match Results, Chatbot, Analytics)
- Pinecone vector store for semantic search of job/resume embeddings
- Redis caching for session management and chat memory
- Groq-powered AI chatbot using LangChain RAG
- Docker Compose orchestration (API + Dashboard + MongoDB + Redis)
- Optuna hyperparameter tuning pipeline
- Optimal threshold tuning for classification
- PDF resume parsing with spaCy NLP
- Comprehensive training pipeline with cross-validation, ROC curves, confusion matrices, and feature importance plots

### Infrastructure
- Docker multi-service setup with healthchecks
- Pydantic-settings for environment configuration
- CORS middleware for cross-origin requests
- Request timing middleware
- Global exception handler