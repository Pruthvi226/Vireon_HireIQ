# Vireon HireIQ API Documentation

Base URL: `http://localhost:8000`

## Health

`GET /health`

`GET /api/health`

Returns backend and database status.

## Demo Seed

`POST /api/demo/seed`

Creates one AI Intern job, three candidates, rankings and a baseline experiment record.

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
