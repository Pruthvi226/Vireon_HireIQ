# Deployment and recovery runbook

Prepared 2026-10-10. No service has been deployed or purchased. Commands below
are for an explicitly approved target. Local tests, Compose configuration
validation and container builds have run. See the dated container verification
in [VERIFICATION.md](VERIFICATION.md). HTTPS and restore drills on a target
have not run because no hosting target is supplied.

## Supported deployment shape

Use one API process, one Nginx frontend and a durable local SQLite/resume volume
for one organization. PostgreSQL, company isolation, distributed ranking cache
and queue workers require further engineering. `DATABASE_URL=postgresql://...`
now fails clearly rather than silently using SQLite. The Alembic baseline is a
placeholder; `alembic upgrade head` does not create or migrate the application
schema. Current SQLite startup initializes tables and applies additive
compatibility columns; back up before upgrading an existing installation.

## Hosting evaluation

| Choice | Fit for current code | Operational requirements |
| --- | --- | --- |
| Existing Docker host / VM | Closest fit to provided Compose | Durable disk, TLS proxy, OS updates, encrypted off-host backups, monitoring |
| Render | Possible as a paid backend with persistent disk plus static frontend | Build-time API URL, CORS, SPA rewrites, disk path and health endpoint |
| Railway | Possible with backend persistent volume and separately hosted frontend | Volume mount, API URL, secrets, CORS and platform networking |
| Static frontend host | Suitable for `frontend/dist` only | Separate durable backend, API URL and SPA rewrites |

