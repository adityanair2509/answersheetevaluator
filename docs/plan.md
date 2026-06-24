# Automated Answer Sheet Evaluator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

---

## 🚦 Implementation Status (updated after each session)

| Week | Day | Status | What was built |
|------|-----|--------|----------------|
| **Week 1** | Day 1–2 | ✅ **DONE** | Project skeleton — `pyproject.toml` (uv), `.env.example`, `Makefile`, `packages/common/` (config, logging, enums, schemas), `apps/api/main.py` (FastAPI + CORS + /health), `apps/api/dependencies.py`, all package stubs, 6 unit tests passing |
| Week 1 | Day 3 | ⬜ Next | Database layer — SQLAlchemy ORM models (12 tables), Alembic migrations, seed fixtures |
| Week 1 | Day 4–5 | ⬜ Pending | OCR pipeline — OpenCV preprocessing, Vision API wrapper, segmentation |
| Week 1 | Day 6–7 | ⬜ Pending | API routers — sheets.py, exams.py, background jobs, integration tests |
| Week 2 | All | ⬜ Pending | RAG — answer key ingestion, embeddings, ChromaDB, concept decomposition |
| Week 3 | All | ⬜ Pending | LLM scoring, confidence routing, review queue |
| Week 4 | All | ⬜ Pending | Next.js dashboard, HITL review workflow |
| Week 5 | All | ⬜ Pending | Hardening, golden-set metrics, demo |

### Key files to read before continuing
- [`AGENTS.md`](../AGENTS.md) — commands, gotchas, what NOT to do
- [`docs/implementation_plan.md`](implementation_plan.md) — day-by-day task breakdown with checkboxes
- [`packages/common/schemas.py`](../packages/common/schemas.py) — all Pydantic models already defined
- [`packages/common/enums.py`](../packages/common/enums.py) — all status enums

### Decisions made during implementation (diverges from original plan)

| Decision | Original Plan | What was built | Reason |
|----------|--------------|----------------|--------|
| Dashboard | Streamlit | **Next.js (React)** | Better UX, modern design, HITL workflow requires rich UI |
| Package manager | poetry / pip | **uv** | Faster, lockfile-native, simpler |
| List env vars | `list[str]` Pydantic field | **`str` field + `@property`** | pydantic-settings 2.14 JSON-parses list fields; plain string bypasses this |
| Swagger server URL | default (0.0.0.0) | **`servers=[{"url":"http://localhost:8000"}]`** | Browsers can't connect to 0.0.0.0 |

---

**Goal:** Build a college-project-grade system that OCRs handwritten answer sheets, evaluates answers against a teacher-provided answer key with RAG + LLM scoring, and routes uncertain cases to human review.

**Architecture:** Use a Python-first monorepo with a FastAPI backend, Streamlit teacher dashboard, OpenCV preprocessing, Google Vision OCR, local vector search (Chroma/FAISS), and a provider-agnostic LLM layer for Claude/GPT. Keep persistence simple and free-tier friendly with SQLite initially, optional Postgres later, and async job processing for OCR/evaluation so the UI stays responsive.

**Tech Stack:** Python, FastAPI, Streamlit, OpenCV, Google Vision API, LangChain, ChromaDB/FAISS, SQLite/Postgres, SQLAlchemy, Pydantic, pytest, optional Celery/RQ or lightweight in-process jobs.

---

## Assumptions
- Answer sheets are scanned images or PDF pages, mostly one exam per batch.
- Teacher provides the reference answer key and marks scheme.
- Evaluation is rubric-based, not exact-string matching.
- The system scores per question and can support partial credit.
- Free-tier constraints matter, so local storage and local vector DB are preferred during development.

## 1. Project Structure

