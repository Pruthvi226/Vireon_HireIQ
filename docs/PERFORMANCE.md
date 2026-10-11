# Performance Testing

The Locust scenario in `backend/tests/load/locustfile.py` targets ranking and analytics.

## Local measurements — 2026-10-10

Windows, Python 3.13.2, SQLite MEMORY journal, one process, 100 synthetic resumes
and one job. `backend/scripts/benchmark_rankings.py` creates a new isolated
database, runs 5 uncached rankings and 20 cached rankings. Both stages used the
same data-generation code; the change batches match writes into one transaction.

| Measurement | Before (commit per match) | After (commit per ranking) |
| --- | --- | --- |
| Cold median | 530.295 ms | 85.259 ms |
| Cold maximum | 559.976 ms | 89.525 ms |
| Cached median | 3.713 ms | 2.497 ms |

These are sequential local function timings, not API p95, load-test results or
Core Web Vitals. Filesystem caching and host load affect comparisons. The main
evidence is the cold-ranking reduction; warm differences are small absolute
times and should not be treated as a dependable improvement.

Initial production JS changed from 349.75 kB (110.19 kB gzip) to 190.88 kB
(62.81 kB gzip) through lazy role-page loading. The recruiter bundle is loaded
after routing. All JS combined is larger because real candidate/admin pages
were added. Build output measures bundle size, not browser load latency.

To repeat safely, set `APP_ENV=test` and `VIREON_DATA_DIR` to a new directory,
then run `python backend/scripts/benchmark_rankings.py`. The script refuses
to modify an existing database.

Start a seeded API, then run:

```bash
locust -f backend/tests/load/locustfile.py --host http://127.0.0.1:8000
```

Capture API p50 and p95 latency at 20 and 50 concurrent users for each release.
Docker-backed load results and Core Web Vitals remain unmeasured.
