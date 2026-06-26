# Vireon HireIQ API Documentation

Base URL: `http://localhost:8000`

## Health and Readiness

`GET /health`

`GET /api/health`

Returns liveness, API version, uptime, database path and request ID.

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

`GET /api/candidates`

Lists parsed candidates.

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

Lists parsed job descriptions.

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

Ranks every candidate for a job.

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

Decision-impacting write/read workflows append audit events: candidate creation, job creation, matching, ranking, interview kit generation, HR assistant query and report export. Responses include `X-Request-ID` and `X-Process-Time-Ms` headers.


## Smoke Test

Run the full live API smoke suite against a started backend:

```bash
python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```