```text
answer-sheet-evaluator/
├─ apps/
│  ├─ api/
│  │  ├─ main.py
│  │  ├─ routers/
│  │  │  ├─ exams.py
│  │  │  ├─ students.py
│  │  │  ├─ sheets.py
│  │  │  ├─ evaluations.py
│  │  │  ├─ review.py
│  │  │  └─ reports.py
│  │  ├─ dependencies.py
│  │  └─ health.py
│  └─ dashboard/
│     ├─ streamlit_app.py
│     ├─ pages/
│     │  ├─ upload_exam.py
│     │  ├─ upload_sheets.py
│     │  ├─ review_queue.py
│     │  ├─ grading_view.py
│     │  └─ analytics.py
│     └─ components/
│        ├─ sheet_preview.py
│        ├─ score_summary.py
│        └─ review_actions.py
├─ packages/
│  ├─ common/
│  │  ├─ config.py
│  │  ├─ logging.py
│  │  ├─ enums.py
│  │  ├─ schemas.py
│  │  └─ utils.py
│  ├─ ocr/
│  │  ├─ preprocess.py
│  │  ├─ vision_client.py
│  │  ├─ segment.py
│  │  ├─ postprocess.py
│  │  ├─ question_mapping.py
│  │  └─ types.py
│  ├─ cleaning/
│  │  ├─ normalize.py
│  │  ├─ question_splitter.py
│  │  ├─ number_parser.py
│  │  └─ types.py
│  ├─ rag/
│  │  ├─ ingest.py
│  │  ├─ chunking.py
│  │  ├─ embeddings.py
│  │  ├─ vectorstore.py
│  │  ├─ retriever.py
│  │  └─ types.py
│  ├─ concepts/
│  │  ├─ decompose.py
│  │  ├─ rubric_builder.py
│  │  └─ types.py
│  ├─ evaluation/
│  │  ├─ evaluator.py
│  │  ├─ confidence.py
│  │  ├─ scorer.py
│  │  ├─ router.py
│  │  └─ types.py
│  ├─ review/
│  │  ├─ queue.py
│  │  ├─ overrides.py
│  │  └─ audit.py
│  └─ llm/
│     ├─ client.py
│     ├─ prompts/
│     │  ├─ concept_decomposition.md
│     │  ├─ answer_normalization.md
│     │  ├─ evaluation.md
│     │  └─ review_summarization.md
│     └─ models.py
├─ db/
│  ├─ models.py
│  ├─ migrations/
│  └─ seed/
├─ data/
│  ├─ samples/
│  ├─ uploads/
│  ├─ ocr_cache/
│  └─ exports/
├─ tests/
│  ├─ unit/
│  │  ├─ test_preprocess.py
│  │  ├─ test_normalize.py
│  │  ├─ test_rag.py
│  │  ├─ test_concepts.py
│  │  ├─ test_evaluation.py
│  │  └─ test_confidence.py
│  ├─ integration/
│  │  ├─ test_api_upload_flow.py
│  │  ├─ test_pipeline_end_to_end.py
│  │  └─ test_teacher_override.py
│  └─ fixtures/
│     ├─ exam_payloads.py
│     ├─ sheet_images/
│     └─ answer_keys/
├─ scripts/
│  ├─ ingest_answer_key.py
│  ├─ reprocess_sheet.py
│  └─ export_results.py
├─ docs/
│  ├─ architecture.md
│  ├─ api.md
│  ├─ prompts.md
│  └─ sample_data.md
├─ .env.example
├─ pyproject.toml
├─ README.md
└─ docker-compose.yml
```

## 2. Data Model

