.PHONY: install train predict test lint format run-api run-dashboard docker-up docker-down clean

# ── Installation ──────────────────────────────────────────────────────────────

install:
	pip install -r requirements.txt
	pip install ruff mypy pytest pytest-cov pre-commit
	pre-commit install

install-dev: install
	pip install ipython jupyter

# ── ML Pipeline ───────────────────────────────────────────────────────────────

train:
	python -m ml.train

tune:
	python -m ml.tune

tune-threshold:
	python -m ml.tune_threshold

predict-single:
	python -m ml.predict --mode single

predict-batch:
	python -m ml.predict --mode batch --input data/sample/sample_features.csv

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	pytest

test-coverage:
	pytest --cov=. --cov-report=html --cov-report=term

# ── Linting & Formatting ──────────────────────────────────────────────────────

lint:
	ruff check .

lint-fix:
	ruff check --fix .

format:
	ruff format .

typecheck:
	mypy backend/ api/ ml/

# ── Running ───────────────────────────────────────────────────────────────────

run-api:
	uvicorn api.main:app --reload --port 8000

run-backend:
	uvicorn backend.main:app --reload --port 8000

run-dashboard:
	streamlit run frontend/app.py

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up:
	docker compose up -d

docker-up-build:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-clean:
	docker compose down -v

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov
	rm -rf ml/plots/*.png