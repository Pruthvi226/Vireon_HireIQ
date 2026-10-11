# Vireon HireIQ Project Documentation

Current source-based findings and release limits are documented in the
[2026-10 audit](docs/PROJECT_AUDIT.md), [verification report](docs/VERIFICATION.md),
[deployment runbook](docs/DEPLOYMENT_RUNBOOK.md) and
[remaining feature roadmap](docs/FEATURE_ROADMAP.md). These supersede historical
test counts and production-readiness claims in this document. SQLite remains
the only implemented database, recruiter data is a shared single-company
workspace, and shortlist values are uncalibrated heuristics.

## 1. Executive Summary

Vireon HireIQ is a role-based hiring intelligence platform for ATS, job portal, and HRMS workflows. It converts resumes and job descriptions into structured records, compares candidate evidence against role requirements, ranks candidates, explains fit, generates interview preparation material, and provides operational visibility for the platform.

The system is implemented as a local-first web application:

- React and Vite provide the browser experience.
- FastAPI and Uvicorn provide the HTTP API and domain orchestration.
- SQLite stores users, candidates, jobs, match results, experiments, and audit events.
- Local filesystem storage keeps uploaded resume files.
- Docker Compose packages the API and Nginx-served frontend.

The project currently provides a functional MVP/demo with production-oriented contracts such as JWT authentication, role-based authorization, request tracing, health/readiness checks, rate limiting, caching, audit logging, and a documented scale path.

## 2. Product Scope

### In scope

- Resume ingestion from text, PDF, and DOCX uploads.
- Resume parsing into contact data, skills, projects, experience, education, certifications, and links.
- Job description parsing into title, company, domain, seniority level, responsibilities, required skills, tools, and quality score.
- Candidate-to-job scoring and ranking.
- Explainable match results with matched, partial, and missing skills.
- Shortlist probability and fit status.
- Skill-gap analysis and improvement roadmaps.
- Recruiter interview-kit generation.
- Evidence-grounded HR candidate search.
- JSON and CSV report output.
- Candidate self-service ATS scoring and resume improvement guidance.
- Admin views for users, platform data, analytics, audit events, and operational health.
- Demo data and user seeding for evaluation.

### Out of scope or not production-complete

- Multi-tenant isolation and tenant administration.
- Distributed job queues and asynchronous processing.
- External object storage and malware scanning for resumes.
- PostgreSQL migrations and managed database operations.
- Production-grade vector search, embedding refresh, or model serving.
- Human approval workflows, interview scheduling, offer management, or payroll.
- Automated hiring decisions. The output is decision support for recruiters and must remain subject to human review.

## 3. Users and Roles