| Table | Purpose | Key Fields | Notes |
|---|---|---|---|
| `exams` | Exam master record | `id`, `title`, `course_code`, `term`, `teacher_id`, `total_marks`, `status`, `created_at` | One row per exam instance |
| `questions` | Question metadata | `id`, `exam_id`, `question_no`, `text`, `max_marks`, `order_index`, `answer_type`, `rubric_json` | Stores teacher rubric and marks |
| `answer_keys` | Canonical reference answers | `id`, `exam_id`, `source_file`, `raw_text`, `version`, `created_at` | One exam can have multiple versions |
| `answer_key_chunks` | RAG chunks from answer key | `id`, `answer_key_id`, `question_id`, `chunk_text`, `concept_json`, `embedding_ref` | Stores vectorized pieces |
| `students` | Student metadata | `id`, `roll_no`, `name`, `section`, `email`, `created_at` | Optional if sheet has no identity |
| `answer_sheets` | Uploaded sheet batch/item | `id`, `exam_id`, `student_id`, `file_path`, `page_count`, `upload_status`, `ocr_status`, `process_status`, `created_at` | Main processing entity |
| `sheet_pages` | Per-page tracking | `id`, `answer_sheet_id`, `page_no`, `image_path`, `rotation_deg`, `quality_score` | Useful for multipage PDFs |
| `extracted_answers` | OCR + segmentation output | `id`, `answer_sheet_id`, `question_id`, `page_no`, `raw_text`, `normalized_text`, `bbox_json`, `ocr_confidence`, `mapping_confidence` | One row per detected answer block |
| `evaluation_results` | LLM scoring output | `id`, `extracted_answer_id`, `question_id`, `score_awarded`, `max_marks`, `rubric_match_json`, `reasoning`, `llm_confidence`, `final_confidence`, `model_name`, `prompt_version`, `created_at` | Immutable evaluation record |
| `confidence_flags` | Human review triggers | `id`, `evaluation_result_id`, `flag_type`, `flag_reason`, `threshold_value`, `status`, `routed_at` | Example types: low_ocr, low_retrieval, low_llm |
| `teacher_overrides` | Human corrections | `id`, `evaluation_result_id`, `teacher_id`, `override_score`, `override_reason`, `final_comment`, `created_at` | Audit trail for final grade changes |
| `processing_jobs` | Pipeline state | `id`, `answer_sheet_id`, `job_type`, `status`, `error_message`, `started_at`, `ended_at` | Strongly recommended for reliability |
| `audit_logs` | Traceability | `id`, `actor_type`, `actor_id`, `action`, `entity_type`, `entity_id`, `payload_json`, `created_at` | Recommended for college demo and debugging |

### Key Relationships
- `exams 1 -> many questions`
- `exams 1 -> many answer_keys`
- `answer_keys 1 -> many answer_key_chunks`
- `exams 1 -> many answer_sheets`
- `answer_sheets 1 -> many sheet_pages`
- `answer_sheets 1 -> many extracted_answers`
- `extracted_answers 1 -> 1 evaluation_results`
- `evaluation_results 1 -> many confidence_flags`
- `evaluation_results 1 -> 0..1 teacher_overrides`

## 3. Module Breakdown

### A. OCR & Preprocessing Module

| Item | Details |
|---|---|
| Inputs | Raw image/PDF page, exam template metadata, optional page orientation hints |
| Outputs | Deskewed crops, cleaned images, OCR text blocks, bounding boxes, confidence scores |
| Core functions | `preprocess_sheet(image)`, `deskew_image(image)`, `remove_noise(image)`, `detect_page_regions(image)`, `run_google_vision(image)`, `extract_text_blocks(ocr_response)`, `assign_question_regions(blocks, template)` |
| Signatures | `def preprocess_sheet(image: np.ndarray) -> PreprocessedSheet`<br>`def run_google_vision(image: np.ndarray) -> OCRResult`<br>`def detect_question_regions(image: np.ndarray) -> list[Region]` |
| Edge cases | Skewed scans, blur, shadow, page borders missing, rotated pages, multipage PDFs, crossed-out text, diagrams, low handwriting legibility, duplicated OCR tokens |

### B. Answer Standardization / Cleaning Module

