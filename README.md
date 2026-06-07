# Vireon HireIQ

Vireon HireIQ is a deploy-ready AI hiring intelligence console for ATS, job portal and HRMS workflows. It parses resumes, analyzes job descriptions, ranks candidates, predicts shortlist probability, explains decisions, generates interview kits, exposes hiring analytics and answers recruiter questions over candidate evidence.

## Features

- Resume text and PDF/DOCX upload intake
- Job description parser with required skills, tools, level, domain and JD quality score
- Candidate-job matching with semantic, skill, project, experience, keyword and education scoring
- Candidate ranking matrix with shortlist probability and explainable fit status
- Skill-gap roadmap for each candidate against the selected role
- Recruiter interview kit generator with expected answer signals
- HR assistant for grounded candidate search and comparison
- Analytics dashboard with status distribution, missing skills and model metrics
- CSV report export for ranked candidates
- Production frontend container with Nginx API proxy

## Stack

- Backend: FastAPI, SQLite, Python, deterministic NLP scoring, optional PDF/DOCX extraction
- Frontend: React, Vite, Framer Motion, responsive recruiter operations UI
- Storage: SQLite database and uploaded resume folder
- Deploy: Docker Compose, backend Uvicorn container, frontend Nginx container

## Local Run

Start the API:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Start the dashboard:

```bash
cd frontend
npm install
npm run dev
```

- Dashboard: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`

The frontend uses `/api` by default. Vite proxies `/api/*` to `http://127.0.0.1:8000` during local development.

## Docker Deploy

```bash
docker compose up --build
```

- Web app: `http://localhost:8080`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

The production Nginx container serves the React app and proxies `/api/*` to the backend container. SQLite data is persisted in the `vireon_data` Docker volume.

## Demo Flow

1. Open the dashboard.
2. Click `Seed Demo`.
3. Select the Artificial Intelligence Intern job.
4. Open `Matching Matrix` and click `Match & Rank`.
5. Select a candidate to inspect skill gaps and interview questions.
6. Use `HR Assistant` to ask questions like `Who knows Python and NLP but lacks Computer Vision?`.
7. Export ranked candidates from `CSV Export`.

## Core APIs

- `GET /api/health`
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

## Runtime Data

On Windows, the default local SQLite database is written to `C:\tmp\vireon-hireiq` to avoid OneDrive file-locking issues. Override storage with:

```env
VIREON_DATA_DIR=./storage
```

or:

```env
DATABASE_URL=sqlite:///./storage/vireon_hireiq.sqlite
```
