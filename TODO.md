# JOB-AI 3D Platform - System Status & Task Tracker

- [x] Fixed `run.bat` and `stop.bat` Windows CMD trailing backslash escaping and `&` syntax errors
- [x] Implemented robust experience extraction regex that excludes candidate age and DOB patterns
- [x] Fixed MongoDB connection handling with IPv4 (`127.0.0.1`) fallback
- [x] Built multi-tiered matching engine in `matcher.py` with vector search, database fallback, and dataset fallback
- [x] Configured backend startup auto-seeding handler in `main.py`
- [x] Seeded 100 job vectors and resumes to Pinecone and local RAG vector store
- [x] Consolidated all utility scripts into `scripts/` directory and removed loose root scratch files
