# Contributing to JOB-AI-PLATFORM

Thank you for your interest in contributing! This guide explains the development workflow.

---

## 🧑‍💻 Development Setup

```bash
# Clone the repository
git clone <repo-url>
cd JOB_PREDICTION

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install all dependencies (including dev tools)
pip install -r requirements.txt
pip install ruff mypy pytest pytest-cov pre-commit

# Install pre-commit hooks
pre-commit install
```

## 🧪 Code Quality

This project uses **ruff** for linting/formatting and **mypy** for type checking.

```bash
# Lint your code
ruff check .

# Auto-fix lint issues
ruff check --fix .

# Format code
ruff format .

# Type check
mypy backend/ api/ ml/

# Run all checks at once (CI pipeline)
ruff check . && ruff format --check . && mypy backend/ api/ ml/
```

## ✅ Testing

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=. --cov-report=html --cov-report=term

# Specific test file
pytest tests/unit/test_ml_pipeline.py -v
```

## 📝 Pull Request Checklist

1. **Branch from `main`** and name your branch descriptively:
   - `fix/typo-in-readme`
   - `feat/add-rate-limiting`
   - `refactor/ml-pipeline`

2. **Run all checks** before submitting:
   ```bash
   ruff check .
   ruff format --check .
   mypy backend/ api/ ml/
   pytest
   ```

3. **Write tests** for new functionality

4. **Update documentation** if changing public APIs

5. **Keep PRs small and focused** — one feature/fix per PR

## 📐 Coding Conventions

- **Python 3.10+** type hints required on all function signatures
- **Docstrings** for all public modules, classes, and functions (Google style)
- **Imports**: standard library → third-party → local (separated by blank line)
- **Line length**: 100 characters maximum
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants

Example:

```python
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from backend.config import settings

logger = logging.getLogger(__name__)


def load_model(path: Path) -> Any:
    """Load a serialized model from disk.

    Args:
        path: Path to the model pickle file.

    Returns:
        The deserialized model object.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {path}")
    return joblib.load(path)
```

## 🐳 Docker

```bash
# Build and run with Docker Compose
docker compose up -d --build

# View logs
docker compose logs -f

# Rebuild a single service
docker compose build api
docker compose up -d api
```

## 📋 Reporting Issues

- Use GitHub/GitLab Issues to report bugs or suggest features
- Include:
  - Python version, OS info
  - Steps to reproduce
  - Expected vs actual behavior
  - Full error traceback (if applicable)

## 📄 Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add rate limiting middleware
fix: correct SECRET_KEY loading from .env
docs: update API endpoint documentation
refactor: extract feature validation into separate module
test: add ML pipeline unit tests
chore: update ruff config to v0.7
```

---

Thank you for contributing! 🎉