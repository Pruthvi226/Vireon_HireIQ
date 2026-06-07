# Vireon HireIQ

Vireon HireIQ is an AI hiring intelligence system for ATS, job portal and HRMS workflows. It parses resumes, analyzes job descriptions, ranks candidates, predicts shortlist probability, explains decisions, generates interview kits, exposes hiring analytics and answers recruiter questions over candidate evidence.

## Stack

- Backend: FastAPI, SQLite, deterministic NLP scoring, optional PDF/DOCX extraction
- Frontend: React, Vite, operational recruiter dashboard
- Storage: local SQLite database and uploaded resume folder
- AI/ML: hybrid semantic similarity, skill overlap, project relevance, experience relevance, calibrated shortlist probability

## Run Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

On Windows the default runtime database is written to `C:\tmp\vireon-hireiq` to avoid OneDrive file-locking issues with SQLite.

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: `http://localhost:5173`

## Core APIs

- `POST /api/demo/seed`
- `POST /api/resumes/text`
- `POST /api/resumes/upload`
- `GET /api/candidates`
- `POST /api/jobs/create`
- `GET /api/jobs`
- `POST /api/match/candidate`
- `GET /api/jobs/{job_id}/rank-candidates`
- `GET /api/candidates/{candidate_id}/skill-gap/{job_id}`
- `POST /api/interview/generate`
- `GET /api/analytics/job/{job_id}`
- `POST /api/chat/hr`
- `GET /api/reports/job/{job_id}?format=csv`

## Demo Flow

1. Start backend and frontend.
2. Click `Seed Demo`.
3. Select the Artificial Intelligence Intern job.
4. Click `Rank Candidates`.
5. Generate an interview kit for a selected candidate.
6. Ask HR Assistant questions such as `Who knows Python and NLP but lacks Computer Vision?`.

## Git Preservation

The old AI Interview Coach code was committed locally on branch `ai-interview-existing-20260607`. The GitHub push was blocked by the approval reviewer as an external code export and needs explicit approval before retrying.
