# Vireon HireIQ API Documentation

Base URL: `http://localhost:8000`

## Health and Readiness

`GET /health`

`GET /api/health`

Returns liveness, API version, uptime, database type and request ID. Filesystem paths are not returned by public probes.

`GET /ready`

`GET /api/ready`

Returns dependency readiness checks for SQLite and runtime storage. A failed check returns `503`.

## Platform Operations

`GET /api/system/overview`

Returns topology, readiness, data counts, traffic counters, cache stats, resilience controls, SLO targets and production scale path. Requires ADMIN or RECRUITER.

`GET /api/system/audit?limit=20`

Returns recent audit events with actor role, action, resource, metadata, request ID and timestamp. Requires ADMIN.

## Demo Seed

`POST /api/demo/seed`

Creates one AI Intern job, three candidates, rankings, a baseline experiment record and an audit event.

Both `/api/demo/seed` and `/api/demo/seed-users` return `404` outside local/dev/development/test environments.

## Candidates

`POST /api/resumes/text`

```json
{
  "name": "Candidate Name",
  "resume_text": "Resume text with skills, projects, education and experience"
}
```

`POST /api/resumes/upload`

Multipart form with `file` and optional `candidate_name`.

`GET /api/resumes/limits`

Requires an authenticated candidate, recruiter or administrator. Returns current
`max_resume_bytes`, `max_bulk_bytes`, `max_bulk_files`, `extensions` and
`archive_extension`. Upload interfaces read these values rather than assuming
the default deployment configuration.

`GET /api/candidates`

Lists parsed candidates using `page`, `page_size`, `search`, and `sort`; returns `{items,total,page,page_size}`.

`POST /api/resumes/bulk`

Multipart `files` upload accepting multiple resumes or ZIP archives. Returns per-file success/error results.

Recruiter/admin access is required. The response is
`{results:[{filename,status,candidate?|error?}],succeeded,failed}`. The multipart
byte budget is checked before importing any document. ZIP expansion budgets
are shared across the whole batch. Successful imports remain saved when another
entry fails; retry only failed documents to avoid duplicate candidates. A lost
response can have an uncertain outcome, so check the candidate list before retrying.

Defaults: 5 MB per resume, 25 files per request, 25 MB bulk byte budget,
100:1 maximum ZIP entry expansion ratio, 100000 extracted characters, and a
26 MB transport body limit including multipart overhead. Limits are enforced
before archive entries are read. Invalid single resumes return `400`; body
budget violations return `413`. Scanned/image-only PDF files require text
extraction before upload; OCR is not implemented.

## Jobs

`POST /api/jobs/create`

```json
{
  "title": "Artificial Intelligence Intern",
  "company": "QuickHyre AI",
  "description": "Job description text"
}
```

`GET /api/jobs`

Lists parsed job descriptions using pagination/filtering and the `status` filter (`draft`, `open`, `closed`, `archived`).

Candidates only receive open jobs. Defaults: `page=1`, `page_size=25`; maximum
page size is 100. Candidate sorting accepts `created_at|name`; job sorting
accepts `created_at|title|status`. Validation errors return `422`.

`PATCH /api/jobs/{job_id}/status`

```json
{"status":"closed"}
```

Requires RECRUITER or ADMIN. Closed and archived jobs cannot be ranked.

## Matching

`POST /api/match/candidate`

```json
{
  "candidate_id": 1,
  "job_id": 1,
  "bias_safe": true
}
```

`GET /api/jobs/{job_id}/rank-candidates`

Ranks every candidate for an open job.

`PATCH /api/match/{match_id}/stage`

```json
{"pipeline_stage":"Interview"}
```

Requires RECRUITER or ADMIN and appends an audit event.

## Skill Gap and Interview

`GET /api/candidates/{candidate_id}/skill-gap/{job_id}`

`POST /api/interview/generate`

```json
{
  "candidate_id": 1,
  "job_id": 1,
  "include_answer_hints": true
}
```

## Analytics, Chat and Reports

`GET /api/analytics/job/{job_id}`

`POST /api/chat/hr`

```json
{
  "question": "Who knows Python and NLP but lacks Computer Vision?",
  "job_id": 1
}
```

`GET /api/reports/job/{job_id}?format=csv`

Candidate exports are available at `/api/candidate/skill-gap/{job_id}/export?format=csv|pdf` and `/api/candidate/interview-kit/{job_id}/export?format=csv|pdf`.

`GET /metrics`

Prometheus exposition format for request counts, errors, and latency percentiles.

## Authentication lifecycle

`POST /api/auth/register` creates CANDIDATE accounts only. `role` defaults to
`CANDIDATE`; requesting ADMIN or RECRUITER returns `403`. Staff accounts are
provisioned locally with `backend/scripts/provision_user.py`.

```json
{"name":"Jane Doe","email":"jane@example.com","password":"example-password-123"}
```

`POST /api/auth/login` accepts `{email,password}`. Register/login/refresh return
`{access_token,token_type,refresh_token,user}`. Authenticated calls send
`Authorization: Bearer <access_token>`. Passwords require at least eight
characters on creation/reset and at most 72 UTF-8 bytes for bcrypt.

`POST /api/auth/refresh` rotates a hashed seven-day refresh token. `POST /api/auth/logout` revokes all refresh tokens for the user. Password reset uses `/api/auth/password-reset/request` and `/api/auth/password-reset/confirm`; five failed logins trigger a temporary lockout.

Refresh body: `{ "refresh_token": "<token>" }`. Reset confirmation body:
`{ "token": "<token>", "password": "<new password>" }`. Reset tokens are
returned only during development. Production reset requests return `503`
until a delivery adapter is implemented. Logout/reset invalidate refresh
tokens; previously issued access tokens expire naturally within 15 minutes.
Expired/invalid tokens return `401`; wrong roles return `403`; failed login
lockout returns `423`; throttling returns `429` with `Retry-After`.

Candidate APIs (`/api/candidate/profile`, `/api/candidate/ats-score?job_id=...`,
`/api/candidate/skill-gap/{job_id}`, `/api/candidate/resume-improvement/{job_id}`)
use the current user's owned resume by default. Optional `candidate_id` must
belong to that user; other candidates return `404`. ADMIN can inspect a
specified candidate. Recruiters currently share one workspace, with no tenant isolation.

CSV exports escape formula-leading candidate names and job titles. Match
`shortlist_probability` is retained for API compatibility but is an uncalibrated
heuristic. Seeded experiment rows are fixtures; rule-generated evaluation
labels do not establish real hiring accuracy.

Decision-impacting write/read workflows append audit events: candidate creation, job creation, matching, ranking, interview kit generation, HR assistant query and report export. Responses include `X-Request-ID` and `X-Process-Time-Ms` headers.


## Smoke Test

Run the full live API smoke suite against a started backend:

```bash
python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```