| Role        | Purpose               | Main capabilities                                                                                                                                                          |
| ----------- | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ADMIN`     | Platform operator     | Inspect users, candidates, jobs, analytics, platform counters, health, topology, and audit events. Can also access recruiter and candidate surfaces.                       |
| `RECRUITER` | Hiring workflow owner | Create jobs, ingest resumes, view candidates, match and rank candidates, inspect explanations, generate interview kits, use HR search, view analytics, and export reports. |
| `CANDIDATE` | Resume owner          | Upload or submit a resume, view owned profiles, calculate ATS score for a job, inspect skill gaps, and receive resume improvement guidance.                                |

Authentication is required for protected API operations. Authorization is enforced by role on the backend and reflected in frontend route guards.

## 4. Functional Requirements and Features

### FR-01: Account and authentication management

- Users can register and log in through the authentication API.
- Passwords are stored as bcrypt hashes rather than plaintext.
- Successful authentication returns a JWT bearer token and public user details.
- Tokens include subject, issue time, expiration time, email, and role claims.
- The current authenticated user can be retrieved with `/api/auth/me`.
- The default token lifetime is 24 hours and is configurable.

### FR-02: Resume ingestion and parsing

- Recruiters, candidates, and admins can submit resume text.
- The upload endpoint accepts a multipart file and optional candidate name.
- PDF and DOCX text is extracted by backend libraries; plain text is also supported.
- Uploaded filenames are normalized before being written to local resume storage.
- Upload size is limited by `MAX_RESUME_BYTES`, defaulting to 5 MB.
- Parsed resumes are persisted as candidate records.
- Candidate-created records are associated with the candidate user for owner-scoped self-service.

### FR-03: Job description ingestion

- Recruiters and admins can create a job from title, company, and description text.
- The parser extracts required skills, tools, responsibilities, domain, level, and a job-description quality score.
- Jobs can be listed for selection by ranking and candidate self-service workflows.

### FR-04: Candidate matching and ranking

- A recruiter or admin can match one candidate to one job.
- A recruiter or admin can rank all candidates for a job.
- The matching engine combines semantic, skill, project, experience, keyword, and education signals.
- Results include component scores, final score, shortlist probability, fit status, matched skills, partial skills, missing skills, and an explanation.
- Match rows use a unique candidate/job key and upsert behavior, so repeated ranking does not create duplicate logical decisions.
- Ranking results are cached with a configurable TTL and invalidated when candidate or job data changes.

### FR-05: Skill-gap and development guidance

- Recruiters can inspect the skill gap for any candidate/job pair.
- Candidates can inspect their own skill gap for a selected job.
- Responses classify strong, partial, and missing skills.
- Missing skills can be converted into a week-by-week roadmap with artifact-based actions.
- Candidates can request resume improvement suggestions based on missing skills and evidence quality.

### FR-06: Interview-kit generation

- Recruiters and admins can generate a candidate/job interview kit.
- Questions are generated from matched skills, resume projects, missing skills, and a general behavioral/iteration prompt.
- Questions are categorized as technical, project, skill-gap, or HR.
- Optional answer hints describe the expected evidence or signal.
- A maximum of ten questions is returned.

### FR-07: HR assistant and evidence retrieval

- Recruiters and admins can ask natural-language questions about candidate evidence.
- The service compares the question with candidate skills, projects, experience, and resume text.
- The response returns top candidate evidence records and retrieval scores.
- The assistant answer is grounded in retrieved candidate names and does not invent an unsupported candidate match.

### FR-08: Analytics and reporting

- Recruiters can view total candidates, average score, shortlist ratio, status distribution, common missing skills, and top candidates for a job.
- Admins can view platform-wide user, candidate, job, and match totals plus job summaries.
- Recruiters and admins can export ranked results as JSON or CSV.
- CSV output includes candidate name, role, final score, shortlist probability, status, matched skills, and missing skills.

### FR-09: Candidate self-service

- Candidates can view their own uploaded resume profiles.
- Candidate ATS scoring is calculated for a selected job.
- Candidate responses include the score, fit status, job details, and match explanation.
- Candidate endpoints prevent a candidate from reading all platform candidates.

### FR-10: Administration and platform operations

- Admins can list users, candidates, and jobs.
- Admins can inspect platform counts and operational counters.
- Admins can inspect recent audit events.
- Recruiters and admins can inspect system overview data including topology, readiness, traffic, cache, resilience controls, SLO targets, and production scale path.
- Public health endpoints expose liveness; readiness endpoints validate SQLite and required runtime directories.

### FR-11: Demo and evaluation support

- Demo seeding creates a representative AI internship job, three candidates, baseline model experiment data, rankings, and audit activity.
- Demo user seeding creates one account for each supported role.
- The smoke suite exercises authentication, RBAC, ingestion, matching, ranking, analytics, chat, reporting, candidate self-service, admin APIs, and platform operations.

## 5. Main User Workflows

### Recruiter workflow

1. Log in as a recruiter.
2. Create a job by entering or pasting a job description.
3. Add candidates through text input or resume upload.
4. Select a job and run matching/ranking.
5. Review the ranked matrix, scores, probabilities, statuses, and explanations.
6. Open a candidate to inspect skill gaps and interview questions.
7. Ask the HR assistant evidence-based questions.
8. Review analytics and export a CSV report.

### Candidate workflow

1. Register or log in as a candidate.
2. Upload or submit a resume.
3. Open the candidate profile.
4. Select a job and request an ATS score.
5. Review matched, partial, and missing skills.
6. Follow the generated roadmap and resume improvement suggestions.

### Administrator workflow

1. Log in as an admin.
2. Inspect platform users, candidates, jobs, and match totals.
3. Review system health, readiness, traffic, cache, and topology information.
4. Inspect audit records for decision-impacting actions.
5. Use recruiter or candidate views when operational support requires it.

## 6. Non-Functional Requirements

### NFR-01: Security

- Use JWT bearer authentication for protected APIs.
- Use bcrypt password hashing.
- Enforce role-based access control in backend dependencies, independent of frontend visibility.
- Scope candidate self-service reads to the owning user.
- Keep JWT secrets and runtime configuration in environment variables.
- Apply CORS allow-list configuration.
- Enforce request rate limits and upload size limits.
- Normalize uploaded filenames to reduce path manipulation risk.
- Never treat model output as an autonomous hiring decision.

Production hardening still required: replace development/default secrets, rotate signing keys, add stronger tenant policies, add malware scanning, use HTTPS, and place rate limiting at an API gateway or WAF.

### NFR-02: Availability and reliability

- Docker services restart unless stopped.
- Backend readiness is used by Docker health checks and frontend startup dependency ordering.
- Liveness and readiness are separate contracts.
- SQLite uses configurable journal mode and busy timeout behavior.
- Match writes are idempotent for a candidate/job pair.
- Decision-impacting operations append audit events.
- Target availability for recruiter workflows is 99.9% in the documented production design.

### NFR-03: Performance

- Ranking reads use an in-process TTL cache.
- Database indexes support owner-scoped candidates, recent jobs, ranked match lookup, candidate match lookup, and audit queries.
- Target latency is p95 below 500 ms for cached reads and below 2 seconds for demo ranking.
- Health/readiness target is p95 below 100 ms.
- Current implementation is synchronous and local; large-scale workloads require worker queues and shared services.

### NFR-04: Scalability

- The API boundary is designed to be stateless because identity is carried by JWTs.
- Frontend assets can be served from Nginx replicas or a CDN.
- The documented production path replaces in-process cache with Redis and SQLite with PostgreSQL.
- Resume storage can move from local disk to object storage.
- Parsing, embeddings, and ranking can move to queue-backed workers.
- Candidate retrieval can move to pgvector or FAISS with offline embedding refresh.

### NFR-05: Observability and auditability

- Each response includes `X-Request-ID` and `X-Process-Time-Ms` headers.
- Audit records store actor, role, action, resource, metadata, request ID, and timestamp.
- Runtime counters track requests, client errors, server errors, error rate, latency percentiles, and top paths.
- Cache statistics expose hits, misses, sets, invalidations, TTL, and active keys.
- System overview exposes readiness and topology information.

### NFR-06: Maintainability

- Frontend, backend, database reference schema, and documentation are separated by concern.
- Pydantic request models validate API payloads.
- The backend exposes OpenAPI/Swagger documentation through FastAPI.
- Configuration is environment-driven.
- The smoke test provides a repeatable release check.
- The codebase keeps a clear local development path and a Docker deployment path.

### NFR-07: Portability and deployment

- Local development works with Python virtual environments and npm.
- Docker Compose runs the complete two-service stack.
- The backend persists data through the `vireon_data` named volume.
- The frontend container serves the production build through Nginx and proxies `/api` requests to the backend.
- Health checks are defined for both containers.

### NFR-08: Data integrity and consistency

- Core entities are stored in one SQLite database for strong local consistency.
- Candidate/job/match relationships are protected by schema constraints and indexes.
- Match results are unique per candidate/job pair.
- Audit event IDs are unique.
- Ranking cache can be stale only within its configured TTL, with write-triggered invalidation.

## 7. Architecture

```text
Browser
  |
  v
