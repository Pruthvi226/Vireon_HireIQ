# Changelog

## Unreleased

### Source audit and reliability improvements — October 2026

- Restricted public signup to candidates and added interactive local staff provisioning.
- Centralized runtime configuration, rejected unsupported database URLs, and enforced signing-key validation.
- Added dedicated candidate and admin dashboards, recruiter search/pagination and job/pipeline controls.
- Added session validation, single-flight refresh/retry and server logout calls.
- Added document/body/archive budgets, strict parsing, CSV formula escaping and sanitized public probes.
- Closed SQLite connections, fixed compatibility index ordering and invalidated stale rankings.
- Batched ranking writes; measured 100-candidate cold median from 530.295 ms to 85.259 ms locally.
- Added keyboard navigation, drawer focus/escape handling, accessible states and lazy page bundles.
- Upgraded advisory-affected backend packages and removed unused Axios/Tailwind frontend dependencies.
- Added dependency audit gates, reliable container test exit handling, loopback bindings and a tested backup utility.
- Added source audit, deployment/recovery runbook, feature roadmap and current verification report.
- Classified demo metrics as unevaluated fixtures and documented scoring/model limits.

The entries below describe earlier work; their coverage figures are historical.

- Added short-lived access tokens, rotating hashed refresh tokens, logout revocation, password reset, and login lockout.
- Added paginated candidate, job, and admin list envelopes with filtering and sorting.
- Added job lifecycle status and audited pipeline stage transitions.
- Added isolated bulk resume upload with ZIP support and resume content validation.
- Added candidate-facing interview-kit and skill-gap CSV/PDF exports.
- Added persisted model evaluation via `backend/scripts/evaluate.py`.
- Added JSON request logging, Prometheus metrics, notification hooks, security headers, and non-root backend packaging.
- Added backend regression tests with an 83% measured coverage baseline.
