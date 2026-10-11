# Project audit and improvement roadmap

Reviewed 2026-10-10 against the source in this workspace. Historical README smoke
results are not evidence that this checkout passes today.

## What the application does

Vireon HireIQ helps recruiters turn resumes and job descriptions into structured
profiles, compare candidates, inspect skill gaps, prepare interviews, and export
rankings. Candidates have backend endpoints for their own resumes and guidance.
Admins have endpoints for users, aggregate statistics, and audit events.

## How it works

The browser runs React 18 with Vite, React Router and Framer Motion. `RootApp.jsx`
selects a page after login. `api.js` calls `/api`; Vite proxies that prefix locally,
and Nginx proxies it inside Docker. FastAPI validates requests, checks the bearer
JWT against a current database user, and executes parameterized SQLite queries.
Resume parsing extracts known skills and sections. Matching combines token cosine
similarity, skill overlap, projects, experience, keywords and education into a
weighted score. Optional local sentence-transformer embeddings replace cosine
when installed and enabled. No external LLM is required by the current assistant.

`backend/app/main.py` contains routes, schema initialization, parsing, matching,
exports, metrics, caching and rate limiting. `auth/` implements bcrypt passwords,
JWTs, lockout, hashed refresh tokens and password-reset tokens. `semantic.py` and
`notifications.py` supply optional embeddings and a console notification adapter.

SQLite holds users, candidates, jobs, unique candidate/job matches, model
experiments, audit logs, refresh tokens and reset tokens. Lists in profiles are
stored as JSON text. Resume bytes are stored on disk. Candidate ownership uses
`owner_user_id`. Jobs and recruiter data currently belong to one shared workspace;
there is no company/tenant boundary. Foreign-key enforcement is enabled but most
table declarations have no foreign-key constraints. Startup creates tables and
adds a few compatibility columns. Alembic's baseline is empty, and PostgreSQL is
not implemented by the runtime despite an optional Compose service.

## Verified feature inventory before changes

| Area | Existing implementation | Limitation |
| --- | --- | --- |
| Identity | Register, login, role guards, refresh, logout, lockout, reset | Public ADMIN registration; browser does not use refresh or validate stored identity |
| Resume ingestion | Text, TXT/PDF/DOCX, bulk files and ZIP | Unbounded reads/decompression; invalid upload raises 500; parsers fall back to binary text |
| Jobs | Create, list/search/sort/page, lifecycle status | Lifecycle controls absent from browser; candidates can list drafts |
| Matching | Weighted scores, ranking cache, evidence, shortlist heuristic | Stage changes leave stale cache; commits for every candidate; probability is uncalibrated |
| Pipeline | Stage update and audit/notification event | API exists; browser lacks control |
| Candidate self service | Profile, ATS score, roadmap, resume advice, CSV/PDF exports | Candidate page is an alias for recruiter App |
| Administration | Paged users, candidates/jobs, aggregate analytics, platform data | Admin page is an alias for recruiter App |
| Recruiter UI | Overview, job lab, resumes, matrix, assistant, ops, theme, drawer | Initial refresh errors unhandled; only first 25 rows; mouse-only navigation; stale job insights |
| Operations | Health/readiness, request IDs, structured logs, metrics, audit, Redis limiter fallback | Local cache/metrics; health shares request quota; raw route cardinality; no tracing backend |
| Delivery | Dockerfiles, Compose, GitHub Actions, unit/API/component tests, smoke and Locust scripts | CI coverage target needs measurement; Docker test exit handling; no real deployment evidence |

## Prioritized roadmap

