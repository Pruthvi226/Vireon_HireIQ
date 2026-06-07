# Production Notes

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
