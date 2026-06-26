# Vireon HireIQ System Design

This project is still runnable as a local Docker Compose app, but it now exposes production-style system contracts: health, readiness, tracing, cache visibility, audit logs, and an explicit scale path.

## Product Boundary

Vireon HireIQ is a hiring intelligence platform with three role surfaces:

- Recruiters ingest resumes, create jobs, rank candidates, generate interviews, ask grounded HR questions, and export reports.
- Candidates upload resumes and view role-specific ATS score, skill gaps, and improvement plans.
- Admins inspect users, platform counts, audit events, and operational health.

## Logical Architecture

```text
Browser
  |
  v
React/Vite dashboard --built--> Nginx static frontend
  |
  | /api proxy or Vite dev proxy
  v
FastAPI API gateway
  |-- JWT auth and RBAC
  |-- request ID middleware
  |-- rate limiting and upload limits
  |-- cache-aware orchestration
  |-- audit event writer
  |
  |-- Matching engine
  |     |-- resume/JD parsing
  |     |-- bias-safe scoring
  |     |-- ranking and shortlist probability
  |
  |-- HR assistant retrieval
  |-- report generation
  |
  v
SQLite runtime database + local resume storage
```

## Runtime Components

| Component | Current implementation | Production evolution |
| --- | --- | --- |
| Frontend | React served by Vite or Nginx | CDN-backed static assets plus edge caching |
| API gateway | FastAPI/Uvicorn | Multiple stateless workers behind a load balancer |
| Auth | JWT and bcrypt | Managed identity, key rotation, tenant-aware policies |
| Cache | In-process TTL cache | Redis cluster with shared invalidation |
| Database | SQLite with configurable journal mode and indexes | PostgreSQL primary, replicas, backups, migrations |
| Resume storage | Local files under runtime storage | S3-compatible object storage with malware scanning |
| Async work | Synchronous demo flow | Queue-backed workers for parsing, embeddings, and ranking |
| Observability | Request IDs, latency counters, readiness, audit logs | Metrics, traces, logs, alerts, dashboards, SLO burn alerts |

## Core System Design Concepts Applied

### 1. Stateless API Boundary

FastAPI owns orchestration and validation. The API does not keep user session state in memory; identity comes from JWTs. This lets the API scale horizontally once the cache and database move to shared services.

### 2. Readiness vs Health

- `GET /health` confirms the process is alive and returns version, uptime, database path, and request ID.
- `GET /ready` confirms dependencies needed to serve traffic are available.

This separates liveness from deploy/load-balancer readiness.

### 3. Request Tracing

Every request receives an `X-Request-ID`, and responses include `X-Process-Time-Ms`. Audit events store the same request ID, so a decision can be followed from UI action to backend event.

### 4. Backpressure

The middleware applies an in-process request limit per client and resume uploads have a fixed byte cap. In production this would move to an edge gateway, WAF, or API gateway policy.

### 5. Cache With Explicit Invalidation

Ranking results are cached with a TTL because ranking is a repeated expensive read. Candidate and job writes invalidate ranking cache keys to prevent stale decisions.

### 6. Idempotent Match Writes

`match_results` has a unique `(candidate_id, job_id)` constraint and uses upsert semantics. Running ranking multiple times updates the same logical decision row instead of duplicating it.

### 7. Auditability

Decision-impacting flows append immutable audit events:

- demo seeding
- candidate creation
- job creation
- candidate matching
- ranking
- interview kit generation
- HR assistant queries
- report exports

Audit logs capture actor role, resource, metadata, request ID, and timestamp.

### 8. Query-Oriented Indexing

The schema includes indexes for owner-scoped candidate reads, latest jobs, ranked match lookups, candidate match lookup, and audit-log inspection.

## API Request Flow

```text
1. Browser sends JWT-authenticated API request.
2. Middleware assigns or accepts X-Request-ID.
3. Middleware applies rate-limit policy.
4. Auth dependency resolves user and checks role permissions.
5. Endpoint validates input with Pydantic.
6. Domain function performs parse, score, rank, search, or report work.
7. Writes update SQLite with the configured journal mode and query indexes.
8. Decision-impacting workflows append audit logs.
9. Response returns data plus request ID and latency headers.
```

## Data Model

Primary entities:

- `users`: role-scoped actors.
- `candidates`: parsed resumes and owner mapping for candidate self-service.
- `jobs`: parsed job descriptions, required skills, tools, domain, and quality score.
- `match_results`: persisted candidate-job scores with unique idempotency key.
- `model_experiments`: baseline model benchmark metadata.
- `audit_logs`: immutable operational and decision events.

## Consistency Model

The local MVP uses strong consistency through a single SQLite database. Ranking cache is eventually consistent for up to `VIREON_CACHE_TTL_SECONDS`, but candidate/job writes invalidate ranking cache entries immediately.

For production:

- User, candidate, job, match, and audit writes remain strongly consistent in PostgreSQL.
- Search and embedding indexes are eventually consistent through async workers.
- Reports read from materialized match results to avoid re-running expensive ranking work.

## Reliability And SLO Targets

| Workflow | Target |
| --- | --- |
| Health/readiness | p95 under 100 ms |
| Cached reads | p95 under 500 ms |
| Demo ranking | p95 under 2 s |
| Recruiter API availability | 99.9% |
| Audit event durability | No decision-impacting action without an audit row |

## Production Deployment Path

1. Replace SQLite with PostgreSQL and Alembic migrations.
2. Move in-process cache to Redis.
3. Move resume files to object storage.
4. Add a job queue for resume parsing, embedding refresh, and ranking bursts.
5. Add OpenTelemetry traces and Prometheus metrics.
6. Introduce tenant IDs across users, candidates, jobs, matches, and audit logs.
7. Add backup/restore tests and disaster recovery runbooks.
8. Gate model changes through offline evaluation, bias review, and rollout flags.

## Local Operational Endpoints

| Endpoint | Purpose | Access |
| --- | --- | --- |
| `GET /health`, `GET /api/health` | Liveness, version, uptime, request ID | Public |
| `GET /ready`, `GET /api/ready` | Dependency readiness | Public |
| `GET /api/system/overview` | Topology, counters, cache, traffic, scale path | ADMIN, RECRUITER |
| `GET /api/system/audit?limit=20` | Recent audit events | ADMIN |
