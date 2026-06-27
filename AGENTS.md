# Agent Instructions

## Repo Shape (as of Week 1 Day 1–2 completion)

The repo is a **live Python monorepo** with a running FastAPI backend. It is no longer empty.

### What exists
```
answersheetevaluator/
├── pyproject.toml          <- uv project; all deps declared (ocr/rag/llm/dev groups)
├── uv.lock                 <- 139 packages locked (DO NOT delete)
├── .venv/                  <- virtualenv installed by uv (do not commit)
├── .env.example            <- template; copy to .env before running
├── Makefile                <- canonical task runner (see commands below)
├── README.md               <- architecture overview + quickstart
├── alembic.ini             <- Alembic config (sqlalchemy.url = sqlite+aiosqlite)
├── alembic/
│   ├── env.py              <- async-compatible Alembic env (imports Base.metadata)
│   └── versions/           <- migration scripts (0001_initial_schema)
├── apps/api/
│   ├── main.py             <- FastAPI app (CORS, lifespan, /health, schema previews)
│   └── dependencies.py     <- get_db() -> AsyncSession + get_verified_teacher()
├── packages/common/
│   ├── config.py           <- Pydantic Settings singleton (get_settings())
│   ├── logging.py          <- structlog configure_logging() + get_logger()
│   ├── enums.py            <- all StrEnums: JobStatus, SheetStatus, ReviewStatus, etc.
│   └── schemas.py          <- all Pydantic v2 request/response models
├── packages/{ocr,rag,llm,evaluation,cleaning,concepts,review}/
│   └── __init__.py         <- stubs only; implementation starts Day 4+
├── db/
│   ├── base.py             <- DeclarativeBase shared by all models + Alembic
│   ├── models.py           <- 12 ORM models (SQLAlchemy 2 Mapped[] syntax)
│   └── session.py          <- async engine, AsyncSessionLocal, get_db(), create_all_tables()
├── data/                   <- runtime data dir (git-ignored); evaluator.db lives here
├── scripts/
│   └── seed_db.py          <- idempotent dev seed (1 exam, 3 questions, 3 students, 3 sheets)
├── tests/
│   ├── conftest.py         <- session-scoped TestClient fixture
│   ├── unit/test_config.py <- 3 tests (settings, teacher IDs, dev flag)
│   ├── unit/test_health.py <- 3 tests (/health, /api/v1/teachers, headers)
│   └── unit/test_models.py <- 3 tests (ORM imports, table count, FK checks)
└── docs/                   <- architecture docs, implementation plan
```

### What does NOT exist yet
- `packages/ocr/*` implementation (Day 4-5)
- `apps/api/routers/` -- sheets.py, exams.py (Day 6-7)
- `apps/web/` -- Next.js dashboard (Week 4)
- Any real data, migrations, or seed fixtures

## Canonical Commands

These commands are confirmed working:

```powershell
# Install all dependencies (already done; uv.lock committed)
uv sync --all-extras

# Start the FastAPI dev server (auto-reload)
.venv\Scripts\uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# Run all unit tests
uv run pytest tests/unit/ -q --tb=short

# Run full test suite with coverage
uv run pytest tests/ -q --tb=short --cov=apps --cov=packages

# Lint
uv run ruff check apps/ packages/ tests/

# Format
uv run ruff format apps/ packages/ tests/
```

> **Windows note:** `make` targets work if GNU Make is installed. Otherwise use the `uv run ...` forms above directly.

## Current Architecture

- **Stack:** Python 3.11+, FastAPI 0.138, Pydantic v2, pydantic-settings 2.14, structlog, SQLAlchemy 2 + Alembic, aiosqlite, ChromaDB, sentence-transformers, litellm, OpenCV, Google Vision API (optional)
- **Frontend:** Next.js (React) in `apps/web/` — **not yet scaffolded**, planned for Week 4
- **Auth:** Header-based teacher allowlist via `X-Teacher-Id` + `ALLOWED_TEACHER_IDS` env var (no OAuth)
- **DB:** SQLite (`data/evaluator.db`) via async SQLAlchemy — ORM models pending Day 3

## Critical Gotchas

1. **`ALLOWED_TEACHER_IDS` env var** — must be a plain comma-separated string (e.g. `teacher_a,teacher_b`). **Do NOT use JSON array syntax** — pydantic-settings 2.14 will JSON-parse list fields and raise `JSONDecodeError`. It is declared as `allowed_teacher_ids_raw: str` in `config.py` with a `@property` that splits on commas.

2. **`uv sync` exit code** — `uv` prints to stderr which PowerShell treats as exit code 1. The install still succeeds. Check the actual output, not the exit code.

3. **Swagger `/docs` server URL** — FastAPI is started with `--host 0.0.0.0` but browsers can't connect to `0.0.0.0`. The `servers=[{"url": "http://localhost:8000"}]` param in `main.py` fixes this. Always keep it.

4. **starlette `StarletteDeprecationWarning`** — cosmetic warning about `httpx` vs `httpx2`. Suppressed in `pyproject.toml` `filterwarnings`. Does not affect test results.

## Working Rules

- **Always run `uv run pytest tests/unit/ -q`** after any change to `packages/common/` or `apps/api/main.py`.
- **Read `packages/common/schemas.py`** before adding new API routes — all request/response shapes are already defined there.
- **Read `packages/common/enums.py`** before using status strings — all enums are `StrEnum` and safe to use as string values.
- **Do not import `settings` at module level in packages/** — always call `get_settings()` inside functions to avoid circular imports during tests.
- Re-check `AGENTS.md`, `docs/implementation_plan.md`, and `README.md` before starting any new day's tasks.

## Verification

After any code change:
1. `uv run python -c "from apps.api.main import app; print('OK:', len(app.routes))"` — confirms the app loads
2. `uv run pytest tests/unit/ -q --tb=short` — confirms 6 tests pass
3. Hit `http://localhost:8000/health` — confirms server responds