React/Vite application or Nginx static frontend
  |
  | /api proxy
  v
FastAPI application
  |-- JWT authentication and RBAC
  |-- request ID and latency middleware
  |-- rate limit and upload limit controls
  |-- endpoint validation and orchestration
  |-- audit event writer
  |
  |-- Resume/JD parsing
  |-- Matching and ranking engine
  |-- Skill-gap and interview generation
  |-- HR evidence retrieval
  |-- Analytics and report generation
  |
  v
SQLite database + local resume storage + in-process TTL cache
```

### Components

| Component       | Responsibility                                                                                          | Current technology                                                      |
| --------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Web client      | Authentication, role-specific dashboards, forms, ranking views, analytics, chat, and candidate insights | React 18, React Router, Framer Motion, Vite                             |
| API gateway     | HTTP contracts, validation, authentication, authorization, tracing, rate limits, and orchestration      | FastAPI, Pydantic, Uvicorn                                              |
| Matching engine | Parsing, feature scoring, fit classification, shortlist probability, and explanations                   | Python deterministic NLP/scoring logic, NumPy/scikit-learn dependencies |
| Authentication  | Registration, login, JWT creation/validation, password verification                                     | PyJWT, bcrypt                                                           |
| Persistence     | Users, candidates, jobs, matches, experiments, and audit logs                                           | SQLite                                                                  |
| File storage    | Uploaded resume bytes                                                                                   | Local runtime directory                                                 |
| Cache           | Repeated ranking reads and cache metrics                                                                | In-process TTL cache                                                    |
| Delivery        | Static frontend and API proxy                                                                           | Docker, Nginx, Docker Compose                                           |

## 8. Data Model

### `users`

Stores account identity, unique email, bcrypt password hash, role, optional company, and creation time.

### `candidates`

Stores parsed resume identity and evidence: name, email, phone, links, education, skills, projects, experience, certifications, original resume text, optional file path, owner user ID, and timestamp.

### `jobs`

Stores job title, company, original description, required skills, responsibilities, tools, skill weights, level, domain, quality score, and timestamp.

### `match_results`

Stores candidate/job scores for semantic, skill, project, experience, keyword, education, final score, shortlist probability, status, matched/partial/missing skills, explanation, and timestamp. `(candidate_id, job_id)` is unique.

### `model_experiments`

Stores model name, accuracy, precision, recall, F1 score, parameters, and timestamp. The current demo exposes a calibrated baseline record.

### `audit_logs`

Stores immutable event ID, actor identity and role, action, resource, metadata, request ID, and timestamp.

## 9. API Catalog

### Public and authentication APIs

- `GET /health`, `GET /api/health`: liveness information.
- `GET /ready`, `GET /api/ready`: dependency readiness.
- `POST /api/auth/register`: register and receive a token.
- `POST /api/auth/login`: authenticate and receive a token.
- `GET /api/auth/me`: return the current authenticated user.
- `POST /api/demo/seed`: create demo data.
- `POST /api/demo/seed-users`: create demo accounts.

### Resume and job APIs

- `POST /api/resumes/text`: parse and save a resume from text.
- `POST /api/resumes/upload`: parse and save a PDF, DOCX, or text upload.
- `GET /api/candidates`: list candidates for recruiters/admins.
- `POST /api/jobs/create`: parse and save a job description.
- `GET /api/jobs`: list jobs for authenticated users.

### Matching and recruiter APIs

- `POST /api/match/candidate`: calculate and persist one match.
- `GET /api/jobs/{job_id}/rank-candidates`: rank all candidates for a job.
- `GET /api/candidates/{candidate_id}/skill-gap/{job_id}`: inspect a candidate's gap.
- `POST /api/interview/generate`: generate an interview kit.
- `GET /api/analytics/job/{job_id}`: return job-level hiring analytics.
- `POST /api/chat/hr`: retrieve evidence for a recruiter question.
- `GET /api/reports/job/{job_id}?format=json|csv`: export ranked results.
- `GET /api/model/experiment`: return baseline model metrics.
- `GET /api/recruiter/dashboard`: return recruiter summary data.
- `GET /api/recruiter/jobs`: recruiter job list alias.
- `GET /api/recruiter/candidates`: recruiter candidate list alias.
- `GET /api/recruiter/analytics/{job_id}`: recruiter analytics alias.

### Candidate APIs

- `GET /api/candidate/profile`: list the authenticated candidate's resumes.
- `GET /api/candidate/ats-score?job_id={id}`: calculate owned candidate ATS score.
- `GET /api/candidate/skill-gap/{job_id}`: calculate owned candidate skill gap.
- `GET /api/candidate/resume-improvement/{job_id}`: return improvement guidance.

### Administration and operations APIs

- `GET /api/admin/users`: list users.
- `GET /api/admin/candidates`: list all candidates.
- `GET /api/admin/jobs`: list all jobs.
- `GET /api/admin/analytics`: return platform analytics.
- `GET /api/admin/platform-data`: return platform counters and runtime metrics.
- `GET /api/system/overview`: return readiness, topology, SLO targets, traffic, cache, and scale path.
- `GET /api/system/audit?limit={n}`: return recent audit events.

## 10. Frontend Screens and Navigation

- `/login`: authenticate an existing user.
- `/register`: create an account.
- `/recruiter`: recruiter dashboard for ingestion, ranking, analytics, candidate inspection, interview kits, HR assistant, reports, and platform status.
- `/candidate`: candidate dashboard for profile, ATS score, skill gap, and improvement guidance.
- `/admin`: administrator dashboard for platform data and operations.
- `/`: redirects an authenticated user to the home route for their role, otherwise to login.

The frontend also supports persisted theme selection, loading/error/success states, drag-and-drop resume upload behavior, candidate detail inspection, and animated UI transitions.

## 11. Configuration

| Variable                       | Default                                  | Purpose                                            |
| ------------------------------ | ---------------------------------------- | -------------------------------------------------- |
| `APP_ENV` or `ENVIRONMENT`     | `local` locally; `production` in Compose | Runtime environment label                          |
| `VIREON_DATA_DIR`              | backend runtime directory                | SQLite and resume storage root                     |
| `DATABASE_URL`                 | local SQLite path when supplied          | Optional database location override                |
| `JWT_SECRET_KEY`               | required environment value               | JWT signing secret, at least 32 characters outside development |
| `JWT_EXPIRE_HOURS`             | `24`                                     | JWT lifetime                                       |
| `VIREON_CACHE_TTL_SECONDS`     | `60`                                     | Ranking cache lifetime                             |
| `VIREON_RATE_LIMIT_PER_MINUTE` | `240`                                    | In-process per-client request limit                |
| `VIREON_SQLITE_JOURNAL_MODE`   | `MEMORY` locally, `WAL` in Compose       | SQLite journal mode                                |
| `MAX_RESUME_BYTES`             | `5242880`                                | Maximum uploaded resume size                       |
| `CORS_ALLOWED_ORIGINS`         | local frontend origins                   | Allowed browser origins                            |

## 12. Running and Deploying

### Local development

```text
Backend:  cd backend && python -m venv .venv
          .venv\\Scripts\\activate
          pip install -r requirements.txt
          uvicorn app.main:app --reload --port 8000

