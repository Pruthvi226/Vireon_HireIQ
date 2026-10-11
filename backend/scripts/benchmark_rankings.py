"""Local cold/warm timing; requires an isolated, empty runtime directory."""
import json
import logging
import sys
import time
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app.main as main


def benchmark():
    if main.DB_PATH.exists():
        raise RuntimeError("Use a new VIREON_DATA_DIR; benchmark will not mutate an existing database")
    main.logger.setLevel(logging.WARNING)
    main.init_db()
    with main.connect() as db:
        job = main.create_job_record(db, main.parse_jd("Build Python FastAPI APIs using SQL Docker Git and automated testing.", "Backend Engineer", "Benchmark"))
        for index in range(100):
            main.create_candidate_record(db, main.parse_resume(f"Candidate {index}\nPython FastAPI SQL Docker Git\nProjects: built backend API and data workflows\nExperience: backend intern building API automation\nEducation: Computer Science", f"Candidate {index}"))
    def measure(cold):
        timings = []
        for _ in range(5 if cold else 20):
            if cold: main.invalidate_cache()
            start = time.perf_counter()
            ranked = main.rank_candidates_internal(job["id"])
            timings.append((time.perf_counter() - start) * 1000)
            assert len(ranked) == 100
        return {"runs": len(timings), "median_ms": round(median(timings), 3), "max_ms": round(max(timings), 3)}
    return {"candidates": 100, "journal": main.SQLITE_JOURNAL_MODE, "cold": measure(True), "warm": measure(False)}


if __name__ == "__main__":
    print(json.dumps(benchmark(), indent=2))
