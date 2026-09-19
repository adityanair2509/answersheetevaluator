<div align="center">

# 🎓 Automated Answer Sheet Evaluator
**An Enterprise-Grade, AI-Powered, Human-in-the-Loop Grading Platform**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.138-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-Powered-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

*Revolutionizing the educational ecosystem by bridging state-of-the-art Optical Character Recognition (OCR) and Generative AI (LLMs) to automate and refine the evaluation of handwritten examination papers.*

</div>

---

## 🎯 The Problem Statement

In educational institutions, teachers spend **40% to 50% of their non-teaching hours** manually grading handwritten answer sheets. This process is:
- **Time-Consuming & Repetitive:** Grading hundreds of similar answers leads to fatigue.
- **Prone to Human Bias:** Subjective variations in grading exist between different evaluators.
- **Delayed Feedback:** Students often wait weeks to receive constructive feedback on their performance.

## 💡 Our Solution
The **Automated Answer Sheet Evaluator** serves as an intelligent AI Teaching Assistant. It ingests scanned handwritten answer scripts, extracts text via computer vision, and employs the **Google Gemini Pro LLM** to semantically grade the answers against a teacher-provided ground truth rubric. 

Most importantly, it maintains a **Human-in-the-Loop (HITL)** architecture—meaning the AI suggests a score and rationale, but the final authority to approve, modify, or flag the grade remains strictly with the human educator.

---

## ✨ Comprehensive Feature Suite

### 👨‍🏫 For Educators (Teachers)
- **Dynamic Rubric Generation:** Easily create answer keys by specifying Question Text, Expected Ground Truth, and Maximum Marks.
- **Human-in-the-Loop Review Console:** A beautiful, dark-themed, split-screen UI that displays the original scanned document alongside the AI's extracted text, proposed score, and detailed grading rationale.
- **One-Click Grade Modifications:** Disagree with the AI? Instantly override the score or flag the paper for manual review.
- **Deep Analytics Dashboard:** View overall class performance, highest/lowest scores, and average score distributions.
- **LMS Integration & Export:** Export finalized grades as standard CSV files ready for import into Canvas, Moodle, or Google Classroom.

### 👨‍🎓 For Students
- **Digital Submission Portal:** Seamlessly upload multi-page PDF, JPG, or PNG answer booklets via a smooth drag-and-drop interface.
- **Real-Time Grade Transparency:** View final evaluated scores securely from the student dashboard.
- **Re-evaluation Ticketing:** Initiate requests for re-evaluation if a discrepancy is found, seamlessly routing the paper back to the teacher's priority queue.

### 🤖 Core AI Capabilities
- **Advanced OCR Pipeline:** Handles messy handwriting, skew correction, and noise reduction before text extraction.
- **Context-Aware Semantic Grading:** The LLM doesn't just look for exact keywords; it understands context, synonyms, and logical reasoning to award partial or full marks.
- **RAG-Powered Grading (Retrieval-Augmented Generation):** Integrates with **ChromaDB** to index syllabus materials. The AI cross-references student answers not just with the rubric, but with official textbook contexts.

---

## 🏗️ Deep Dive System Architecture

The application is built on a modern, decoupled microservices architecture.

```mermaid
graph TD
    subgraph Frontend [Frontend - React UI / Vite]
        UI1[Authentication & AuthZ]
        UI2[Teacher Dashboard & Rubrics]
        UI3[HITL Review Console]
        UI4[Student Upload Portal]
    end

    subgraph Backend [Backend - FastAPI (Async)]
        API1[Auth Middleware]
        API2[Document Ingestion & OCR]
        API3[LLM Prompt Engineering Engine]
        API4[RAG Vector Search]
    end
    
    subgraph Storage [Persistent Storage]
        DB[(SQLite / PostgreSQL Relational DB)]
        VDB[(ChromaDB Vector Store)]
        BLOB[(Local Storage / S3 Blob)]
    end

    subgraph External [External AI Services]
        LLM[Google Gemini 1.5 Pro API]
    end

    Frontend <-->|REST API / JSON| Backend
    API1 --> DB
    API2 --> BLOB
    API2 --> LLM
    API3 <--> LLM
    API4 <--> VDB
```

---

## ⚙️ Environment Configuration

To run this project, you must set up the necessary environment variables. Create a `.env` file in the `backend/` directory:

```env
# Server Configuration
ENVIRONMENT=development
PORT=8000

# Authentication (JWT)
SECRET_KEY=your_super_secret_jwt_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database
DATABASE_URL=sqlite+aiosqlite:///./auto_sheet.db

# AI & LLM Integration
GEMINI_API_KEY=your_google_gemini_api_key_here

# File Storage
UPLOAD_DIR=data/uploads
```

---

## 🚀 Getting Started & Installation

You can deploy the application seamlessly using Docker (Recommended) or set it up natively.

### Option A: 🐳 Docker Deployment (Zero-Config)
The fastest and safest way to get started without polluting your local environment.

```bash
# 1. Clone the repository
git clone https://github.com/your-username/AUTO_SHEET_EVALUATOR.git
cd AUTO_SHEET_EVALUATOR

# 2. Build and spin up the containers
docker-compose up --build -d
```
- **Frontend Application:** `http://localhost:3000/answersheetevaluator/`
- **Backend Swagger API Docs:** `http://localhost:8000/docs`

---

### Option B: 💻 Native Local Setup

#### 1. Backend Setup (FastAPI)
Requires Python 3.11+ and the lightning-fast [`uv`](https://docs.astral.sh/uv/) package manager.

```bash
cd backend

# Install dependencies and sync virtual environment
uv sync --all-extras

# Seed the database with sample demo data (optional but recommended)
uv run python scripts/seed_db.py

# Start the ASGI server
uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Frontend Setup (React)
Requires Node.js v18+.

```bash
cd frontend

# Install Node modules
npm install

# Start the Vite development server
npm run dev
```
Navigate to `http://localhost:5173` to experience the UI.

---

## 📂 Project Directory Structure

```text
AUTO_SHEET_EVALUATOR/
├── backend/
│   ├── apps/
│   │   ├── api/            # FastAPI Routers (Exams, Sheets, Auth)
│   │   └── models/         # SQLAlchemy ORM Models
│   ├── packages/
│   │   ├── ocr/            # Vision and OCR Extraction Logic
│   │   ├── llm/            # Gemini Prompt Engineering & Parsing
│   │   └── rag/            # ChromaDB Vector Embeddings Logic
│   ├── tests/              # Pytest Unit & Integration Tests
│   ├── scripts/            # Database Seeding & Maintenance scripts
│   ├── pyproject.toml      # UV/Pip dependencies
│   └── Makefile            # Dev shortcuts
├── frontend/
│   ├── src/
│   │   ├── components/     # Reusable React UI Components (Sidebar, Cards)
│   │   ├── pages/          # Full Views (Dashboard, Review Console, Login)
│   │   ├── api/            # Axios API Client configurations
│   │   └── utils/          # Helper functions (PDF extraction, formatting)
│   ├── package.json        # Node dependencies
│   └── vite.config.js      # Vite build configuration
├── docker-compose.yml      # Orchestration file
└── README.md
```

---

## 🔐 Default Demo Credentials

For testing purposes, the database seeding script provides the following accounts:

| Persona | Email Address | Password | Role Description |
|---------|---------------|----------|------------------|
| **Administrator/Teacher** | `teacher@scribscore.com` | `teacher123` | Full access to create exams, review sheets, and export analytics. |
| **Student** | `student@scribscore.com` | *Any password* | Restricted access. Can upload answers and view published scores. |

---

## 🔮 Future Scope & Roadmap

While the system currently boasts state-of-the-art capabilities, our roadmap for V2 includes:
1. **Mathematical Equation Parsing:** Upgrading OCR to reliably parse LaTeX and complex handwritten calculus formulas.
2. **Plagiarism Detection:** Utilizing ChromaDB to compare student answer semantic embeddings against one another to flag potential cheating.
3. **Multi-LLM Fallback:** Introducing load-balancing between Google Gemini, OpenAI GPT-4o, and Anthropic Claude 3.5 Sonnet to ensure 100% uptime and varied consensus grading.
4. **Mobile Application:** A dedicated React Native app allowing students to scan papers directly via smartphone cameras with edge-based edge-detection.

---

## ⚠️ Known Limitations
- **Extreme Cursive:** Deeply messy, overlapping, or highly stylized handwriting may suffer from decreased OCR accuracy, requiring higher manual intervention.
- **AI Hallucinations:** As with all Generative AI, there is a minor non-zero chance of scoring anomalies. The Human-in-the-Loop architecture explicitly mitigates this risk.

---

## 📄 License & Open Source
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. Contributions, issues, and feature requests are highly welcome!