Render's filesystem is ephemeral unless a persistent disk is attached; disks
are available on paid services. Its free service cannot persist the current
SQLite database and uploads. See [Render disks](https://render.com/docs/disks)
and [free-service limitations](https://render.com/docs/free).
Railway supports persistent [volumes](https://docs.railway.com/volumes/reference)
and [volume backups](https://docs.railway.com/volumes/backups).

Recommendation: validate the existing Compose stack on a private Docker host
first. Choose managed hosting only after budget, region, domain and retention
requirements are known. No price or availability promises are made here.

## Environment separation

Root `.env.example` is for Compose production; `backend/.env.example` is for
local development. Each staging/production environment needs its own signing
secret, data volume and deployment project name. Never reuse production resumes
in tests. The frontend's `VITE_API_BASE_URL` is public build-time configuration,
not a place for secrets. Keep it unset for same-origin Compose; for a split
deployment set it to `https://api.example.com/api` before building.

| Variable | Purpose |
| --- | --- |
| APP_ENV | `local/dev/development/test` enables demo endpoints; other values disable them |
| JWT_SECRET_KEY | Required non-placeholder 32+ characters; generate a random secret |
| JWT_EXPIRE_MINUTES | Access token lifetime, default 15 |
| VIREON_DATA_DIR | Local data directory; Compose fixes this to `/app/storage` |
| DATABASE_URL | Optional `sqlite:///...` only; defaults to data-dir SQLite file |
| VIREON_SQLITE_JOURNAL_MODE | Use WAL on normal durable storage; MEMORY only for local synced folders |
| MAX_RESUME_BYTES | Default 5242880; proxy body limit must accommodate bulk overhead |
| VIREON_CACHE_TTL_SECONDS | Process-local ranking TTL, default 60 |
| VIREON_RATE_LIMIT_PER_MINUTE | Default 240 per client; 0 disables it for controlled tests only |
| CORS_ALLOWED_ORIGINS | Comma-separated exact frontend origins |
| REDIS_URL | Optional shared rate limiter; unavailable Redis falls back to process memory |
| ENABLE_EMBEDDINGS / EMBEDDING_MODEL | Optional local model; needs the extra requirements and model files |

Without a local JWT secret, a random per-process development key is used;
restarts invalidate sessions and multiple workers cannot share it. Production
always requires a supplied secret. Do not enable optional embeddings until its
dependencies and model download/runtime behavior are verified separately.

## Local release checks

PowerShell from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests --cov=app --cov=auth --cov-fail-under=80
Set-Location frontend
npm ci
npm test
npm run build
npm audit --audit-level=high
Set-Location ..
```

To start a fresh local environment, copy `backend/.env.example` to `backend/.env`,
then `cd backend` and run `uvicorn app.main:app --reload --port 8000` after
installing `requirements.txt`. Run `npm run dev` in `frontend`. Seed demo accounts
only in that development environment. Smoke testing writes demo and workflow
data, so run it only against an isolated test service:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

## Approved Docker target

Commands use POSIX shell on the host. Docker Compose only binds localhost by
default; the service stays private until a TLS reverse proxy is deliberately
configured. Do not change bindings or DNS without deployment approval.

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Put the generated value in JWT_SECRET_KEY; keep APP_ENV=production.
# Set CORS_ALLOWED_ORIGINS=https://hire.example.com if using that domain.
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.test.yml build
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --no-deps backend
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --no-deps frontend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
curl --fail http://127.0.0.1:8000/api/ready
curl --fail http://127.0.0.1:8080/health
docker compose ps
```

Provision the first trusted admin interactively; its password is not passed on
the command line. Repeat with `--role RECRUITER` for trusted recruiting staff:

```bash
docker compose exec backend python scripts/provision_user.py \
  --name 'Workspace Admin' --email admin@example.com --role ADMIN
```

Log in through the frontend. Public signup creates candidates. Demo accounts
are disabled in production. Password reset delivery is not implemented;
production reset requests return 503 instead of issuing an undeliverable token.

## HTTPS and edge controls

Terminate HTTPS at a host reverse proxy, point its approved domain to that host,
and proxy to `127.0.0.1:8080`. Provision and renew certificates through that
proxy's supported ACME workflow. Configure a 26 MB request body budget (default),
request timeouts and edge rate limits. Keep port 8000 private. Enable HSTS at the
TLS proxy after verifying HTTPS. Test certificate renewal, redirects, login,
uploads and API responses from the intended network before accepting users.
The Nginx config proxies `/api` and serves SPA routes; production API traffic is
same-origin. Externally hosted frontends need equivalent SPA rewrites.

## CI and release promotion

GitHub Actions tests the Python API with an 80% coverage gate and audits its
installed dependency graph, tests/builds the
frontend, checks npm advisories, builds/scans containers and runs container tests.
Each test service runs independently so its exit code can fail CI. Audit artifacts
and Compose cleanup run even after failures. No automatic deployment is configured.
Promote only an immutable image digest/commit tested in staging. Save previous
image digests and a pre-upgrade backup before a production promotion.

## Backup, restore and rollback

The backup script uses SQLite's backup API, checks database integrity and copies
resume files into a new destination. It refuses to overwrite a prior backup or
write inside the live data directory. Freeze uploads/writes for a consistent
database-plus-files snapshot. Store encrypted backups off-host with access
controls and a retention policy; snapshots contain personal data.

```bash
docker compose exec backend python scripts/backup.py --output /tmp/hireiq-backup-20261010
docker cp vireon-hireiq-api:/tmp/hireiq-backup-20261010 ./hireiq-backup-20261010
```

Restore drill (isolated local environment; never overwrite live production data):

```bash
mkdir -p ./restore-drill/resumes
cp ./hireiq-backup-20261010/vireon_hireiq.sqlite ./restore-drill/
cp -R ./hireiq-backup-20261010/resumes/. ./restore-drill/resumes/
APP_ENV=test VIREON_DATA_DIR="$PWD/restore-drill" \
  python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011
# In another terminal:
curl --fail http://127.0.0.1:8011/api/ready
```

Uploaded file paths currently store absolute runtime paths. A restored environment
must reproduce the original data mount if later functionality reads those paths;
current score/profile pages use stored resume text. Validate login, counts and
resume evidence before selecting a restored volume for production. Never use
`docker compose down -v` on a production stack. Schema rollback is not automated;
restore to a separate volume and switch only after explicit approval. Application
rollback means restarting the previous tested image digests with compatible data.

## Monitoring and troubleshooting

Watch `/api/ready`, 5xx frequency, disk utilization, memory, request latency and
backup age. Logs include request IDs; `/metrics` and ops counters are per process,
not a centralized monitoring system. Configure your monitoring target before
promising availability or SLOs. Alert on readiness failures, sustained errors,
disk pressure and missed backups. Keep logs access-restricted; notification logs
can contain candidate identifiers and screening scores.

- JWT startup failure: supply a strong secret to the correct environment file.
- Unsupported database URL: use SQLite; PostgreSQL integration is pending.
- Missing candidate data: candidate users can only access their own resumes.
- Upload 400: verify supported type, size and readable text; invalid documents do not fall back to binary text.
- Upload 413: align proxy and API budgets; reduce the bulk batch.
- Rank 409: the job must be open.
- Frontend 401: inspect refresh/login; a server restart with an ephemeral dev key invalidates old tokens.
- Tests spawn EPERM / temp access errors in managed Windows environments: run authorized local checks outside the sandbox.
- Docker pipe unavailable: start Docker Desktop and rerun container verification.

Production release remains conditional on Docker/image scans, target restore
drills, manual browser/accessibility verification and the intended single-company
scope. Multi-company use, automated hiring decisions and high availability need
the P3 architecture/model work documented in the audit.