| Item | Details |
|---|---|
| Inputs | OCR text blocks, question numbers, question text, OCR confidence |
| Outputs | Cleaned per-question answer text, normalized numbering, segment map |
| Core functions | `normalize_ocr_text(text)`, `standardize_question_labels(text)`, `split_into_answers(text)`, `fix_common_ocr_errors(text)`, `merge_fragmented_answers(parts)` |
| Signatures | `def normalize_answer_text(raw_text: str) -> NormalizedAnswer`<br>`def split_student_answers(raw_text: str) -> list[AnswerSegment]` |
| Edge cases | Missing numbering, merged answers, OCR replacing `1.` with `l.`, duplicate question labels, answer continues across pages, mixed language, bullets and abbreviations |

### C. RAG Ingestion Module

| Item | Details |
|---|---|
| Inputs | Teacher answer key, rubric, question metadata |
| Outputs | Embedded chunks, concept index, retrievable vector records |
| Core functions | `ingest_answer_key()`, `chunk_by_question()`, `extract_concepts()`, `embed_chunks()`, `upsert_vectors()` |
| Signatures | `def ingest_answer_key(answer_key_id: str) -> IngestionResult`<br>`def build_answer_key_chunks(exam_id: str) -> list[Chunk]` |
| Edge cases | Long answers, duplicated rubric points, one chunk containing multiple questions, vector store reindexing after teacher edits |

### D. RAG Retrieval Module

| Item | Details |
|---|---|
| Inputs | Question text, student answer, rubric tags |
| Outputs | Top-k relevant chunks, matching concepts, retrieval scores |
| Core functions | `build_query()`, `retrieve_context()`, `rerank_results()`, `attach_supporting_evidence()` |
| Signatures | `def retrieve_for_answer(question_id: str, student_text: str, k: int = 5) -> RetrievalResult` |
| Edge cases | Wrong question mapping, near-duplicate chunks, sparse answers, semantic mismatch, empty vector store |

### E. Concept Decomposition Module

| Item | Details |
|---|---|
| Inputs | Teacher answer key text, question text, marks scheme |
| Outputs | Atomic concepts, scoring rubric, acceptable variants |
| Core functions | `decompose_answer()`, `extract_atomic_points()`, `assign_weights()`, `build_rubric_json()` |
| Signatures | `def decompose_conceptually(question_text: str, answer_key_text: str, max_marks: float) -> ConceptMap` |
| Edge cases | Vague answers, multiple valid formulations, hidden assumptions, questions with diagrams/code/math, partial credit ambiguity |

### F. LLM Evaluation Module

| Item | Details |
|---|---|
| Inputs | Normalized student answer, retrieved reference context, concept map, rubric |
| Outputs | Score, rationale, matched concepts, missing concepts, confidence |
| Core functions | `evaluate_answer()`, `score_partial_credit()`, `compare_against_rubric()`, `summarize_reasoning()` |
| Signatures | `def evaluate_question_answer(question: Question, student_answer: str, context: RetrievalResult, rubric: ConceptMap) -> EvaluationResult` |
| Edge cases | LLM hallucinating missing facts, over-scoring fluent but incorrect answers, under-scoring valid paraphrases, prompt injection inside student answer |

### G. Confidence Routing / HITL Module

| Item | Details |
|---|---|
| Inputs | OCR confidence, retrieval confidence, LLM confidence, rubric uncertainty, model disagreement |
| Outputs | Auto-accept, auto-reject, mandatory review, review priority |
| Core functions | `compute_final_confidence()`, `route_for_review()`, `set_thresholds()`, `create_review_flag()` |
| Signatures | `def should_route_to_human(result: EvaluationResult) -> bool`<br>`def compute_final_confidence(ocr: float, retrieval: float, llm: float, rubric: float) -> float` |
| Suggested thresholds | `>= 0.85` auto-accept, `0.65-0.85` optional review, `< 0.65` mandatory review |
| Edge cases | High OCR confidence but wrong question mapping, high LLM confidence with weak retrieval, borderline partial-credit answers |

### H. Teacher Review Dashboard Logic

