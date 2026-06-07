# Production Notes

## Recommended Upgrades

## Deployable MVP

This repo includes production-oriented Docker packaging:

- `backend/Dockerfile` runs FastAPI with Uvicorn.
- `frontend/Dockerfile` builds React and serves it with Nginx.
- `frontend/nginx.conf` serves the SPA and proxies `/api/*` to the backend container.
- `docker-compose.yml` starts both services and persists SQLite data in a Docker volume.

Run:

```bash
docker compose up --build
```

Open `http://localhost:8080`.

## Recommended Upgrades

- Move from SQLite to PostgreSQL.
- Add recruiter authentication and role-based access control.
- Move resume parsing into background jobs with Redis and Celery.
- Store resumes in S3-compatible object storage.
- Add audit logs for every screening decision.
- Add rate limiting and tenant isolation.
- Add persisted FAISS or pgvector indexes for richer retrieval.
- Wire Gemini only for grounded explanation expansion, never as the sole screening signal.

## Bias-Safe Screening

The MVP removes common non-job-related text signals during scoring. Production should additionally add structured redaction, audit reports and legal review before hiring use.
