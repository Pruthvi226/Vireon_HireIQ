# Verification report

Final verification date: 2026-10-11 (Asia/Calcutta). Source edits remain in this
workspace; nothing was published, deployed, purchased, migrated on a live system,
or committed. Git commands fail because repository metadata resolves to an
unrelated `Finance_Tracker/finance-tracker/.git` path. Metadata was not rewritten.

## Executed checks

| Check | Result / scope |
| --- | --- |
| Baseline backend tests | 11 passed; 82% statement coverage before improvements |
| Expanded backend suite | 37 passed; 86.35% statement coverage over app/auth; regression, API, config, body-limit and backup tests |
| Frontend Vitest | 10 passed across 6 files; login/errors, route guards, role workflows, refresh concurrency, keyboard drawer focus and score component |
| Production frontend build | Passed with Node 22.14.0 and Vite 6.4.3 |
| Live API smoke | 41 passed on upgraded loopback API at port 8012 with a fresh isolated SQLite directory |
| Python source compile | Passed for app/auth/schemas/models/scripts |
| Dependency consistency | `pip check`: no broken requirements |
| Python installed graph audit | `pip-audit`: no known vulnerabilities after upgrades |
| npm audit | Zero reported advisories after compatible source-map update and unused dependency removal |
| Compose validation | Base, production override and test override all passed `docker compose ... config --quiet` |
| Local benchmark | 100 synthetic candidates; cold median 530.295 → 85.259 ms; methodology in PERFORMANCE.md |
| Schema reference | Regenerated from an isolated runtime DB: eight tables and eight indexes |

Automated component tests run in jsdom, so they do not verify rendered geometry,
contrast, real browser behavior or Core Web Vitals. Backend coverage is statement
coverage over `app` and `auth`; it is not exhaustive path or security coverage.
Audit tools report known database entries at execution time, not proof of safety.
The installed Python graph was audited; optional embedding/load extras were not
installed or audited. Release CI repeats the scan against its resolved packages.
One Starlette test-client deprecation warning remains: its current HTTPX adapter
is supported but recommends a future `httpx2` test-client migration.

## Verified behavior changes

- ADMIN/RECRUITER public signup is denied; candidate signup works.
- Candidate resume ownership and unpublished-job boundaries are enforced.
- Production demo routes are disabled; development fixtures remain usable.
- Invalid/oversized documents return client errors and do not create stored resumes.
- ZIP file count, byte/expansion and transport-body limits are enforced.
- Pipeline changes invalidate cached rankings; explicit matching also invalidates cache.
- Legacy ownership columns are added before creating their index; handles close after transactions.
- Candidate/admin views call their appropriate APIs, with actionable loading/error states.
- Concurrent expired frontend requests share one refresh and retry with the new token.
- Recruiter navigation works with Enter; Escape closes the drawer and restores focus in component tests.
- Backups preserve database rows and resume files, check integrity and refuse overwrites.
- New seeded model fixtures no longer imply measured accuracy.

## Not executed / release gates

- Browser UI, screenshots, real viewport and screen-reader checks: no connected
  browser was available; Browser discovery returned an empty list.
- Docker image builds, containerized tests, Nginx runtime and Trivy scans: Docker
  Desktop daemon is not running. Only Compose configuration was validated.
- GitHub Actions itself was not run from this environment.
- Production TLS/domain verification, monitoring integration, disaster-recovery
  drills and rollback on a target: no approved deployment target supplied.
- Concurrent API load, WAL-specific performance, Core Web Vitals and fairness:
  not measured. Local sequential timings do not establish production SLOs.
- Production reset delivery, organization isolation, PostgreSQL repositories,
  background workers and distributed ranking cache: not implemented.

## Operational limitations

The supported architecture is one organization, one API process and durable
SQLite/filesystem storage. Access tokens remain valid until their short expiry
after logout/reset; refresh tokens are revoked. Browser tokens are held in local
storage, so protecting against XSS remains necessary. Console notification logs
can contain candidate identifiers and scores and need restricted access.

Alembic's baseline is empty and is not a PostgreSQL migration. Existing schema
startup changes are additive compatibility operations, not a reversible migration
system. Schema foreign-key declarations and tenant ownership are future work.
Synthetic evaluation labels do not validate hiring predictions. Consult the
[audit](PROJECT_AUDIT.md), [feature roadmap](FEATURE_ROADMAP.md) and
[deployment runbook](DEPLOYMENT_RUNBOOK.md) before selecting a release scope.

## Commands to repeat

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests --cov=app --cov=auth --cov-fail-under=80
.\backend\.venv\Scripts\python.exe -m pip check
.\backend\.venv\Scripts\python.exe -m pip_audit --progress-spinner off
Set-Location frontend
npm test
npm run build
npm audit --audit-level=high
```

Run smoke only against an isolated started test API. The suite writes demo and
workflow data. Initial sandbox attempts hit pytest temporary-directory access
errors and esbuild spawn EPERM; authorized runs outside the sandbox succeeded.

## Container security follow-up (2026-10-11)

Docker became available for this follow-up. Both updated production images built
locally. Trivy 0.70.0 scanned the final images with HIGH/CRITICAL severity and
without excluding unfixed vulnerabilities:

| Runtime image | Before | After | Remaining blocker |
| --- | --- | --- | --- |
| Backend | 48 findings (44 Debian, 4 Python) | 44 Debian, 0 Python | Debian stable has no patched versions listed for these findings |
| Frontend | 43 findings in the Nginx 1.27 Alpine base | 0 | None in this scan |

The backend now removes pip from both the copied virtual environment and the
system Python installation, along with ensurepip's installer wheels. Installation
remains in the build stage; runtime package installation is intentionally unavailable.
This removes the vulnerable bundled msgpack, setuptools and urllib3 copies.
Application dependency versions did not change. All 37 backend tests passed
inside the rebuilt Python 3.12 image with 86.35% statement coverage. Existing
deprecation warnings remain.

The frontend uses the verified Nginx 1.30.5 stable Alpine image pinned by digest
and upgrades Alpine packages during the build. Its production bundle built and
`nginx -t` passed with the application configuration.

The backend blocker covers eight distinct CVEs reported across multiple installed
Debian packages: CVE-2025-69720, CVE-2026-16742, CVE-2026-54369,
CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 and
CVE-2026-9538. The Debian tracker confirms the stable-release patch gap for
[util-linux](https://security-tracker.debian.org/tracker/CVE-2026-76642),
[ncurses](https://security-tracker.debian.org/tracker/CVE-2025-69720) and
[Perl](https://security-tracker.debian.org/tracker/CVE-2026-9538).
This is an unresolved release blocker, not an accepted exception or a clean scan.
Rebuild and rescan when Debian publishes patches; changing the runtime distribution
would require a separate compatibility review.

CI retains exit code 1 for all HIGH/CRITICAL findings, including unfixed findings.
The frontend scan runs even when the backend scan fails, and both JSON reports
are uploaded as the `image-vulnerability-reports` artifact. A failing image gate
must continue to block release approval.
