- [x] Inspect backend settings + existing env template
- [x] Create root `.gitignore` with secrets ignored
- [x] Ensure backend has a `.env` at project root
- [ ] (Optional) Remove/stop committing `frontend/env.example` keys
- [ ] Restart FastAPI: `uvicorn backend.main:app --reload`
- [ ] Verify Pydantic no longer reports missing GROQ_API_KEY / PINECONE_API_KEY


