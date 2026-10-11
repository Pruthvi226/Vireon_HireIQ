# Production Notes

The current authoritative procedure is [the deployment and recovery runbook](docs/DEPLOYMENT_RUNBOOK.md).
See [verified results and limitations](docs/VERIFICATION.md) before a release.

## Deployable MVP

This repo includes production-oriented Docker packaging:

- `backend/Dockerfile` runs FastAPI with Uvicorn.
- `frontend/Dockerfile` builds React and serves it with Nginx.
- `frontend/nginx.conf` serves the SPA and proxies `/api/*` to the backend container.
- `docker-compose.yml` starts both services and persists SQLite data in a Docker volume.

Run:

```bash
cp .env.example .env
# edit .env and set a strong JWT_SECRET_KEY
docker compose up --build
```

Open `http://localhost:8080`.

## System Design Controls Included

The local stack now includes practical production contracts:

- Liveness: `GET /health` and `GET /api/health`.
- Readiness: `GET /ready` and `GET /api/ready`.
- Request tracing: `X-Request-ID` response header and audit-log request IDs.
- Latency visibility: `X-Process-Time-Ms` and in-process p50/p95 counters.
- Backpressure: per-client request limit and maximum resume upload size.
- Worker-safe backpressure: set `REDIS_URL` to use shared `INCR`/`EXPIRE` buckets; if unavailable, the service falls back to the documented single-process limiter.
- Caching: TTL cache for ranking reads with invalidation on candidate/job writes.
- Idempotency: unique candidate/job match rows with upsert behavior.
- Auditability: immutable audit logs for decision-impacting workflows.
- Authentication: 15-minute access tokens, rotating hashed refresh tokens, reset tokens, and five-attempt temporary lockout.
- Notifications: swappable transport interface with a console/log implementation for stage, shortlist, and interview-kit events.
- Embeddings: install `backend/requirements-embeddings.txt` only on workers that enable the local model; the default API image uses the deterministic fallback and stays lightweight.
- Dependency security: the 2026-10-10 frontend audit reports zero advisories after a compatible transitive update; CI uploads its audit artifact even on failure.
- Database posture: configurable SQLite journal mode, busy timeout and query indexes.
- Migration posture: Alembic's baseline is empty. It does not provision PostgreSQL or migrate the application schema; SQLite startup remains the current schema initializer.

## Pre-Deploy Verification

Run these checks before shipping a release:

```bash
cd frontend
npm run build
cd ..
python -c "import ast,pathlib; [ast.parse(pathlib.Path(p).read_text(), filename=p) for p in ['backend/app/main.py','backend/auth/auth_service.py','backend/scripts/smoke_test.py']]"
python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000
docker compose config
```

Run the containerized test path in CI or with Docker Desktop running:

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml build
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --no-deps backend
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --no-deps frontend
```

The test override runs the backend coverage gate and frontend Vitest suite inside their build containers. CI additionally scans both tagged images with Trivy.

The smoke suite validates 41 API checks across auth, RBAC, resume ingestion, matching, ranking, analytics, reports, candidate flows, admin flows, audit logs and platform ops.

## Recommended Production Upgrades

- Move from SQLite to PostgreSQL with Alembic migrations, backups and read replicas.
- Move ranking cache from process memory to Redis so all API replicas share state.
- Move resume parsing, embedding refresh and ranking bursts into a queue-backed worker pool.
- Store resumes in S3-compatible object storage with malware scanning and lifecycle policies.
- Add tenant isolation across users, jobs, candidates, matches, reports and audit logs.
- Add OpenTelemetry traces, Prometheus metrics, structured logs and alerting on SLO burn rate.
- Add rate limiting at the edge gateway or WAF instead of relying on in-process controls.
- Add data retention, right-to-delete workflows and legal review before real hiring use.
- Add model evaluation gates, bias review and rollout flags before changing scoring weights.
- Wire Gemini or another LLM only for grounded explanation expansion, never as the sole screening signal.

## Bias-Safe Screening

The MVP removes common non-job-related text signals during scoring. Production should additionally add structured redaction, fairness dashboards, protected-class proxy checks, audit reports and legal review before hiring use.

## SLO Targets

| Workflow | Target |
| --- | --- |
| Health/readiness | p95 under 100 ms |
| Cached reads | p95 under 500 ms |
| Demo ranking | p95 under 2 s |
| Recruiter API availability | 99.9% |
| Decision auditability | No decision-impacting action without an audit row |