| Priority | Issue / Feature | Proposed Improvement | Files Affected | Complexity | Expected Benefit |
| --- | --- | --- | --- | --- | --- |
| P0 | Public privileged registration | Limit public roles to candidates; provision staff locally | auth/auth_routes.py, scripts/provision_user.py, tests | Low | Stops unauthenticated privilege escalation |
| P0 | Empty signing secret / unsupported DB URL | Central configuration; random development key, fail closed elsewhere; reject unsupported databases | app/config.py, auth/security.py, app/main.py | Low | Reliable startup and explicit storage selection |
| P0 | Upload abuse and invalid inputs | Bounded reads, archive budgets, typed errors, strict document parsing | app/main.py, tests | Medium | Limits memory use and avoids invalid stored resumes |
| P0 | Vulnerable pinned backend packages | Apply advisory fixes and verify transitive dependencies | requirements.txt, CI, tests | Medium | Avoids rebuilding known vulnerable versions |
| P0 | Missing candidate/admin interfaces | Connect existing APIs to dedicated role pages | pages/*Dashboard.jsx, api.js, component tests | Medium | Working role-specific user journeys |
| P1 | Session state and expiry | Validate identity, refresh once, revoke on logout, shared errors | auth/AuthContext.jsx, api.js, auth/session.js | Medium | Predictable session recovery |
| P1 | Stale rankings | Invalidate stage updates and explicit matches; clear UI on context changes | app/main.py, App.jsx, tests | Low | Accurate current decisions |
| P1 | SQLite handles / upgrade order | Close connections explicitly; create ownership index after compatibility column | app/database.py, auth/auth_service.py, app/main.py | Low | Reliable resource and legacy schema handling |
| P1 | CI / deployment accuracy | Gate actual tests, correct container exit handling, local-only bindings, backup/restore runbook | .github/workflows, compose, PRODUCTION.md | Medium | Reproducible release checks |
| P2 | Discoverability / accessible design | Search/pagination, real buttons, focused dialogs, usable auth forms, reduced motion | App.jsx, components, index.css, pages | Medium | Keyboard/mobile access and discoverable data |
| P2 | Hiring pipeline | Expose existing stage/status endpoints with validation and feedback | api.js, App.jsx | Medium | Recruiters can manage progress |
| P3 | Tenant isolation | Add organizations, invitations and ownership checks across every resource | DB migration, all recruiter routes | High | Required before unrelated organizations share a deployment |
| P3 | PostgreSQL + background workers | Build repositories and real migrations, then queue parsing/ranking | backend, alembic, Compose | High | Multi-replica capacity; requires separately approved migration |
| P3 | Model evaluation | Independent labeled dataset, calibration and fairness analysis | scripts/evaluate.py, semantic.py, docs | High | Evidence for model quality; existing synthetic labels are insufficient |
| P3 | Password reset delivery / storage | Configure a verified mail adapter and object storage policy | auth, notifications, deployment | Medium | Real reset recovery and durable uploads |

## UI audit and design plan

Keep the current teal palette, dark/light CSS variables, rounded panels and spacing.
Use system font fallbacks rather than adding font/network dependencies. Add visible
focus, semantic labels, alert/status announcements, comfortable controls, reduced
motion and a keyboard-contained drawer. Auth pages should have empty credentials,
autocomplete, validation and submission feedback. Candidate pages should lead with
resume upload and a selected open job, then score, gaps and advice. Admin pages
should lead with counts, searchable users and audit history. Recruiter pages should
retain the established layout and gain pagination and pipeline controls.

Reusable components should handle page headers, asynchronous states, pagination
and dialog focus. A complete WCAG 2.2 AA claim requires manual keyboard, contrast,
screen-reader and responsive verification; CSS changes alone do not certify it.

## Testing and production boundaries

Add meaningful regressions for privileged signup, ownership, upload boundaries,
cache invalidation, reset/refresh replay and frontend sessions and role workflows.
Run existing suites, build and smoke where possible. Measure cold/warm ranking
with the same seeded dataset; do not generalize local timings to production.
Docker health, TLS, restore drills and load tests need a working target environment.

Prepare a single-instance SQLite deployment first. Do not deploy, change live
infrastructure, publish, purchase services or migrate existing production data in
this work. Hosting comparisons must be checked against current provider docs.
Git status currently reports an unrelated repository path; preserve changes in
place until repository metadata is understood, without rewriting history.
