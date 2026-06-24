# Automated Answer Sheet Evaluator — Week-by-Week Implementation Plan

> Derived from [docs/plan.md](file:///c:/answersheetevaluator/docs/plan.md). This document expands the milestone table into concrete daily tasks and proposes changes to the original design.

---

## 📋 Session Log

| Date | Session | What was completed | Tests |
|------|---------|-------------------|-------|
| 2026-06-24 | Week 1 Day 1–2 | Full project skeleton: pyproject.toml, .env.example, Makefile, packages/common/{config,logging,enums,schemas}, apps/api/{main,dependencies}, all package stubs, 6 unit tests | ✅ 6/6 pass |

> **Next session:** Start with **Week 1 Day 3** — Database layer (SQLAlchemy ORM + Alembic).
> Command to resume: `uv run pytest tests/unit/ -q` should show 6 passing before starting.

---

---

## Overview

| Week | Theme | Key Deliverable |
|------|-------|-----------------|
| 1 | **Foundation + OCR Pipeline** | Upload → Preprocess → OCR → Store extracted text |
| 2 | **Answer Key Ingestion + RAG** | Teacher uploads key → decompose → embed → retrieve |
| 3 | **LLM Scoring + Confidence** | Student answer → score + reasoning + HITL routing |
| 4 | **Dashboard + Review Workflow** | Next.js web app: review queue, override, export |
| 5 | **Hardening + Evaluation + Demo** | Golden-set metrics, bug fixes, presentation |

---

## Week 1 — Foundation + OCR Pipeline

### Goals
- Bootable monorepo with linting, tests, and environment management
- Upload image/PDF, preprocess with OpenCV, OCR via Google Vision, persist results

### Day-by-Day Breakdown

#### Day 1–2: Project Skeleton
- [x] Initialize `pyproject.toml` with `uv` (or `poetry`) — define all dependency groups
- [x] Create folder structure matching `docs/plan.md` § 1 (apps/, packages/, db/, data/, tests/, scripts/)
- [x] Set up `.env.example` with all required env vars (Google Vision key, LLM keys, DB path)
- [x] Create `packages/common/config.py` — Pydantic `Settings` from `.env`
- [x] Create `packages/common/logging.py` — structured logging with `structlog` or stdlib
- [x] Create `packages/common/enums.py` and `packages/common/schemas.py` — shared Pydantic models
- [x] Wire up `apps/api/main.py` with FastAPI + CORS + `/health` endpoint
- [x] Add a basic `Makefile` or `justfile` with `dev`, `test`, `lint` targets

> **Implementation notes:**
> - Used `uv` (not poetry) — faster and lockfile-native. `uv.lock` committed with 139 packages.
> - `ALLOWED_TEACHER_IDS` is a `str` field + `@property` (not `list[str]`) — pydantic-settings 2.14 JSON-parses list fields which breaks on plain comma strings.
> - Added `servers=[{"url": "http://localhost:8000"}]` to FastAPI — Swagger UI can't connect to `0.0.0.0`.
> - Added schema preview routes (`/api/v1/schema-preview/*`) so all Pydantic models appear in Swagger Schemas panel.
> - **Verified:** 6/6 unit tests pass, server boots, `/health` returns 200, Swagger UI works.

#### Day 3: Database Layer
- [ ] Define SQLAlchemy ORM models in `db/models.py` (all 12 tables from § 2)
- [ ] Set up Alembic for migrations; generate initial migration
- [ ] Create `db/seed/` with sample exam fixture data
- [ ] Add `apps/api/dependencies.py` — DB session dependency injection

#### Day 4–5: OCR Pipeline
- [ ] Implement `packages/ocr/preprocess.py` — deskew, denoise, threshold, crop (OpenCV)
- [ ] Implement `packages/ocr/vision_client.py` — Google Vision API wrapper with retry + caching to `data/ocr_cache/`
- [ ] Implement `packages/ocr/segment.py` — detect question regions from OCR bounding boxes
- [ ] Implement `packages/ocr/question_mapping.py` — assign text blocks to question numbers
- [ ] Implement `packages/ocr/postprocess.py` — merge/clean raw OCR blocks
- [ ] Define `packages/ocr/types.py` — `PreprocessedSheet`, `OCRResult`, `Region`, etc.

#### Day 6–7: API + Integration
- [ ] Create `apps/api/routers/sheets.py` — `POST /answer-sheets` (upload), `GET /answer-sheets/{id}`
- [ ] Create `apps/api/routers/exams.py` — `POST /exams`, `GET /exams/{id}`, `POST /exams/{id}/questions`
- [ ] Implement async job runner (start with `asyncio.create_task` or `BackgroundTasks`; no Celery yet)
- [ ] Wire upload → preprocess → OCR → store pipeline as a background job
- [ ] Create `db/models.py` entry for `processing_jobs` with status tracking
- [ ] Write unit tests: `tests/unit/test_preprocess.py` (deskew, denoise, crop)
- [ ] Write integration test: `tests/integration/test_api_upload_flow.py` (upload → status → answers)
- [ ] Add sample test images to `tests/fixtures/sheet_images/`

### Week 1 Done When
✅ `POST /api/v1/answer-sheets` accepts an image, runs OCR, and `GET /answer-sheets/{id}/answers` returns extracted text with confidence scores.

---

## Week 2 — Answer Key Ingestion + RAG + Concept Extraction

### Goals
- Teacher uploads answer key → system chunks, embeds, stores in vector DB
- Concept decomposition via LLM prompt
- Retrieval returns relevant context for a given student answer

### Day-by-Day Breakdown

#### Day 1–2: Answer Cleaning + Standardization
- [ ] Implement `packages/cleaning/normalize.py` — fix OCR artifacts, standardize whitespace
- [ ] Implement `packages/cleaning/question_splitter.py` — split raw text into per-question segments
- [ ] Implement `packages/cleaning/number_parser.py` — recognize "1.", "Q1", "1)", etc.
- [ ] Write tests: `tests/unit/test_normalize.py`

#### Day 3–4: RAG Ingestion + Embeddings
- [ ] Implement `packages/rag/chunking.py` — chunk answer key by question + semantic boundaries
- [ ] Implement `packages/rag/embeddings.py` — embedding wrapper (OpenAI `text-embedding-3-small` or local `sentence-transformers`)
- [ ] Implement `packages/rag/vectorstore.py` — ChromaDB client, collection management, upsert/delete
- [ ] Implement `packages/rag/ingest.py` — orchestration: answer key → chunks → embed → store
- [ ] Create API: `POST /exams/{id}/answer-key` (upload) and trigger ingestion job
- [ ] Write tests: `tests/unit/test_rag.py`

#### Day 5: Concept Decomposition
- [ ] Implement `packages/llm/client.py` — provider-agnostic LLM wrapper (Claude + GPT via LangChain or `litellm`)
- [ ] Create `packages/llm/prompts/concept_decomposition.md` (from § 5.A)
- [ ] Implement `packages/concepts/decompose.py` — call LLM with concept-decomposition prompt
- [ ] Implement `packages/concepts/rubric_builder.py` — parse JSON response into `ConceptMap`
- [ ] Create API: `POST /exams/{id}/answer-key/decompose`
- [ ] Write tests: `tests/unit/test_concepts.py`

#### Day 6–7: RAG Retrieval + Integration
- [ ] Implement `packages/rag/retriever.py` — build query from question + student answer, retrieve top-k
- [ ] Add reranking logic (optional: cross-encoder reranker or cosine similarity threshold)
- [ ] End-to-end integration test: upload answer key → decompose → embed → retrieve
- [ ] Create `scripts/ingest_answer_key.py` — CLI script for manual ingestion
- [ ] Add sample answer keys to `tests/fixtures/answer_keys/`

### Week 2 Done When
✅ Teacher uploads an answer key → system decomposes into atomic concepts → chunks are embedded in ChromaDB → `retrieve_for_answer(question_id, student_text)` returns relevant context with scores.

---

## Week 3 — LLM Scoring + Confidence Routing

### Goals
- Score each student answer against rubric + retrieved context
- Compute multi-signal confidence and route low-confidence to human review

### Day-by-Day Breakdown

#### Day 1–2: LLM Evaluation Engine
- [ ] Create `packages/llm/prompts/evaluation.md` (from § 5.C)
- [ ] Create `packages/llm/prompts/answer_normalization.md` (from § 5.B)
- [ ] Implement `packages/evaluation/evaluator.py` — assemble prompt, call LLM, parse JSON
- [ ] Implement `packages/evaluation/scorer.py` — score extraction, partial credit logic
- [ ] Define `packages/evaluation/types.py` — `EvaluationResult`, `ScoreBreakdown`
- [ ] Write tests: `tests/unit/test_evaluation.py` (mock LLM responses)

#### Day 3–4: Confidence + Routing
- [ ] Implement `packages/evaluation/confidence.py` — multi-signal confidence aggregation (OCR × retrieval × LLM × rubric)
- [ ] Implement `packages/evaluation/router.py` — threshold-based routing (`>= 0.85` auto, `< 0.65` mandatory review)
- [ ] Create `packages/llm/prompts/review_summarization.md` (from § 5.D)
- [ ] Implement `packages/review/queue.py` — create and manage review queue entries
- [ ] Write tests: `tests/unit/test_confidence.py`

#### Day 5–6: Pipeline Orchestration
- [ ] Wire the full pipeline: upload sheet → OCR → clean → retrieve context → evaluate → route
- [ ] Create API: `POST /answer-sheets/{id}/process` — trigger full pipeline
- [ ] Create API: `GET /evaluations?exam_id=...` — fetch graded results
- [ ] Create API: `GET /review-queue?exam_id=...` — fetch items needing review
- [ ] Store all results in `evaluation_results` and `confidence_flags` tables
- [ ] Add `processing_jobs` status updates throughout the pipeline

#### Day 7: Testing + Debugging
- [ ] Run pipeline on 5–10 sample sheets end-to-end
- [ ] Write integration test: `tests/integration/test_pipeline_end_to_end.py`
- [ ] Tune confidence thresholds based on initial results
- [ ] Fix edge cases: empty answers, out-of-order questions, multi-page merging

### Week 3 Done When
✅ `POST /answer-sheets/{id}/process` runs the full pipeline. `GET /evaluations` returns per-question scores with reasoning. Low-confidence items appear in `GET /review-queue`.

---

## Week 4 — Next.js Web Dashboard + Review Workflow

### Goals
- Teacher-facing Next.js web app for upload, review, override, and export
- Complete HITL loop with audit trail
- Premium, responsive UI with modern design (dark mode, glassmorphism, micro-animations)

> [!NOTE]
> The frontend is a **Next.js (React)** app living in `apps/web/`. It communicates with the FastAPI backend via REST API. All business logic stays in the Python backend — the frontend is purely a presentation layer.

### Revised Project Structure for Frontend

```text
apps/web/                        # Next.js app (replaces Streamlit)
├─ src/
│  ├─ app/                       # App Router pages
│  │  ├─ layout.tsx              # Root layout with sidebar nav + dark mode
│  │  ├─ page.tsx                # Dashboard home / overview
│  │  ├─ exams/
│  │  │  ├─ page.tsx             # List exams
│  │  │  ├─ new/page.tsx         # Create exam + add questions
│  │  │  └─ [examId]/
│  │  │     ├─ page.tsx          # Exam detail: questions, answer key status
│  │  │     ├─ upload/page.tsx   # Upload answer sheets
│  │  │     ├─ results/page.tsx  # Graded results table
│  │  │     ├─ review/page.tsx   # Review queue for this exam
│  │  │     └─ analytics/page.tsx # Score distributions, charts
│  │  └─ review/
│  │     └─ [resultId]/page.tsx  # Side-by-side grading view
│  ├─ components/
│  │  ├─ ui/                     # Reusable UI primitives (Button, Card, Modal, etc.)
│  │  ├─ SheetPreview.tsx        # Image preview with OCR bounding-box overlay
│  │  ├─ ScoreSummaryCard.tsx    # Exam-level summary stats
│  │  ├─ ReviewActions.tsx       # Accept / Override / Skip action bar
│  │  ├─ GradingPanel.tsx        # Side-by-side: image | OCR text | score + reasoning
│  │  ├─ FileUploader.tsx        # Drag-and-drop file upload with progress
│  │  ├─ ConfidenceBadge.tsx     # Color-coded confidence indicator
│  │  └─ ScoreDistribution.tsx   # Chart component (bar/histogram)
│  ├─ lib/
│  │  ├─ api.ts                  # Typed fetch wrapper for FastAPI endpoints
│  │  └─ types.ts                # TypeScript types mirroring Pydantic schemas
│  └─ styles/
│     └─ globals.css             # Design system: tokens, dark mode, animations
├─ public/
├─ next.config.js
├─ package.json
└─ tsconfig.json
```

### Day-by-Day Breakdown

#### Day 1–2: Next.js Shell + Design System + Upload Pages
- [ ] Initialize Next.js app in `apps/web/` with TypeScript, App Router, ESLint
- [ ] Set up design system in `globals.css`: CSS custom properties, dark mode, typography (Inter/Outfit from Google Fonts), color palette, glassmorphism utilities, transition tokens
- [ ] Create root `layout.tsx` — sidebar navigation, teacher selector (from allowlist), dark mode toggle
- [ ] Create `lib/api.ts` — typed fetch wrapper with `X-Teacher-Id` header injection, error handling
- [ ] Create `lib/types.ts` — TypeScript interfaces matching API response shapes
- [ ] Create `exams/page.tsx` — list exams with status badges, "Create Exam" button
- [ ] Create `exams/new/page.tsx` — form: exam title, course code, add questions, upload answer key (drag-and-drop)
- [ ] Create `exams/[examId]/upload/page.tsx` — batch upload answer sheets with progress bar, processing status polling
- [ ] Create `components/FileUploader.tsx` — drag-and-drop zone with file preview, progress animation

#### Day 3–4: Review Queue + Grading View
- [ ] Create `exams/[examId]/review/page.tsx` — filterable, sortable table of items needing review (confidence, question, student)
- [ ] Create `review/[resultId]/page.tsx` — the core grading view:
  - Left panel: sheet image with OCR bounding-box overlay (`SheetPreview.tsx`)
  - Center panel: OCR extracted text + normalized text
  - Right panel: model score, reasoning, matched/missing concepts, confidence badge
- [ ] Create `components/GradingPanel.tsx` — three-column responsive layout
- [ ] Create `components/ReviewActions.tsx` — Accept (✓), Override (✎), Skip (→) buttons with keyboard shortcuts (`a`, `o`, `s`)
- [ ] Create `components/ConfidenceBadge.tsx` — color-coded badge (green ≥0.85, yellow 0.65–0.85, red <0.65)
- [ ] Implement `packages/review/overrides.py` — save teacher overrides to DB
- [ ] Implement `packages/review/audit.py` — log all override actions to `audit_logs`
- [ ] Create API: `POST /evaluations/{id}/override` and `POST /review-queue/bulk-approve`

#### Day 5–6: Results + Analytics + Export
- [ ] Create `exams/[examId]/results/page.tsx` — sortable results table with per-student scores, status chips, CSV download button
- [ ] Create `exams/[examId]/analytics/page.tsx` — score distribution histogram, avg per question, review rate, override rate
- [ ] Create `components/ScoreDistribution.tsx` — bar chart (use lightweight charting: Chart.js or Recharts)
- [ ] Create `components/ScoreSummaryCard.tsx` — card with total graded, avg score, review rate, pass rate
- [ ] Create API: `GET /reports/exams/{id}/export?format=csv` — download final marks
- [ ] Create `scripts/export_results.py` — CLI export utility
- [ ] Write integration test: `tests/integration/test_teacher_override.py`

#### Day 7: Polish + UX
- [ ] Add keyboard shortcuts for review navigation (← → between items, `a`/`o`/`s` for actions)
- [ ] Add loading skeletons and shimmer states for all data-fetching pages
- [ ] Add toast notifications for success/error feedback (override saved, export ready, etc.)
- [ ] Add responsive design breakpoints for tablet and desktop
- [ ] Add micro-animations: page transitions, card hover effects, button press feedback
- [ ] Test the complete teacher workflow end-to-end in the browser

### Week 4 Done When
✅ Teacher can upload exam + answer key, upload student sheets, see auto-graded results, review flagged items with side-by-side grading view, override scores, and export final CSV — all through the Next.js web app.

---

## Week 5 — Hardening, Evaluation, Demo Polish

### Goals
- Run system on golden test set and measure all metrics from § 6
- Fix critical bugs, optimize performance, prepare demo

### Day-by-Day Breakdown

#### Day 1–2: Golden Test Set + Metrics
- [ ] Prepare golden set: 20–30 sheets, 100–200 answer segments with human grades
- [ ] Implement metrics computation: CER, WER, question mapping accuracy, retrieval recall@k, Cohen's kappa, exact/within-1 agreement
- [ ] Run the 3 baselines (keyword overlap, exact match, naive LLM without RAG) on same set
- [ ] Compare system performance against baselines; document results

#### Day 3–4: Bug Fixes + Optimization
- [ ] Fix top failures from golden-set run
- [ ] Add OCR caching to avoid redundant Vision API calls
- [ ] Add embedding caching for answer key re-ingestion
- [ ] Optimize slow queries and add DB indices
- [ ] Add retry/fallback for LLM API failures

#### Day 5–6: Demo Preparation
- [ ] Create `scripts/reprocess_sheet.py` — CLI to rerun pipeline on a sheet
- [ ] Write `README.md` with setup instructions, architecture diagram, and quickstart
- [ ] Write `docs/architecture.md` — system diagram, data flow, component responsibilities
- [ ] Write `docs/api.md` — API reference (can auto-generate from FastAPI OpenAPI schema)
- [ ] Prepare a demo script/walkthrough showing the full flow

#### Day 7: Final Testing + Cleanup
- [ ] Run full test suite; ensure all tests pass
- [ ] Review and clean up code, docstrings, comments
- [ ] Optional: `docker-compose.yml` for one-command deployment
- [ ] Final golden-set run and metrics report

### Week 5 Done When
✅ System runs on golden set with metrics documented, README and docs are complete, demo is rehearsed, and all tests pass.

---

## Suggested Changes & Updates to the Original Plan

> [!IMPORTANT]
> The following are recommendations to strengthen the plan. Some are low-effort quick wins, others are optional enhancements. **Please review and let me know which you'd like to adopt.**

### 1. OCR Fallback Strategy

The plan relies exclusively on **Google Vision API**, which requires an API key and has cost/rate-limit implications.

> [!CAUTION]
> **Do NOT use Tesseract for handwriting.** Tesseract produces near-garbage output on handwritten text, which will cascade into bad cleaning, bad retrieval, and misleading evaluation scores. It is designed for printed/typed text only.

**Suggestion:** Add a local fallback OCR option for handwriting:
- **PaddleOCR** — strong multilingual handwriting support, runs locally, free, well-maintained
- **TrOCR** (via HuggingFace `transformers`) — transformer-based, excellent for English handwriting, heavier but more accurate
- Keep Google Vision as the primary (best handwriting quality + lowest friction), but make the provider configurable
- This makes the project runnable without a Google Cloud account

```python
# packages/common/config.py
class Settings(BaseSettings):
    ocr_provider: Literal["google_vision", "paddle_ocr", "trocr"] = "google_vision"
```

---

### 2. Environment & Dependency Management

The plan mentions `pyproject.toml` but doesn't specify a package manager.

**Suggestion:** Use **`uv`** for fast, deterministic dependency management:
- `uv init` to create the project
- `uv lock` for lockfile-based reproducibility
- `uv run` for running scripts in the project virtualenv
- This is faster and simpler than Poetry for a college project

---

### 3. Authentication & Multi-Tenancy

The plan has a `teacher_id` field but no auth system.

**Suggestion for MVP:** Keep it simple — no OAuth. But **validate `teacher_id` against a hardcoded allowlist** in `.env` so overrides can't be submitted by arbitrary callers:

```env
# .env
ALLOWED_TEACHER_IDS=teacher_ravi,teacher_priya,teacher_amit
```

```python
# packages/common/config.py
class Settings(BaseSettings):
    allowed_teacher_ids: list[str] = []  # comma-separated in .env

# apps/api/dependencies.py
def get_verified_teacher(x_teacher_id: str = Header(...)) -> str:
    if x_teacher_id not in settings.allowed_teacher_ids:
        raise HTTPException(403, "Unknown teacher_id")
    return x_teacher_id
```

- API routes that mutate grades (override, bulk-approve) require `Depends(get_verified_teacher)`
- Next.js sidebar teacher selector picks from the same allowlist (fetched via a `/api/v1/teachers` endpoint or hardcoded in env)
- Audit log always records the validated `teacher_id`

> [!WARNING]
> Without this minimum check, anyone who can hit the API can submit overrides and corrupt your audit trail.

**Post-MVP:** Add simple API key auth or Streamlit's built-in auth.

---

### 4. LLM Provider Abstraction

The plan mentions "Claude/GPT" and LangChain but doesn't specify the abstraction strategy.

**Suggestion:** Use **`litellm`** instead of full LangChain for the LLM layer:
- Simpler API, less boilerplate than LangChain
- `completion(model="claude-sonnet-4-20250514", messages=[...])` works for any provider
- LangChain is heavyweight for what you need (you're not using chains/agents)
- Keep LangChain only if you want its document loaders or text splitters

---

### 5. Missing: Student Roster / Bulk Upload

The plan has `students` table but no API for bulk upload.

**Suggestion:** Add:
- `POST /api/v1/students/bulk` — accept CSV upload for class roster
- Next.js page for CSV upload with preview table and validation
- Auto-match sheets to students by roll number if printed on sheet

---

### 6. Missing: Answer Key Versioning Workflow

The plan mentions `answer_keys.version` but doesn't define the re-evaluation workflow.

**Suggestion:** When a teacher updates the answer key:
1. Create a new `answer_key` version
2. Mark all `evaluation_results` linked to the old version as `stale`
3. Offer a "Re-evaluate with new key" button in the dashboard
4. Store `answer_key_version` on each `evaluation_result` for traceability

---

### 7. Missing: PDF Page Splitting

The plan handles multi-page PDFs but doesn't specify the extraction method.

**Suggestion:** Add `pdf2image` (poppler) or `PyMuPDF` to convert PDF pages to images:
- Split each PDF into per-page images
- Store in `data/uploads/{sheet_id}/page_{n}.png`
- Track in `sheet_pages` table with `image_path` per page

---

### 8. Testing Strategy Gaps

The plan lists test files but doesn't specify mocking strategy for external services.

**Suggestion:**
- Mock Google Vision API responses using `pytest` fixtures with real OCR output snapshots
- Mock LLM responses with canned JSON for deterministic evaluation tests
- Use `pytest-asyncio` for async pipeline tests
- Add `conftest.py` with shared fixtures (DB session, sample exam, sample sheets)

---

### 9. Database: Add Indices

The data model doesn't specify indices, which will matter at scale.

**Suggestion:** Add indices on:
- `extracted_answers(answer_sheet_id, question_id)` — join queries
- `evaluation_results(extracted_answer_id)` — lookup by answer
- `confidence_flags(status)` — filter pending reviews
- `processing_jobs(answer_sheet_id, status)` — job lookup

---

### 10. Missing: Error Recovery / Retry

The plan has `processing_jobs` but doesn't specify what happens when a job fails mid-pipeline.

**Suggestion:**
- Add `retry_count` and `max_retries` to `processing_jobs`
- On failure: log error, set status to `failed`, allow manual retry via API
- Add `POST /api/v1/processing-jobs/{id}/retry` endpoint
- Dashboard shows failed jobs with error message and retry button

---

### 11. Cost Controls

The plan mentions budget blow-up as a risk but doesn't specify controls.

**Suggestion:**
- Add a `daily_api_budget` config with counters
- Track Vision API calls and LLM token usage in `audit_logs`
- Show API usage stats in the analytics dashboard
- Add a hard stop when budget is exceeded (fail gracefully, not silently)

---

### 12. Docker Compose — Promote to Week 1

The plan lists `docker-compose.yml` as optional/late.

**Suggestion:** Create a minimal Docker Compose in Week 1:
- `api` service (FastAPI on port 8000)
- `web` service (Next.js dev server on port 3000, proxying `/api` to the FastAPI service)
- Shared volume for `data/` and SQLite DB
- This ensures consistent dev environments and simplifies the demo

---

## Open Questions

> [!NOTE]
> These decisions will affect implementation details. Please clarify when you can.

1. **Team size?** The plan suggests a 3-person split. Are you working solo or in a team? This affects the weekly pacing.
2. **Google Vision API access?** Do you already have a Google Cloud project with Vision API enabled, or should we plan for PaddleOCR/TrOCR first?
3. **LLM provider preference?** Claude (Anthropic) vs GPT (OpenAI) vs both? Do you have API keys ready?
4. **Embedding model?** Cloud (`text-embedding-3-small`) vs local (`all-MiniLM-L6-v2`)? Local is free but slightly less accurate.
5. **Deployment target?** Local only for the demo, or do you want to deploy to a cloud instance?
6. **Timeline flexibility?** Is 5 weeks fixed, or can it extend? Some suggestions above (Docker, cost controls) could be deferred.