| Item | Details |
|---|---|
| Inputs | Review queue, sheet images, OCR text, model rationale, score suggestions |
| Outputs | Teacher-approved final score, override notes, audit log, exports |
| Core functions | `load_review_queue()`, `render_side_by_side_view()`, `submit_override()`, `bulk_approve()`, `export_results()` |
| Signatures | `def get_pending_reviews(exam_id: str) -> list[ReviewItem]`<br>`def apply_teacher_override(result_id: str, score: float, reason: str) -> OverrideResult` |
| Edge cases | Teacher changing rubric mid-review, concurrent edits, saving partial review state, restoring unfinished batches |

## 4. API Design

| Method | Endpoint | Purpose | Request Shape | Response Shape |
|---|---|---|---|---|
| POST | `/api/v1/exams` | Create exam | `{title, course_code, term, total_marks}` | `{exam_id, status}` |
| GET | `/api/v1/exams/{exam_id}` | Fetch exam details | path param | `{exam, questions, answer_key_status}` |
| POST | `/api/v1/exams/{exam_id}/questions` | Add/update questions | `{question_no, text, max_marks, rubric_json}` | `{question_id}` |
| POST | `/api/v1/exams/{exam_id}/answer-key` | Upload answer key | `multipart/form-data` file + metadata | `{answer_key_id, ingestion_job_id}` |
| POST | `/api/v1/exams/{exam_id}/answer-key/decompose` | Run concept extraction | `{force_rebuild: bool}` | `{chunks_created, concepts_created}` |
| POST | `/api/v1/students` | Create student | `{roll_no, name, section}` | `{student_id}` |
| POST | `/api/v1/answer-sheets` | Upload answer sheet(s) | `multipart/form-data` file(s), `exam_id`, optional `student_id` | `{answer_sheet_id, job_id}` |
| POST | `/api/v1/answer-sheets/{sheet_id}/process` | Start pipeline | `{reprocess: bool}` | `{job_id, status}` |
| GET | `/api/v1/answer-sheets/{sheet_id}` | Get processing status | path param | `{sheet, pages, status, progress}` |
| GET | `/api/v1/answer-sheets/{sheet_id}/answers` | Get extracted answers | path param | `{answers: [...]}` |
| GET | `/api/v1/evaluations?exam_id=...` | Get graded results | query params | `{results: [...], summary}` |
| GET | `/api/v1/review-queue?exam_id=...` | Get low-confidence items | query params | `{items: [...], counts}` |
| POST | `/api/v1/evaluations/{result_id}/override` | Submit teacher override | `{override_score, reason, comment}` | `{final_score, saved: true}` |
| POST | `/api/v1/review-queue/bulk-approve` | Bulk accept reviewed items | `{result_ids: [...]}` | `{updated_count}` |
| GET | `/api/v1/reports/exams/{exam_id}/export?format=csv` | Export grades | query params | file download |
| GET | `/api/v1/health` | Health check | none | `{status: "ok"}` |

### Example request/response shapes

```json
POST /api/v1/answer-sheets
{
  "exam_id": "exam_123",
  "student_id": "stu_456",
  "file_name": "roll12_page1.pdf"
}
```

```json
{
  "answer_sheet_id": "sheet_789",
  "job_id": "job_001",
  "status": "queued"
}
```

```json
POST /api/v1/evaluations/ev_123/override
{
  "override_score": 7.5,
  "reason": "Student used equivalent definition not captured by model",
  "comment": "Accepted after manual check"
}
```

```json
{
  "result_id": "ev_123",
  "final_score": 7.5,
  "saved": true
}
```

## 5. Prompt Library

### A. Concept Decomposition Prompt

