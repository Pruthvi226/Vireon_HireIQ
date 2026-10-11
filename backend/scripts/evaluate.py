from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import candidate_out, connect, init_db, job_out, score_match


def evaluate() -> dict:
    init_db()
    labels: list[int] = []
    predictions: list[int] = []
    pairs = 0
    with connect() as db:
        candidates = [candidate_out(row) for row in db.execute("SELECT * FROM candidates").fetchall()]
        jobs = [job_out(row) for row in db.execute("SELECT * FROM jobs WHERE status='open'").fetchall()]
        for candidate in candidates:
            for job in jobs:
                result = score_match(candidate, job, True)
                required = set(job["required_skills"])
                overlap = len(set(candidate["skills"]) & required) / max(1, len(required))
                human_style_label = int(overlap >= 0.5 or (overlap >= 0.3 and result["project_score"] >= 50))
                labels.append(human_style_label)
                predictions.append(int(result["final_score"] >= 58))
                pairs += 1
        if not pairs:
            raise RuntimeError("No candidate-job pairs available; seed demo data first")
        metrics = {
            "model_name": "HybridScoreCalibratedShortlistBaseline",
            "accuracy": round(accuracy_score(labels, predictions), 4),
            "precision": round(precision_score(labels, predictions, zero_division=0), 4),
            "recall": round(recall_score(labels, predictions, zero_division=0), 4),
            "f1_score": round(f1_score(labels, predictions, zero_division=0), 4),
            "parameters": {"pairs": pairs, "label_rule": "skill overlap >= 0.5 or overlap >= 0.3 with project evidence", "threshold": 58},
            "created_at": datetime.utcnow().isoformat(),
        }
        db.execute(
            "INSERT INTO model_experiments (model_name, accuracy, precision, recall, f1_score, parameters_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (metrics["model_name"], metrics["accuracy"], metrics["precision"], metrics["recall"], metrics["f1_score"], json.dumps(metrics["parameters"]), metrics["created_at"]),
        )
        db.commit()
    return metrics


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
