# ─── Answer Sheet Evaluator — Makefile ──────────────────────────────────────
# Requires: uv (https://docs.astral.sh/uv/)
# Usage:
#   make install   → create venv + install all dev deps
#   make dev       → start FastAPI in reload mode
#   make test      → run pytest with coverage
#   make lint      → ruff check + format
#   make fmt       → auto-fix formatting
#   make typecheck → mypy static analysis
#   make clean     → remove __pycache__ and .pytest_cache

.PHONY: install dev test lint fmt typecheck clean dirs

# ── Setup ─────────────────────────────────────────────────────────────────────

install:
	uv sync --all-extras

dirs:
	mkdir -p data/uploads data/ocr_cache data/chroma db/seed tests/fixtures/sheet_images tests/fixtures/answer_keys secrets

# ── Dev Server ────────────────────────────────────────────────────────────────

dev: dirs
	uv run uvicorn apps.api.main:app \
		--reload \
		--host 0.0.0.0 \
		--port 8000 \
		--log-level info

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	uv run pytest tests/ -q --tb=short --cov=apps --cov=packages --cov-report=term-missing

test-unit:
	uv run pytest tests/unit/ -q --tb=short

test-integration:
	uv run pytest tests/integration/ -q --tb=short

# ── Lint & Format ──────────────────────────────────────────────────────────────

lint:
	uv run ruff check apps/ packages/ tests/
	uv run ruff format --check apps/ packages/ tests/

fmt:
	uv run ruff check --fix apps/ packages/ tests/
	uv run ruff format apps/ packages/ tests/

# ── Type Checking ─────────────────────────────────────────────────────────────

typecheck:
	uv run mypy apps/ packages/

# ── Housekeeping ──────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

# ── DB Migrations (Alembic — available from Day 3) ────────────────────────────

migrate:
	uv run alembic upgrade head

migration:
	uv run alembic revision --autogenerate -m "$(msg)"
