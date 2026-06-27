<div align="center">

# 🎓 Automated Answer Sheet Evaluator

**An AI-powered grading system for handwritten exam answer sheets**

*OCR → RAG Retrieval → LLM Scoring → Human-in-the-Loop Review*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.138-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Build](https://img.shields.io/badge/Tests-6%20Passing-brightgreen?style=for-the-badge)](tests/)
[![Week](https://img.shields.io/badge/Progress-Week%201%20Day%201--2-blue?style=for-the-badge)](#-progress)

</div>

---

## 📖 What is this project?

This is a **college-project-grade intelligent exam grading system** that automatically evaluates handwritten student answer sheets using a multi-stage AI pipeline:

```
📄 Upload Scanned Sheet
        ↓
🔍 OpenCV Preprocessing  (deskew, denoise, crop)
        ↓
📝 OCR via Google Vision  (extract handwritten text)
        ↓
🧩 RAG Retrieval          (find relevant answer-key context)
        ↓
🤖 LLM Scoring            (Claude/GPT scores against rubric)
        ↓
📊 Confidence Routing     (auto-approve or flag for review)
        ↓
👨‍🏫 Teacher Review UI     (Next.js dashboard for overrides)
        ↓
📤 CSV Export             (final grades)
```

### Why does this exist?

Grading hundreds of handwritten answer sheets is **tedious, inconsistent, and slow**. This system automates the process while keeping a teacher in the loop for uncertain cases — combining the speed of AI with the accuracy of human judgment.

---

## 🏗️ Architecture

```
answersheetevaluator/
│
├── apps/
│   ├── api/                    ← FastAPI backend (Python)
│   │   ├── main.py             ← App entrypoint, CORS, middleware
│   │   ├── dependencies.py     ← Auth + DB session injection
│   │   └── routers/            ← API route modules (Week 1 Day 6-7)
│   └── web/                    ← Next.js dashboard (Week 4)
│
├── packages/                   ← Shared Python packages
│   ├── common/
│   │   ├── config.py           ← All settings via .env
│   │   ├── logging.py          ← Structured logging (structlog)
│   │   ├── enums.py            ← Status enumerations
│   │   └── schemas.py          ← All Pydantic request/response models
│   ├── ocr/                    ← OpenCV + Vision API (Week 1 Day 4-5)
│   ├── rag/                    ← ChromaDB embeddings + retrieval (Week 2)
│   ├── llm/                    ← LiteLLM client + prompts (Week 2-3)
│   ├── evaluation/             ← Scorer + confidence routing (Week 3)
│   ├── cleaning/               ← OCR text normalization (Week 2)
│   ├── concepts/               ← Concept decomposition (Week 2)
│   └── review/                 ← Teacher overrides + audit log (Week 3-4)
│
├── db/                         ← SQLAlchemy ORM + Alembic migrations
├── data/                       ← Runtime uploads, cache, SQLite DB (git-ignored)
├── tests/                      ← pytest suite (unit + integration)
├── scripts/                    ← CLI utilities
├── docs/                       ← Implementation plan, architecture docs
├── pyproject.toml              ← uv project manifest
├── Makefile                    ← Task runner
└── .env.example                ← Environment variable template
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Backend API** | FastAPI 0.138 | Async, auto-docs, type-safe |
| **Language** | Python 3.11+ | Rich ML/AI ecosystem |
| **Config** | Pydantic Settings v2 | Type-safe env var parsing |
| **Logging** | structlog | Structured JSON logs for production |
| **Database** | SQLite → PostgreSQL | Simple local dev, easy scale-up |
| **ORM** | SQLAlchemy 2 + Alembic | Async ORM, migrations |
| **OCR** | Google Vision API + OpenCV | Best handwriting recognition |
| **Vector DB** | ChromaDB | Local-first, no cloud needed |
| **Embeddings** | sentence-transformers | Free local embeddings |
| **LLM** | LiteLLM (Claude/GPT) | Provider-agnostic, swap anytime |
| **Frontend** | Next.js (React) | Rich interactive review UI |
| **Package Mgr** | uv | Fast, lockfile-native |
| **Testing** | pytest + pytest-asyncio | Async test support |
| **Linting** | Ruff | Fast Python linter + formatter |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — install with: `pip install uv`
- Git

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/answersheetevaluator.git
cd answersheetevaluator
```

### 2. Install dependencies

```bash
uv sync --all-extras
```

> This installs all 139 packages including FastAPI, OpenCV, ChromaDB, torch, sentence-transformers, and dev tools. First run takes ~5 minutes (downloads ML packages). Subsequent runs use the cache.

### 3. Configure environment

```bash
cp .env.example .env
```

Then open `.env` and set at minimum:
```env
ALLOWED_TEACHER_IDS=your_name
APP_ENV=development
```

For full functionality, also add:
```env
GOOGLE_APPLICATION_CREDENTIALS=./secrets/google_vision_key.json
ANTHROPIC_API_KEY=your-key-here   # or OPENAI_API_KEY
```

### 4. Start the API server

```bash
# Using Make (if available)
make dev

# Or directly
.venv\Scripts\uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Explore the API

Open **http://localhost:8000/docs** for the interactive Swagger UI.

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/v1/teachers` | List allowed teacher IDs |
| `GET /api/v1/schema-preview/exam` | Example exam data shape |
| `GET /api/v1/schema-preview/evaluation` | Example scored answer with concepts |
| `GET /api/v1/schema-preview/review-queue-item` | Example review queue entry |

### 6. Run tests

```bash
uv run pytest tests/unit/ -q --tb=short
```

Expected: **6 tests passing** ✅

---

## 🗄️ Data Model

The system uses 12 database tables:

```
exams ──────────────────── questions
  │                            │
  ├── answer_keys ─────────── answer_key_chunks (RAG vectors)
  │
  └── answer_sheets ─────────── sheet_pages
            │
            └── extracted_answers (OCR output)
                      │
                      └── evaluation_results (LLM scores)
                                │
                                ├── confidence_flags (review triggers)
                                └── teacher_overrides (human corrections)

processing_jobs  ← pipeline status tracking
audit_logs       ← full action history
students         ← optional student roster
```\n## 🧱 Day 3 – ORM Layer Overview\n\n**What was done today**\n- Implemented a full async SQLAlchemy 2 ORM with **12 tables** covering exams, questions, answer keys, student sheets, OCR pages, extracted answers, processing jobs, evaluation results, confidence flags, and teacher overrides.\n- Added Alembic migration `0001_initial_schema` and applied it to the SQLite database.\n- Created a **seed script** (`scripts/seed_db.py`) that populates a minimal development dataset (1 exam, 3 questions, 3 students, 3 answer sheets).\n- Wrote unit tests (`tests/unit/test_models.py`) confirming imports, table count, and foreign‑key integrity (now 9 tests pass).\n- Updated `AGENTS.md` and the README progress table to mark Day 3 as **DONE**.\n\n**How the ORM layers fit together**\n````\nexams ── questions\n   │        │\n   ├─ answer_keys ── answer_key_chunks   (RAG vectors)\n   │\n   └─ answer_sheets ── sheet_pages\n               │\n               └─ extracted_answers (OCR output)\n                     │\n                     └─ evaluation_results\n                               │\n                               ├─ confidence_flags\n                               └─ teacher_overrides\nprocessing_jobs  ← pipeline status tracking\naudit_logs       ← full action history\nstudents         ← optional student roster\n````\n\n- **Exam** is the root entity. It owns **questions**, an optional **answer key**, and many **answer sheets**.\n- **AnswerKey** is split into **chunks** for vector search (RAG).\n- **AnswerSheet** belongs to a student (optional) and contains multiple **pages** (images). Each page yields **extracted answers** via OCR.\n- Each **ExtractedAnswer** receives an **EvaluationResult** from the LLM. The result can generate **confidence flags** that trigger human review, and a **teacher override** records any manual correction.\n- **ProcessingJob** tracks the background pipeline that runs OCR → RAG → LLM for a sheet.\n\nThese tables provide a clean, normalized schema that supports the end‑to‑end grading pipeline while remaining easy to extend for future features (e.g., analytics, audit logs).

---

## 📡 API Design

The full API (implemented progressively across weeks):

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/exams` | Create exam |
| `POST` | `/api/v1/exams/{id}/answer-key` | Upload answer key |
| `POST` | `/api/v1/answer-sheets` | Upload student sheet |
| `POST` | `/api/v1/answer-sheets/{id}/process` | Start grading pipeline |
| `GET` | `/api/v1/evaluations?exam_id=` | Get graded results |
| `GET` | `/api/v1/review-queue?exam_id=` | Get items needing review |
| `POST` | `/api/v1/evaluations/{id}/override` | Teacher score override |
| `GET` | `/api/v1/reports/exams/{id}/export` | Download CSV grades |

---

## 🔐 Authentication

Simple header-based auth — no OAuth needed for a college project:

1. Teacher IDs are configured in `.env` as `ALLOWED_TEACHER_IDS=teacher_ravi,teacher_priya`
2. Frontend sends `X-Teacher-Id: teacher_ravi` header with every request
3. API validates the ID against the allowlist — 403 if unknown
4. All overrides are logged with the validated teacher ID

---

## 🧪 Confidence & Routing

The system computes a **multi-signal confidence score** for each answer:

```
Final Confidence = f(OCR confidence × Retrieval score × LLM confidence × Rubric match)

≥ 0.85  →  ✅ Auto-approved    (no human review needed)
0.65–0.85 → 🟡 Optional review  (teacher can spot-check)
< 0.65  →  🔴 Mandatory review  (human must verify)
```

---

## 📊 Success Metrics

| Metric | Target |
|--------|--------|
| OCR Character Error Rate | ≤ 20% on clean scans |
| Question Mapping Accuracy | ≥ 90% on structured sheets |
| Retrieval Recall@5 | ≥ 85% |
| Cohen's Kappa vs human | ≥ 0.70 |
| Within-1-mark accuracy | ≥ 85% |
| Review Rate | 10–30% of answers |
| Human Override Rate | ≤ 15–20% |

---

## 📅 Progress

### Week 1 — Foundation + OCR Pipeline

| Day | Status | What |
|-----|--------|------|
| Day 1–2 | ✅ **DONE** | Project skeleton, config, logging, schemas, FastAPI app, 6 tests |
| Day 3 | ✅ **DONE** | SQLAlchemy ORM (12 tables), Alembic migrations, seed data, 9 tests |
| Day 4–5 | ⬜ Pending | OCR pipeline — OpenCV preprocessing, Google Vision wrapper, segmentation |
| Day 6–7 | ⬜ Pending | API routers (sheets, exams), background job runner, integration tests |

### Week 2 — Answer Key Ingestion + RAG

| Day | Status | What |
|-----|--------|------|
| Day 1–2 | ⬜ Pending | OCR cleaning + text normalization |
| Day 3–4 | ⬜ Pending | ChromaDB ingestion, embeddings, vector store |
| Day 5 | ⬜ Pending | LLM concept decomposition |
| Day 6–7 | ⬜ Pending | RAG retrieval + end-to-end ingestion test |

### Week 3 — LLM Scoring + Confidence

| Day | Status | What |
|-----|--------|------|
| Day 1–2 | ⬜ Pending | LLM evaluation engine, scorer |
| Day 3–4 | ⬜ Pending | Confidence routing, review queue |
| Day 5–6 | ⬜ Pending | Full pipeline orchestration |
| Day 7 | ⬜ Pending | End-to-end testing + tuning |

### Week 4 — Next.js Dashboard

| Day | Status | What |
|-----|--------|------|
| Day 1–2 | ⬜ Pending | Next.js shell, design system, upload pages |
| Day 3–4 | ⬜ Pending | Review queue UI, side-by-side grading view |
| Day 5–6 | ⬜ Pending | Results table, analytics, CSV export |
| Day 7 | ⬜ Pending | Polish — animations, keyboard shortcuts, toasts |

### Week 5 — Hardening + Demo

| Day | Status | What |
|-----|--------|------|
| Day 1–2 | ⬜ Pending | Golden test set, metrics computation |
| Day 3–4 | ⬜ Pending | Bug fixes, caching, DB indices |
| Day 5–6 | ⬜ Pending | Demo prep, architecture docs |
| Day 7 | ⬜ Pending | Final test run + cleanup |

---

## 🔧 Development Commands

```bash
# Install dependencies
uv sync --all-extras

# Start API server (auto-reload)
make dev
# or: .venv\Scripts\uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
make test           # all tests with coverage
make test-unit      # unit tests only (fast)

# Lint & format
make lint           # check only
make fmt            # auto-fix

# Type checking
make typecheck

# Database migrations (Week 1 Day 3+)
make migrate        # apply migrations
make migration msg="add answer sheets table"
```

---

## 🌿 Environment Variables

See [`.env.example`](.env.example) for all variables. Key ones:

| Variable | Required | Description |
|----------|----------|-------------|
| `ALLOWED_TEACHER_IDS` | ✅ | Comma-separated teacher IDs (e.g. `ravi,priya`) |
| `APP_ENV` | ✅ | `development` or `production` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Week 1 Day 4+ | Path to Google Vision JSON key |
| `ANTHROPIC_API_KEY` | Week 3+ | Claude API key for LLM scoring |
| `OPENAI_API_KEY` | Week 3+ | OpenAI API key (fallback) |
| `OCR_PROVIDER` | Optional | `google_vision` / `paddle_ocr` / `trocr` |
| `EMBEDDING_PROVIDER` | Optional | `local` (default) or `openai` |

> **⚠️ Never commit your `.env` file.** It's in `.gitignore`. Copy `.env.example` to `.env` and fill in your keys.

---

## 🏃 Project Status

- **Current milestone:** Week 1, Day 1–2 complete
- **Tests passing:** 6/6
- **API server:** Running and interactive Swagger UI available
- **Next step:** Database layer (SQLAlchemy ORM + Alembic migrations)

---

## 🤝 Contributing

This is a college project in active development. The implementation follows [`docs/implementation_plan.md`](docs/implementation_plan.md) day-by-day.

If you're picking up this project as an agent or collaborator, start by reading:
1. [`AGENTS.md`](AGENTS.md) — critical gotchas and working rules
2. [`docs/implementation_plan.md`](docs/implementation_plan.md) — what's done and what's next
3. [`packages/common/schemas.py`](packages/common/schemas.py) — all data shapes

---

## 📄 License

MIT — see [LICENSE](LICENSE)
