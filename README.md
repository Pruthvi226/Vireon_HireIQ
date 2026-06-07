# Vireon HireIQ

![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-22c1b6)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-0f766e)
![SQLite](https://img.shields.io/badge/Database-SQLite-64748b)
![Auth](https://img.shields.io/badge/Auth-JWT%20RBAC-f59e0b)
![Status](https://img.shields.io/badge/Smoke%20Test-Passing-16a34a)

Vireon HireIQ is a deploy-ready AI hiring intelligence console for ATS, job portal, and HRMS workflows. It parses resumes, analyzes job descriptions, ranks candidates, predicts shortlist probability, explains hiring decisions, generates interview kits, and gives recruiters a grounded HR assistant over candidate evidence.

## Screenshots

The screenshots below were captured from a live seeded local run.

| Secure login | Recruiter overview |
| --- | --- |
| ![Vireon HireIQ login screen](docs/screenshots/login.png) | ![Vireon HireIQ recruiter dashboard overview](docs/screenshots/recruiter-overview.png) |

| Matching matrix |
| --- |
| ![Vireon HireIQ matching and ranking matrix](docs/screenshots/matching-matrix.png) |

## What It Does

- Parses resume text plus PDF/DOCX uploads.
- Extracts JD skills, tools, level, domain, responsibilities, and JD quality score.
- Scores candidate-job fit across semantic, skill, project, experience, keyword, and education signals.
- Ranks candidates with shortlist probability, fit status, and explainable evidence.
- Builds skill-gap roadmaps and recruiter interview kits.
- Provides an HR assistant for grounded candidate search and comparison.
- Exports ranked candidates as CSV.
- Protects ADMIN, RECRUITER, and CANDIDATE experiences with JWT role-based access.
- Ships with Docker Compose, a FastAPI backend, and an Nginx-served React frontend.

## Tech Stack

| Layer | Tools |
| --- | --- |
| Frontend | React 18, Vite, React Router, Framer Motion |
| Backend | FastAPI, Python, deterministic NLP scoring |
| Auth | JWT, bcrypt, role-based route guards |
| Storage | SQLite plus local resume storage |
| Deployment | Docker Compose, Uvicorn, Nginx API proxy |

## Quick Start

### 1. Start the API

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Recommended backend environment:

```env
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_EXPIRE_HOURS=24
VIREON_DATA_DIR=./runtime
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### 2. Start the dashboard

```bash
cd frontend
npm install
npm run dev
```

- Dashboard: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000` by default.

## Demo Accounts

Seed demo users with either:

```bash
cd backend
.venv\Scripts\python scripts\seed_users.py
```

or:

```bash
curl -X POST http://localhost:8000/api/demo/seed-users
```

| Role | Email | Password | Home |
| --- | --- | --- | --- |
| ADMIN | `admin@vireon.ai` | `admin123` | `/admin` |
| RECRUITER | `recruiter@vireon.ai` | `recruiter123` | `/recruiter` |
| CANDIDATE | `candidate@vireon.ai` | `candidate123` | `/candidate` |

## Demo Flow

1. Start the backend and frontend.
2. Seed data with `POST /api/demo/seed` or click `Seed Demo`.
3. Sign in as `recruiter@vireon.ai`.
4. Open `Matching Matrix`.
5. Click `Match & Rank`.
6. Inspect ranked candidates, fit status, skill gaps, and interview questions.
7. Ask the HR assistant questions like `Who knows Python and NLP but lacks Computer Vision?`.
8. Export the ranking from `CSV Export`.

## Docker Deploy

```bash
docker compose up --build
```

- Web app: `http://localhost:8080`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

The production frontend container serves the React build through Nginx and proxies `/api/*` to the backend container. SQLite data is persisted in the `vireon_data` Docker volume.

## Core API Routes

| Area | Endpoints |
| --- | --- |
| Health and demo | `GET /api/health`, `POST /api/demo/seed`, `POST /api/demo/seed-users` |
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Resumes | `POST /api/resumes/text`, `POST /api/resumes/upload`, `GET /api/candidates` |
| Jobs and matching | `POST /api/jobs/create`, `GET /api/jobs`, `POST /api/match/candidate`, `GET /api/jobs/{job_id}/rank-candidates` |
| Insights | `GET /api/candidates/{candidate_id}/skill-gap/{job_id}`, `POST /api/interview/generate`, `GET /api/analytics/job/{job_id}` |
| Assistant and reports | `POST /api/chat/hr`, `GET /api/reports/job/{job_id}?format=csv` |
| Admin | `GET /api/admin/users`, `GET /api/admin/analytics` |
| Candidate | `GET /api/candidate/ats-score?job_id={job_id}`, `GET /api/candidate/skill-gap/{job_id}`, `GET /api/candidate/resume-improvement/{job_id}` |

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for more request examples.

## Role Access

- ADMIN can view users, platform data, jobs, candidates, analytics, and admin dashboards.
- RECRUITER can create jobs, upload resumes, rank candidates, generate interviews, view analytics, export reports, and use the HR assistant.
- CANDIDATE can upload their own resume and view their own ATS score, skill gaps, and resume improvement guidance.

Protected route groups:

- `/api/admin/*` requires ADMIN.
- `/api/recruiter/*` requires RECRUITER or ADMIN.
- `/api/candidate/*` requires CANDIDATE or ADMIN.
- Ranking, analytics, interview kits, JD creation, and reports require RECRUITER or ADMIN.

## Smoke Test Status

Verified on 2026-06-08 with a live local run:

- `npm run build` completed successfully.
- Backend Uvicorn smoke test passed for health, demo seed, recruiter login, `/api/auth/me`, candidates, jobs, ranking, analytics, skill gap, interview generation, HR chat, CSV export, and candidate `403` role guard.
- Screenshot capture passed through headless Chrome against the seeded app.

Representative smoke result:

```json
{
  "smoke": "OK",
  "seeded_rankings": 3,
  "candidates": 3,
  "jobs": 1,
  "top_score": 69.9,
  "analytics_total": 3,
  "interview_questions": 6,
  "chat_evidence": 3,
  "role_guard_status": 403
}
```

## Runtime Data

Local SQLite data and uploaded resumes are written to `backend/runtime` by default. Override storage with:

```env
VIREON_DATA_DIR=./storage
```

or:

```env
DATABASE_URL=sqlite:///./storage/vireon_hireiq.sqlite
```

Runtime databases, uploaded resumes, virtualenvs, logs, and build artifacts are ignored by git. Passwords are stored as bcrypt hashes; plain passwords are never stored.

## Project Structure

```text
AI_Interview/
|-- backend/              FastAPI app, auth, schemas, seed scripts
|-- frontend/             React/Vite dashboard
|-- database/             SQL schema reference
|-- docs/screenshots/     README screenshots
|-- docker-compose.yml    Production compose stack
`-- README.md
```