```text
SYSTEM:
You are a strict academic rubric decomposition engine.
Your job is to convert a teacher answer key into atomic scoring concepts.
Do not grade the student. Do not invent facts. Do not write verbose explanations.
Return only valid JSON matching the schema.

TASK:
Given a question, its teacher answer key, and the maximum marks, extract the minimal set of atomic concepts needed for full credit.
Each concept must be independently checkable and must support paraphrases and equivalent phrasing.
If the answer key is ambiguous, preserve ambiguity in the rubric instead of resolving it.

OUTPUT JSON SCHEMA:
{
  "question_summary": string,
  "atomic_concepts": [
    {
      "concept": string,
      "importance": "high|medium|low",
      "marks": number,
      "acceptable_variants": [string],
      "must_have": boolean
    }
  ],
  "partial_credit_rules": [
    {
      "rule": string,
      "deduction": number
    }
  ],
  "ambiguities": [string],
  "teacher_notes": [string]
}

USER:
Question:
{{question_text}}

Teacher answer key:
{{answer_key_text}}

Max marks:
{{max_marks}}
```

### B. Answer Normalization Prompt

```text
SYSTEM:
You normalize OCR text from handwritten answer sheets for downstream evaluation.
Preserve meaning. Remove OCR noise. Fix numbering and obvious transcription artifacts.
Do not answer the question. Do not infer missing content beyond what is visible.
Return only valid JSON.

OUTPUT JSON SCHEMA:
{
  "normalized_answer": string,
  "detected_question_refs": [string],
  "cleaned_sections": [
    {
      "label": string,
      "text": string
    }
  ],
  "ocr_issues": [string],
  "confidence_notes": [string]
}

USER:
Question text:
{{question_text}}

Raw OCR text:
{{raw_ocr_text}}

Nearby OCR blocks:
{{neighbor_blocks}}
```

### C. Evaluation Prompt

```text
SYSTEM:
You are an exam answer evaluator.
Score the student answer against the rubric and retrieved reference context.
Use only the provided context.
Be consistent, conservative, and rubric-driven.
If evidence is insufficient, lower the score and flag for review.
Return only valid JSON.

OUTPUT JSON SCHEMA:
{
  "score_awarded": number,
  "max_marks": number,
  "grade_label": "full|partial|minimal|zero",
  "matched_concepts": [string],
  "missing_concepts": [string],
  "reasoning": string,
  "confidence": {
    "llm_confidence": number,
    "reason": string
  },
  "review_flags": [string],
  "final_verdict": "auto_accept|review_needed"
}

USER:
Question:
{{question_text}}

Rubric:
{{rubric_json}}

Retrieved reference context:
{{retrieved_context}}

Student answer:
{{student_answer}}

Scoring rules:
- Give full marks only if the answer covers all must-have concepts.
- Give partial marks for correct but incomplete answers.
- Penalize unsupported claims.
- Prefer rubric over style.
- If the answer is semantically correct but phrased differently, accept it.
```

### D. Review Triage Prompt

```text
SYSTEM:
You decide whether a graded answer must be shown to a teacher.
Be strict. When in doubt, route to human review.
Return only valid JSON.

OUTPUT JSON SCHEMA:
{
  "route": "auto_accept|human_review",
  "reasons": [string],
  "priority": "low|medium|high"
}

USER:
OCR confidence: {{ocr_confidence}}
Retrieval confidence: {{retrieval_confidence}}
LLM confidence: {{llm_confidence}}
Score awarded: {{score_awarded}}
Max marks: {{max_marks}}
Flags: {{review_flags}}
```

## 6. Evaluation Metrics

| Metric | What It Measures | Target for MVP | Why It Matters |
|---|---|---|---|
| OCR Character Error Rate (CER) | Text accuracy from handwriting OCR | `<= 20%` on clean scans | Checks preprocessing + OCR quality |
| OCR Word Error Rate (WER) | End-to-end OCR accuracy | `<= 30%` overall | Helps spot noisy sheets |
| Question Mapping Accuracy | Correct answer-to-question assignment | `>= 90%` on structured sheets | Prevents scoring the wrong answer |
| Retrieval Recall@k | Whether relevant rubric chunks are retrieved | `>= 0.85` at `k=5` | Critical for RAG usefulness |
| Weighted Cohen’s Kappa | Agreement with human grading | `>= 0.70` | Best single grading-quality metric |
| Exact Score Agreement | Same numeric score as human | `>= 60-75%` acceptable for MVP | Good for grade consistency |
| Within-1-Mark Accuracy | Score close to human grade | `>= 85%` | Better for partial-credit tasks |
| Calibration Error (ECE/Brier) | Confidence quality | Lower is better | Needed for HITL routing |
| Review Rate | % sent to teacher | `10-30%` initially | Too high means noisy system |
| Human Override Rate | How often teacher changes score | `<= 15-20%` after tuning | Shows trustworthiness |

