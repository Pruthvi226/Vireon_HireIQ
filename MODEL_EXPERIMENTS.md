# Model Experiments

The MVP uses a hybrid scoring pipeline and an uncalibrated shortlist heuristic.
The API retains the `shortlist_probability` field for compatibility; it does not
represent a validated probability of a real hiring outcome.

## Features

- `semantic_score`: local `all-MiniLM-L6-v2` embedding similarity when `ENABLE_EMBEDDINGS=true` and `requirements-embeddings.txt` is installed, with token-vector cosine fallback when the model is disabled or unavailable
- `skill_score`: required skill coverage
- `project_score`: evidence of role-relevant projects
- `experience_score`: work or internship relevance
- `keyword_score`: JD keyword coverage in resume evidence
- `education_score`: degree, coursework and certification evidence
- `final_score`: weighted fit score

## Evaluation

Run `python backend/scripts/evaluate.py` after seeding data. The script evaluates every available candidate/open-job pair, applies a documented synthetic human-style label rule, writes the computed metrics to `model_experiments`, and `/api/model/experiment` returns the latest stored row. Metrics are computed at runtime and are not hardcoded.

New demo seeding records `DemoFixtureUnvalidated` with zero-valued placeholders
and `evaluated=false`; these are not evaluation results. The API distinguishes
`unevaluated_fixture` from `synthetic_labels`, and the dashboard hides fixture
metrics. Old hardcoded demo rows remain in existing databases but are also
classified as unevaluated; no historical data is rewritten.

The evaluation script's labels are derived from skill overlap and project
signals used by the scoring engine itself. Agreement with those labels is not
independent validation, calibration or evidence of hiring accuracy. A reviewed
held-out dataset is needed before making those claims.

## Next Iteration

The next iteration can replace the deterministic label rule with reviewed labels and a persisted scikit-learn model while keeping the same API contract.