Frontend: cd frontend
          npm install
          npm run dev
```

Local URLs:

- Dashboard: `http://localhost:5173`
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/health`

### Docker Compose

```text
docker compose up --build
```

- Web application: `http://localhost:8080`
- API: `http://localhost:8000`
- Persistent volume: `vireon_data`

Before deployment, generate `JWT_SECRET_KEY` with `openssl rand -hex 32`, provide it through `.env` or a secret store, review CORS origins, and use storage suitable for the configured SQLite journal mode.

## 13. Testing and Quality Evidence

The repository includes:

- Frontend production build command: `npm run build`.
- Backend smoke suite: `python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000`.
- User seeding script: `python backend/scripts/seed_users.py`.
- FastAPI OpenAPI documentation at `/docs`.
- Smoke coverage for positive flows and negative RBAC checks.

The existing project verification record reports a successful frontend build, backend parse checks, and a passing 41-check API smoke run covering auth, RBAC, seeding, ingestion, matching, ranking, analytics, candidate self-service, admin APIs, platform operations, audit, chat, and CSV export.

## 14. Risks, Constraints, and Future Improvements

1. SQLite and local file storage are appropriate for demos and small deployments, but not for high-volume multi-instance production without migration.
2. The in-process cache is local to one API process and is not shared across replicas.
3. Ranking and parsing are synchronous, so large uploads or ranking bursts can consume request workers.
4. Resume files need object storage, retention rules, access controls, and malware scanning in production.
5. Model metrics are baseline experiment metadata, not a substitute for continuous validation on representative hiring data.
6. Bias-safe scoring should be accompanied by dataset review, feature governance, subgroup evaluation, human oversight, and model change approval.
7. The system should add tenant IDs and explicit data retention/deletion policies before use by multiple organizations.
8. Production deployments should add centralized logs, distributed traces, alerting, backups, restore drills, and disaster recovery procedures.
9. Candidate and recruiter data is sensitive personal information and requires privacy notices, access reviews, encryption in transit and at rest, and appropriate compliance controls.

## 15. Related Documentation

- [README](README.md): quick start, demo accounts, screenshots, and release smoke instructions.
- [API Documentation](API_DOCUMENTATION.md): concise request examples and endpoint notes.
- [System Design](docs/SYSTEM_DESIGN.md): architecture principles, consistency model, SLO targets, and production evolution.
- [Database Schema](database/schema.sql): reference relational schema and indexes.
- [Model Experiments](MODEL_EXPERIMENTS.md): model evaluation context.
- [Production Notes](PRODUCTION.md): deployment and operational considerations.