### Baseline to compare against
- Baseline 1: keyword overlap scoring.
- Baseline 2: exact-string match against answer key.
- Baseline 3: naive LLM scoring without RAG.
- Your system should clearly beat Baseline 1 and 2, and outperform Baseline 3 on calibration and partial credit.

### Small test set plan
- 20 to 30 answer sheets.
- 3 difficulty bands: neat handwriting, average handwriting, poor handwriting.
- At least 5 question types: definition, explanation, comparison, short derivation, structured list.
- 100 to 200 individual answer segments total.
- Each segment should have human score, rationale, and confidence note.
- Keep one fixed “golden set” for regression testing.

## 7. Milestone Plan

| Week | Deliverable | Done When |
|---|---|---|
| Week 1 | OCR pipeline + project skeleton | Upload a sheet, preprocess it, OCR it, and store extracted text with status tracking |
| Week 2 | Answer key ingestion + RAG + concept extraction | Teacher uploads answer key, system decomposes it, chunks it, embeds it, and retrieves relevant context |
| Week 3 | LLM scoring + confidence routing | Student answer gets a numeric score, reasoning, confidence, and low-confidence cases route to review |
| Week 4 | Streamlit review dashboard + override workflow | Teacher can inspect sheet, edit scores, save overrides, and export final results |
| Week 5 if available | Hardening + evaluation + demo polish | Run on golden set, measure metrics, fix failures, prepare final presentation and report |

### Suggested team split
- Person A: OCR/preprocessing + file pipeline
- Person B: RAG + prompts + evaluation logic
- Person C: Streamlit dashboard + API + persistence

## 8. Risks & Failure Modes

| Risk | What Breaks | Mitigation |
|---|---|---|
| Poor handwriting OCR | Wrong text extracted | Add preprocessing, crop answers, use confidence thresholds, and route uncertain answers to human review |
| Wrong question mapping | Answer scored against wrong rubric | Use explicit question numbering + template-based segmentation + manual review for ambiguous sheets |
| Retrieval mismatch | Relevant rubric not found | Keep question-specific retrieval, use hybrid search if needed, and test recall@k on golden set |
| LLM inconsistency | Same answer gets different scores | Temperature near zero, structured JSON output, rubric-constrained prompts, and retry-on-invalid-output |
| Overconfident hallucinations | Model invents concepts | Force evidence-grounded scoring and penalize unsupported claims |
| Confidence miscalibration | Bad answers auto-accepted | Calibrate on human-labeled validation set and keep review thresholds conservative |
| Multi-page sheet loss | Answers split across pages | Page-level tracking and cross-page answer merging |
| Budget blow-up | API calls cost too much | Cache OCR/embeddings, limit LLM calls to low-confidence or final scoring, and prefer local vector DB |
| Teacher workflow friction | Review UI too slow to use | Side-by-side view, one-click override, bulk approve, and keyboard shortcuts |
| Rubric changes mid-run | Results become stale | Version rubrics and mark old evaluations as needing reprocess |
| Diagram/math-heavy answers | OCR + LLM underperform | Flag for human review or support manual rubric-based grading only |
| Prompt injection in student text | Student content manipulates evaluator | Treat student answers as untrusted input, isolate system prompts, and use strict JSON schema |

## Recommended MVP Scope
- Single exam type.
- Text-heavy handwritten answers only.
- Per-question scoring with partial credit.
- Human review for low-confidence items.
- CSV export for final marks.

If you want, I can turn this into a tighter **week-by-week execution plan with task-level tickets** next.
