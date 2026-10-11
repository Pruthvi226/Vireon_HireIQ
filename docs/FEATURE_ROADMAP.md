# Remaining feature and architecture decisions

These recommendations are based on the inspected implementation. They are not
implemented features or promises of production readiness. Do not add unrelated
social, billing, realtime or generative AI features before the release checks.

Candidate PDF/CSV downloads and recruiter batch import are implemented.
See [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md) for the changed
files, behavior and verification. Container builds and strict image scans also
pass in CI; staging TLS and target restore verification remain outstanding.

| Priority / Feature | What and why | User benefit | Frontend work | Backend / DB work | Complexity | Required validation |
| --- | --- | --- | --- | --- | --- | --- |
| P1 · Reset delivery | Deliver single-use account recovery links; production currently returns 503 | Users can recover access without support | Request/confirm pages with generic outcomes and clear expired-link states | Verified mail adapter, rate limits, retry policy; existing hashed token table | Medium | Delivery failure, enumeration resistance, replay, expiry, reset revocation |
| P1 · Durable release verification | Validate Docker builds, image scans, TLS and restore on staging | Confidence that local workflows survive deployment | Manual desktop/mobile and keyboard checks | Staging volume, monitoring and backup target; CI configured already | Medium | Container startup, full smoke suite, backup integrity, restored resume evidence, HTTPS renewal |
| P2 · Accessible responsive polish | Verify and refine real-device layouts and reading order | Keyboard and assistive-technology access | Current focus/labels/reduced-motion work plus manual contrast and mobile review | No DB changes | Medium | Screen reader, 200% zoom, small viewport, focus trap/restore, contrast checks |
| P3 · Organization isolation | Scope every recruiter resource to a company before shared SaaS hosting | Keeps independent organizations' data separate | Invitations, workspace switching and role-aware administration | Organization/membership tables, ownership backfill, scoped queries, audit and cache keys | High; requires approved migration | Cross-company access for every route, export, cache and search; migration/rollback fixtures |
| P3 · PostgreSQL repositories | Replace SQLite-specific SQL and initialize real migrations | Durable multi-instance operation | Preserve API contracts | Repositories, schema constraints, transaction tests, connection pools, migration/backfill | High; requires approved migration | PostgreSQL integration, migrations from representative data, concurrency, backup/restore |
| P3 · Background parsing/ranking | Queue long work only when measured traffic warrants it | Progress and reliable retries during large imports | Job progress, retry/cancel feedback | Queue, worker, idempotency keys, bounded resources and shared result cache | High | Duplicate deliveries, worker crash, timeout, queue saturation and result consistency |
| P3 · Evidence-based model evaluation | Use independently labeled candidate/job pairs and calibrated thresholds | More trustworthy explanations | Distinguish estimated scores from reviewed evidence | Evaluation datasets, calibration, fairness review, versioned scoring and rollout gates | High | Held-out labels, drift/fairness checks, regression comparisons; synthetic labels are insufficient |
| P3 · Retention / deletion | Establish resume retention and consent requirements | Control over personal information | Clear consent and account/data removal flows | Retention policy, deletion jobs, file/database/audit dependencies and backup retention | Medium/High | Authorization, referential integrity, orphan files, retention schedules and restore behavior |

Before extracting `app/main.py` into route/service/repository modules, add contract
tests and move one responsibility at a time. A broad rewrite risks changing score
semantics, transaction boundaries, audit behavior and ownership checks. Shared
configuration, connection management, transport limits, session handling and page
components have already been extracted without changing the framework.
