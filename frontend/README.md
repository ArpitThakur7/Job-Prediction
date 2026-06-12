# JOB-AI-PLATFORM

AI-powered job matching platform using FastAPI, Streamlit, MongoDB, Pinecone, Groq LLM, and XGBoost.

## Tech Stack
- **Backend:** FastAPI, PyMongo, Redis
- **Frontend:** Streamlit
- **ML:** XGBoost, scikit-learn
- **AI:** Groq LLaMA3, LangChain, HuggingFace Embeddings
- **Vector DB:** Pinecone
- **Database:** MongoDB
- **NLP:** spaCy

## Setup

### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/JOB-AI-PLATFORM.git
cd JOB-AI-PLATFORM
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Configure Environment
```bash
cp .env.example .env
# Fill in your API keys in .env
```

### 3. Start Database Services
```bash
docker-compose up -d
```

### 4. Prepare Dataset
```bash
python scripts/prepare_dataset.py
```

### 5. Train ML Model
```bash
python ml/train.py
```

### 6. Run Backend
```bash
uvicorn backend.main:app --reload
```

### 7. Run Frontend
```bash
streamlit run frontend/app.py
```

## API Docs
Visit: http://localhost:8000/docs

## Project Structure
```
JOB_PREDICTION/
├── backend/          FastAPI backend
├── frontend/         Streamlit UI
├── ml/               XGBoost ML pipeline
├── data/             Datasets
├── scripts/          Utility scripts
└── docker-compose.yml
```
