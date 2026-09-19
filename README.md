<div align="center">

# 🎓 Automated Answer Sheet Evaluator

**College AI Project — Automated Answer Sheet Evaluator**

*OCR → Answer Key Rubric → Gemini AI Evaluation → Human-in-the-Loop Review → Grade Export*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.138-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## 📖 Project Overview

The **Automated Answer Sheet Evaluator** is a college-level AI application that automates the evaluation of handwritten student answer sheets using optical character recognition (OCR) and generative AI (Google Gemini / LLM evaluation pipeline).

The system allows teachers to define exam questions with ground truth expected answers, upload scanned student answer sheets (PDF, JPG, PNG), evaluate answers automatically against rubrics, review and adjust scores on an interactive dark-themed review UI, and export final grades to CSV.

---

## 🔐 Demo Login Credentials

Use these credentials to test the application:

| Role | Email | Password |
|------|-------|----------|
| **Teacher** | `teacher@scribscore.com` | `teacher123` |
| **Student** | Any email (e.g. `student@scribscore.com`) | Any password |

---

## 🔄 Complete Demo Workflow

```
1. Login (`/login`) 
   └─ Enter Teacher credentials (`teacher@scribscore.com` / `teacher123`).

2. Define Answer Key & Rubric (`/dashboard`)
   └─ Click "Define Answer Key", enter Question Text, Ground Truth Expected Answer, and Max Marks.

3. Upload Answer Sheet (`/upload`)
   └─ Enter Exam ID & Student Roll Number, drag & drop a PDF, JPG, or PNG sheet file.

4. AI Evaluation (`/review`)
   └─ System extracts student text via OCR and evaluates it against the Ground Truth Expected Answer.

5. Review Result & Human-in-the-Loop (`/review`)
   └─ Inspect document preview, extracted text, expected answer, score, AI confidence, and rationale.
   └─ Edit score input and click "Approve Score" or "Flag Issue".

6. Grade Export (`/export`)
   └─ Select Exam ID and click "Download CSV" to export evaluated grades.
```

---

## 🏗️ Architecture & Component Flow

```
┌──────────────────────────────────────────────────────────┐
│                      React UI (Vite)                     │
│    (Login, Dashboard, Rubric Manager, Upload, Review)    │
└────────────────────────────┬─────────────────────────────┘
                             │ REST API (JSON / FormData)
┌────────────────────────────▼─────────────────────────────┐
│                     FastAPI Backend                      │
│             (Routers: exams.py, sheets.py)              │
└──────────────┬─────────────────────────────┬─────────────┘
               │                             │
┌──────────────▼──────────────┐  ┌───────────▼────────────┐
│      SQLite Database        │  │     Google Gemini AI   │
│   (SQLAlchemy ORM Models)   │  │   (OCR & LLM Evaluator)│
└─────────────────────────────┘  └────────────────────────┘
```

---

## 🚀 How to Run the Demo

### Prerequisites
- Node.js (v18+)
- Python (v3.11+)

---

### Step 1: Run the Backend (FastAPI + SQLite)

Open a terminal window in `backend`:

```bash
cd backend

# Option A: Run using virtual environment python (recommended)
.\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# Option B: Run using uv
uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

To re-seed the SQLite database with fresh sample demo data at any time:
```bash
.\.venv\Scripts\python.exe scripts/seed_db.py
```

Backend API Documentation will be available at: **http://localhost:8000/docs**

---

### Step 2: Run the Frontend (React + Vite)

Open a second terminal window in `frontend`:

```bash
cd frontend

# Install Node dependencies (if needed)
npm install

# Start Vite dev server
npm run dev
```

Open your browser at **http://localhost:5173** (or the URL output by Vite).

---

### Step 3: Run Backend Tests & Build Verification

To run unit tests:
```bash
cd backend
.\.venv\Scripts\python.exe -m pytest
```

To verify production frontend build:
```bash
cd frontend
npm run build
```

---

## ⚠️ Limitations

1. **Handwriting OCR Errors:** Highly messy or cursive handwriting may cause OCR misreadings.
2. **Sample Data Scope:** SQLite database is seeded with a compact set of demo exams and student sheets suitable for viva presentation.
3. **AI Scoring Limitations:** LLM scoring is non-deterministic and depends on prompt clarity and rubric quality.

---

## 🔮 Completed Advanced Features

We have successfully implemented the entire original "Future Scope" roadmap:

1. ✅ **Multi-page Answer Sheet Stitching:** Automatic page layout detection and stitching for multi-page answer booklets, allowing students to upload multiple images/PDFs for a single exam.
2. ✅ **Advanced RAG Retrieval:** Integrated ChromaDB vector embeddings for multi-document textbook retrieval, allowing the AI to use syllabus context when grading.
3. ✅ **LMS Integration:** Direct grade sync and export to Canvas, Moodle, and Google Classroom via the Export Dashboard.
4. ✅ **Student Re-evaluation Request Portal:** Students can request score reviews directly from their dashboard, instantly routing the sheet back to the teacher's Review queue with a flag.

---

## 🐳 Docker Deployment

The application is now fully containerized! You can bypass all local environment setup (and Windows AppLocker restrictions) by running the app in Docker.

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. Run the following command in the root directory:
```bash
docker-compose up --build
```
3. The frontend will be available at `http://localhost:3000/answersheetevaluator/` and the backend API at `http://localhost:8000/docs`.
