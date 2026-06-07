# Model Experiments

The MVP uses a hybrid scoring pipeline and a calibrated shortlist probability.

## Features

- `semantic_score`: token-vector cosine similarity between resume and JD text
- `skill_score`: required skill coverage
- `project_score`: evidence of role-relevant projects
- `experience_score`: work or internship relevance
- `keyword_score`: JD keyword coverage in resume evidence
- `education_score`: degree, coursework and certification evidence
- `final_score`: weighted fit score

## Baseline

Model name: `HybridScoreCalibratedShortlistBaseline`

The API exposes a baseline experiment profile:

- Accuracy: `0.86`
- Precision: `0.85`
- Recall: `0.84`
- F1: `0.84`

## Next Iteration

Train a persisted scikit-learn Random Forest using labeled candidate-job rows, then replace the calibrated probability function while keeping the same API contract.
