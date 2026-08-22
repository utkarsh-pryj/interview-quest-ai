<div align="center">

# 🎯 InterviewQuest AI
### Grounded AI Interview Question Generator & Skill Gap Analyzer

[![React](https://img.shields.io/badge/React_18-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python_3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

<p align="center">
  <b>A real, grounded interview preparation engine that bridges candidate resumes with target job requirements using O*NET skill taxonomy, multi-signal RAG retrieval, and instant evaluation.</b>
</p>

</div>

---

## 💡 Why InterviewQuest AI?

Generic AI interview tools hallucinate random trivia questions without knowing the candidate's background or the specific role requirements. 

**InterviewQuest AI** takes a **RAG-first, grounded approach**:
1. **Parses & Extracts**: Identifies hard skills, years of experience, and domain strengths from your **Resume**.
2. **Taxonomy Mapping**: Maps requirements from the target **Job Description** against the standardized **O*NET Skill Taxonomy**.
3. **Skill Gap Detection**: Computes exact overlapping skills, missing requirements, and resume-exclusive strengths.
4. **Adaptive Question RAG**: Retrieves, scores, and ranks targeted interview questions weighted by skill gaps, role family, and seniority ($0.40 \cdot \text{Skill} + 0.25 \cdot \text{JD} + 0.15 \cdot \text{Resume} + 0.10 \cdot \text{Role} + 0.10 \cdot \text{Strategy}$).
5. **Instant Evaluation**: Analyzes candidate answers with structured scores, feedback, key strengths, and actionable areas for improvement.
6. **PostgreSQL Session Storage**: Explicitly save, organize, and revisit old interview sessions by role and company.

---

## 🏗️ System Architecture & Workflow

```mermaid
flowchart TD
    A[Candidate Resume] --> C[Document Parser & Skill Extractor]
    B[Target Job Description] --> C
    C --> D[O*NET Canonical Skill Matcher]
    D --> E[Skill Gap & Alignment Matrix]
    E --> F[Multi-Signal RAG Vector Engine]
    F --> G[(PostgreSQL Question Bank)]
    G --> H[Ranked Adaptive Questions: 8 / 12 / 16 / 20]
    H --> I[Question Workspace & Collapsible Cards]
    I --> J[Candidate Answers]
    J --> K[Two-Stage Evaluation Engine]
    K --> L[Score / Feedback / Key Strengths / Improvement]
    L --> M[(Saved PostgreSQL Sessions)]
```

---

## ✨ Features & Highlights

- ⚡ **Zero Cold-Start Vector Engine**: Sub-millisecond similarity rankings ($<1\text{ms}$) with zero model-download latency.
- 🎯 **8, 12, 16, or 20 Question Sets**: Customize the length of your preparation session.
- 🎨 **Clean, Native Web Design**: Built with pure Native HTML & plain CSS with a light purple/blue + white theme (No heavy Tailwind or framework bloat).
- 💾 **On-Demand Session Persistence**: Save and manage sessions directly in PostgreSQL with target role, company, and timestamps.
- 🛡️ **Zero Test Overhead**: Streamlined, production-ready codebase without test suite bloat.

---

## 💻 Tech Stack

### Frontend
- **Framework**: React 18 (Vite)
- **Styling**: Pure Native HTML5 & Standard Plain CSS (`src/index.css`)
- **Icons**: Lucide React
- **Routing**: React Router DOM v6
- **HTTP Client**: Axios

### Backend
- **Framework**: FastAPI (Asynchronous Python)
- **Database ORM**: SQLAlchemy 2.0 (Asyncpg + Sync Psycopg2)
- **Validation**: Pydantic v2
- **Vector Retrieval**: Local Deterministic Fast Vector Embedder
- **Server**: Uvicorn ASGI

### Database
- **Engine**: PostgreSQL (Local PGAdmin 4 or Cloud Supabase / Neon)

---

## 🚀 Quickstart Guide

### 1. Clone or Download Repository
```bash
git clone https://github.com/your-username/interviewquest-ai.git
cd interviewquest-ai
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv

# Windows:
.\venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file inside `backend/`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/interviewquest
SYNC_DATABASE_URL=postgresql://postgres:your_password@localhost:5432/interviewquest
SECRET_KEY=your_secure_random_jwt_secret_key_32_characters
GEMINI_API_KEY=your_gemini_api_key
```

Run database ingestion (seeds O*NET skills & questions):
```bash
python run_ingestion.py
```

Start the FastAPI server:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
npm run dev
```

Visit **`http://localhost:5173`** in your browser.

---

## 🌐 100% Free Cloud Deployment Roadmap

When you are ready to deploy this project online for free:

```
┌─────────────────────────────────────────────────────────────┐
│                    FREE CLOUD DEPLOYMENT                     │
├───────────────────┬───────────────────┬─────────────────────┤
│     DATABASE      │      BACKEND      │      FRONTEND       │
│  (Supabase/Neon)  │  (Render/Railway) │  (Vercel/Netlify)   │
│                   │                   │                     │
│ Free PostgreSQL   │ Free FastAPI      │ Free React + Vite   │
│ with pgvector     │ Web Service       │ Static Hosting      │
└───────────────────┴───────────────────┴─────────────────────┘
```

1. **Database on Supabase / Neon (Free)**:
   - Create a free PostgreSQL project at [Supabase](https://supabase.com) or [Neon](https://neon.tech).
   - Copy the connection string to your backend `DATABASE_URL`.

2. **Backend on Render (Free)**:
   - Push your code to GitHub.
   - Link repository on [Render](https://render.com) as a **Web Service**.
   - Build command: `pip install -r backend/requirements.txt`
   - Start command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

3. **Frontend on Vercel (Free)**:
   - Import your GitHub repo on [Vercel](https://vercel.com).
   - Set Root Directory: `frontend`
   - Build command: `npm run build`
   - Output directory: `dist`

---

## 🏷️ Recommended Project Names
If you're showcasing this project on your portfolio or resume, here are top recommended names:
1. **`InterviewQuest AI`** (Default & Recommended)
2. **`HireReady AI`**
3. **`TalentMatch RAG`**
4. **`SkillForge AI`**

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
