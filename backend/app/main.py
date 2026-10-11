from __future__ import annotations

import csv
import copy
import contextvars
import json
import logging
import math
import os
import re
import sqlite3
import time
import unicodedata
import uuid
import zipfile
from contextlib import asynccontextmanager
from collections import Counter, deque
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from auth.auth_routes import router as auth_router
from auth.auth_service import init_auth_db, list_users, seed_demo_users
from auth.dependencies import get_current_user, require_roles
from app.notifications import ConsoleNotificationTransport, configure_transport, notify
from app.semantic import semantic_similarity
from app.config import APP_ENV, DATA_DIR, DB_PATH, JWT_SECRET_KEY, SQLITE_JOURNAL_MODE
from app.database import open_database
from app.body_limits import BodyLimitMiddleware


APP_NAME = "Vireon HireIQ"
SERVICE_VERSION = "2.0.0"
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DEFAULT_DATA_DIR = ROOT / "runtime"
RESUME_DIR = DATA_DIR / "resumes"
MAX_RESUME_BYTES = int(os.getenv("MAX_RESUME_BYTES", str(5 * 1024 * 1024)))
CACHE_TTL_SECONDS = int(os.getenv("VIREON_CACHE_TTL_SECONDS", "60"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("VIREON_RATE_LIMIT_PER_MINUTE", "240"))
REDIS_URL = os.getenv("REDIS_URL", "")
MAX_BULK_FILES = 25
MAX_BULK_BYTES = MAX_RESUME_BYTES * 5
STARTED_AT = datetime.utcnow()
REQUEST_ID_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
HTTP_METRICS: Counter[str] = Counter()
PATH_METRICS: Counter[str] = Counter()
LATENCY_MS: deque[float] = deque(maxlen=500)
RATE_BUCKETS: dict[str, deque[float]] = {}
CACHE: dict[str, dict[str, Any]] = {}
CACHE_STATS: Counter[str] = Counter({"hits": 0, "misses": 0, "sets": 0, "invalidations": 0})
RUNTIME_LOCK = Lock()
REDIS_CLIENT: Any = None


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            **getattr(record, "context", {}),
        })


logger = logging.getLogger("vireon")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
configure_transport(ConsoleNotificationTransport(logger))

SKILLS = {
    "Python": ["python"],
    "FastAPI": ["fastapi", "fast api"],
    "SQL": ["sql", "sqlite", "postgresql", "mysql"],
    "Machine Learning": ["machine learning", "ml", "classification", "regression", "random forest"],
    "NLP": ["nlp", "natural language", "text processing", "transformer", "embedding"],
    "Computer Vision": ["computer vision", "opencv", "ocr", "image processing"],
    "Pandas": ["pandas", "dataframe"],
    "NumPy": ["numpy"],
    "Scikit-learn": ["scikit-learn", "sklearn"],
    "PyTorch": ["pytorch", "torch"],
    "TensorFlow": ["tensorflow", "keras"],
    "FAISS": ["faiss", "vector search", "similarity search"],
    "RAG": ["rag", "retrieval augmented", "retrieval-augmented"],
    "Gemini API": ["gemini", "google generative ai", "llm"],
    "Data Preprocessing": ["preprocessing", "cleaning", "feature engineering", "etl"],
    "Model Evaluation": ["accuracy", "precision", "recall", "f1", "confusion matrix", "metrics"],
    "Visualization": ["plotly", "matplotlib", "dashboard", "visualization", "charts"],
    "Docker": ["docker", "container"],
    "REST API": ["rest", "api", "endpoint", "swagger"],
    "Git": ["git", "github"],
}


class ResumeTextRequest(BaseModel):
    name: str | None = Field(None, max_length=120)
    resume_text: str = Field(..., min_length=20, max_length=100000)


class JobCreateRequest(BaseModel):
    title: str | None = Field(None, max_length=160)
    company: str | None = Field(None, max_length=160)
    description: str = Field(..., min_length=30, max_length=50000)
    status: Literal["draft", "open", "closed", "archived"] = "open"


class MatchRequest(BaseModel):
    candidate_id: int = Field(..., gt=0)
    job_id: int = Field(..., gt=0)
    bias_safe: bool = True


class InterviewRequest(BaseModel):
    candidate_id: int = Field(..., gt=0)
    job_id: int = Field(..., gt=0)
    include_answer_hints: bool = True


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=2000)
    job_id: int | None = None


class StageUpdateRequest(BaseModel):
    pipeline_stage: Literal["Applied", "Screened", "Interview", "Offer", "Hired", "Rejected"]


class JobStatusUpdateRequest(BaseModel):
    status: Literal["draft", "open", "closed", "archived"]


@asynccontextmanager
async def lifespan(application: FastAPI):
    startup()
    yield


app = FastAPI(title=f"{APP_NAME} API", version=SERVICE_VERSION, lifespan=lifespan)
app.add_middleware(BodyLimitMiddleware, max_bytes=MAX_BULK_BYTES + 1024 * 1024)
app.include_router(auth_router)
origins = [item.strip() for item in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in origins if origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def platform_middleware(request: Request, call_next):
    supplied_id = request.headers.get("x-request-id", "")
    request_id = supplied_id if re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", supplied_id) else str(uuid.uuid4())
    token = REQUEST_ID_CONTEXT.set(request_id)
    start = time.perf_counter()
    try:
        retry_after = await run_in_threadpool(check_rate_limit, request)
        if retry_after is not None:
            latency = (time.perf_counter() - start) * 1000
            record_http_metric(request, 429, latency)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "request_id": request_id, "retry_after_seconds": retry_after},
                headers={"X-Request-ID": request_id, "Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        latency = (time.perf_counter() - start) * 1000
        record_http_metric(request, response.status_code, latency)
        logger.info("http_request", extra={"context": {
            "request_id": request_id,
            "user_id": getattr(request.state, "user_id", None),
            "role": getattr(request.state, "role", None),
            "route": request.url.path,
            "latency_ms": round(latency, 2),
            "status": response.status_code,
        }})
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = str(round(latency, 2))
        return response
    except Exception:
        latency = (time.perf_counter() - start) * 1000
        record_http_metric(request, 500, latency)
        logger.error("http_request_failed", extra={"context": {"request_id": request_id, "route": request.url.path, "status": 500}})
        return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred", "request_id": request_id}, headers={"X-Request-ID": request_id})
    finally:
        REQUEST_ID_CONTEXT.reset(token)


def startup() -> None:
    validate_runtime_config()
    init_db()


def validate_runtime_config() -> None:
    if APP_ENV not in {"dev", "development", "test", "local"} and (
        len(JWT_SECRET_KEY) < 32
        or JWT_SECRET_KEY.lower() in {"replace-with-a-long-random-secret-before-production", "change-me", "secret"}
    ):
        raise RuntimeError("JWT_SECRET_KEY must be a non-placeholder value of at least 32 characters outside development")


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    return open_database(DB_PATH, SQLITE_JOURNAL_MODE)


def init_db() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS candidates (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              email TEXT,
              phone TEXT,
              links_json TEXT NOT NULL,
              education_json TEXT NOT NULL,
              skills_json TEXT NOT NULL,
              projects_json TEXT NOT NULL,
              experience_json TEXT NOT NULL,
              certifications_json TEXT NOT NULL,
              resume_text TEXT NOT NULL,
              resume_file_path TEXT,
              owner_user_id INTEGER,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              company TEXT,
              description TEXT NOT NULL,
              required_skills_json TEXT NOT NULL,
              responsibilities_json TEXT NOT NULL,
              tools_json TEXT NOT NULL,
              skill_weightage_json TEXT NOT NULL,
              level TEXT NOT NULL,
              domain TEXT NOT NULL,
              jd_quality_score REAL NOT NULL,
              status TEXT NOT NULL DEFAULT 'open',
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS match_results (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              candidate_id INTEGER NOT NULL,
              job_id INTEGER NOT NULL,
              semantic_score REAL NOT NULL,
              skill_score REAL NOT NULL,
              project_score REAL NOT NULL,
              experience_score REAL NOT NULL,
              keyword_score REAL NOT NULL,
              education_score REAL NOT NULL,
              final_score REAL NOT NULL,
              shortlist_probability REAL NOT NULL,
              status TEXT NOT NULL,
              matched_skills_json TEXT NOT NULL,
              partial_skills_json TEXT NOT NULL,
              missing_skills_json TEXT NOT NULL,
              explanation TEXT NOT NULL,
              pipeline_stage TEXT NOT NULL DEFAULT 'Applied',
              created_at TEXT NOT NULL,
              UNIQUE(candidate_id, job_id)
            );

            CREATE TABLE IF NOT EXISTS model_experiments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              model_name TEXT NOT NULL,
              accuracy REAL NOT NULL,
              precision REAL NOT NULL,
              recall REAL NOT NULL,
              f1_score REAL NOT NULL,
              parameters_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              event_id TEXT NOT NULL UNIQUE,
              actor_user_id INTEGER,
              actor_role TEXT,
              action TEXT NOT NULL,
              resource_type TEXT NOT NULL,
              resource_id TEXT,
              metadata_json TEXT NOT NULL,
              request_id TEXT,
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_created
              ON jobs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_match_results_job_score
              ON match_results(job_id, final_score DESC);
            CREATE INDEX IF NOT EXISTS idx_match_results_candidate
              ON match_results(candidate_id);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created
              ON audit_logs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_resource
              ON audit_logs(resource_type, resource_id);
            """
        )
        columns = {row["name"] for row in db.execute("PRAGMA table_info(candidates)").fetchall()}
        if "owner_user_id" not in columns:
            db.execute("ALTER TABLE candidates ADD COLUMN owner_user_id INTEGER")
        db.execute("CREATE INDEX IF NOT EXISTS idx_candidates_owner_created ON candidates(owner_user_id, created_at DESC)")
        job_columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)").fetchall()}
        if "status" not in job_columns:
            db.execute("ALTER TABLE jobs ADD COLUMN status TEXT NOT NULL DEFAULT 'open'")
        match_columns = {row["name"] for row in db.execute("PRAGMA table_info(match_results)").fetchall()}
        if "pipeline_stage" not in match_columns:
            db.execute("ALTER TABLE match_results ADD COLUMN pipeline_stage TEXT NOT NULL DEFAULT 'Applied'")
        db.commit()
    init_auth_db()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "system": APP_NAME,
        "version": SERVICE_VERSION,
        "database": "SQLite",
        "uptime_seconds": uptime_seconds(),
        "request_id": REQUEST_ID_CONTEXT.get(),
    }


@app.get("/api/health")
def api_health() -> dict:
    return health()


@app.get("/ready")
def ready() -> dict:
    return readiness()


@app.get("/api/ready")
def api_ready() -> dict:
    return readiness()


@app.get("/metrics", response_class=Response)
def metrics() -> Response:
    snapshot = http_metrics_snapshot()
    lines = [
        "# HELP vireon_http_requests_total Total HTTP requests.",
        "# TYPE vireon_http_requests_total counter",
        f"vireon_http_requests_total {snapshot['requests']}",
        "# HELP vireon_http_errors_total Total HTTP errors.",
        "# TYPE vireon_http_errors_total counter",
        f"vireon_http_errors_total{{class=\"4xx\"}} {snapshot['client_errors']}",
        f"vireon_http_errors_total{{class=\"5xx\"}} {snapshot['server_errors']}",
        "# HELP vireon_http_latency_ms HTTP latency percentiles in milliseconds.",
        "# TYPE vireon_http_latency_ms gauge",
        f"vireon_http_latency_ms{{quantile=\"0.5\"}} {snapshot['p50_latency_ms']}",
        f"vireon_http_latency_ms{{quantile=\"0.95\"}} {snapshot['p95_latency_ms']}",
    ]
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/api/system/overview")
def system_overview(user: dict = Depends(require_roles("ADMIN", "RECRUITER"))) -> dict:
    with connect() as db:
        counts = table_counts(db)
        audit_count = db.execute("SELECT COUNT(*) AS c FROM audit_logs").fetchone()["c"]
    return {
        "service": {
            "name": APP_NAME,
            "version": SERVICE_VERSION,
            "environment": os.getenv("APP_ENV") or os.getenv("ENVIRONMENT", "local"),
            "uptime_seconds": uptime_seconds(),
            "generated_at": datetime.utcnow().isoformat(),
        },
        "readiness": readiness(),
        "data": {
            **counts,
            "audit_events": audit_count,
            "database_path": str(DB_PATH),
            "resume_storage": str(RESUME_DIR),
        },
        "traffic": http_metrics_snapshot(),
        "cache": cache_snapshot(),
        "topology": architecture_topology(),
        "resilience": {
            "request_tracing": "Every response includes X-Request-ID and latency headers.",
            "backpressure": f"In-process rate limit: {RATE_LIMIT_PER_MINUTE} requests/min/client.",
            "idempotency": "Candidate-job matches use a unique key with upsert semantics.",
            "auditability": "Decision-impacting workflows append immutable audit events.",
        },
        "scale_path": [
            "React/Nginx scales horizontally behind a CDN or load balancer.",
            "FastAPI workers stay stateless; shared cache moves from memory to Redis.",
            "SQLite moves to PostgreSQL with read replicas and managed backups.",
            "Resume uploads move from local disk to object storage with malware scanning.",
            "Ranking and parsing move to a queue-backed worker pool for burst control.",
            "Candidate retrieval moves to pgvector/FAISS with offline embedding refresh.",
        ],
        "slo": {
            "availability_target": "99.9% API availability for recruiter workflows",
            "latency_target": "p95 under 500 ms for cached reads and under 2 s for ranking demos",
            "data_safety": "Bias-safe scoring, audit logs, encrypted secrets, and role-scoped access",
        },
    }


@app.get("/api/system/audit")
def system_audit(limit: int = Query(20, ge=1, le=100), user: dict = Depends(require_roles("ADMIN"))) -> list[dict]:
    with connect() as db:
        rows = db.execute(
            """
            SELECT id, event_id, actor_user_id, actor_role, action, resource_type, resource_id,
                   metadata_json, request_id, created_at
            FROM audit_logs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "event_id": row["event_id"],
            "actor_user_id": row["actor_user_id"],
            "actor_role": row["actor_role"],
            "action": row["action"],
            "resource_type": row["resource_type"],
            "resource_id": row["resource_id"],
            "metadata": load(row["metadata_json"], {}),
            "request_id": row["request_id"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


@app.post("/api/demo/seed")
def seed_demo() -> dict:
    if APP_ENV not in {"local", "dev", "development", "test"}:
        raise HTTPException(status_code=404, detail="Demo seeding is disabled")
    job_text = """
    Artificial Intelligence Intern. QuickHyre AI builds ATS and HRMS automation.
    Design and train AI/ML models, preprocess resume and job data, build NLP matching APIs,
    evaluate model accuracy, document experiments, and create recruiter dashboards.
    Skills: Python, FastAPI, Machine Learning, NLP, Scikit-learn, Pandas, FAISS, Gemini API,
    visualization, model evaluation. Internship duration 6 months with reports.
    """
    resumes = [
        """
        Pruthvi Raj Panduga
        pruthvi@example.com
        Python, FastAPI, NLP, RAG, FAISS, Gemini API, Pandas, Scikit-learn, SQL, Git
        Projects: Built an AI interview coach with Spring Boot, FastAPI AI service, Gemini prompts, dashboard feedback and resume analysis.
        Projects: Created semantic document search using embeddings, vector search and recruiter-style explanations.
        Experience: AI/ML intern projects focused on backend APIs, model evaluation, data preprocessing and documentation.
        Education: IIIT Naya Raipur, Computer Science and AI coursework.
        """,
        """
        Anika Sharma
        anika@example.com
        Python, TensorFlow, Computer Vision, OpenCV, NumPy, visualization
        Projects: Built image classification and OCR workflows with preprocessing, augmentation and confusion matrix reports.
        Experience: Data science internship using notebooks, dashboards and model evaluation.
        Education: B.Tech Computer Science.
        """,
        """
        Rahul Mehta
        rahul@example.com
        Java, MySQL, Docker, REST API, Git, backend systems
        Projects: Employee management system with authentication, CRUD APIs and SQL reporting.
        Experience: Backend developer trainee building production-style APIs.
        Education: Software engineering coursework.
        """,
    ]
    with connect() as db:
        if not db.execute("SELECT id FROM jobs LIMIT 1").fetchone():
            create_job_record(db, parse_jd(job_text, "Artificial Intelligence Intern", "QuickHyre AI"))
        if db.execute("SELECT COUNT(*) AS c FROM candidates").fetchone()["c"] < 3:
            for resume in resumes:
                create_candidate_record(db, parse_resume(resume))
        ensure_experiment(db)
        job_id = db.execute("SELECT id FROM jobs ORDER BY id LIMIT 1").fetchone()["id"]
    seed_demo_users()
    rankings = rank_candidates_internal(job_id)
    audit_log(None, "demo_seeded", "demo_dataset", str(job_id), {"ranked_candidates": len(rankings)})
    return {"message": "Demo data ready", "job_id": job_id, "ranked": rankings}


@app.post("/api/demo/seed-users")
def seed_users() -> dict:
    if APP_ENV not in {"local", "dev", "development", "test"}:
        raise HTTPException(status_code=404, detail="Demo seeding is disabled")
    init_auth_db()
    return seed_demo_users()


@app.post("/api/resumes/text")
def create_candidate(payload: ResumeTextRequest, user: dict = Depends(require_roles("RECRUITER", "CANDIDATE", "ADMIN"))) -> dict:
    parsed = parse_resume(payload.resume_text, payload.name)
    parsed["owner_user_id"] = user["id"] if user["role"] == "CANDIDATE" else None
    with connect() as db:
        candidate = create_candidate_record(db, parsed)
    audit_log(user, "candidate_created", "candidate", candidate["id"], {"source": "text", "skills": candidate["skills"]})
    return candidate


@app.post("/api/resumes/upload")
async def upload_resume(request: Request, user: dict = Depends(require_roles("RECRUITER", "CANDIDATE", "ADMIN"))) -> dict:
    form = await request.form(max_files=1, max_fields=2)
    file = form.get("file")
    if not file or not hasattr(file, "read"):
        raise HTTPException(status_code=400, detail="Multipart field 'file' is required")
    candidate_name = form.get("candidate_name")
    try:
        raw = await file.read(MAX_RESUME_BYTES + 1)
        return await run_in_threadpool(create_uploaded_candidate, raw, getattr(file, "filename", "") or "resume.txt", candidate_name, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()


@app.post("/api/resumes/bulk")
async def bulk_upload_resumes(request: Request, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    form = await request.form(max_files=MAX_BULK_FILES, max_fields=2)
    uploads = form.getlist("files") or form.getlist("file")
    if not uploads or len(uploads) > MAX_BULK_FILES or any(not hasattr(item, "read") for item in uploads):
        await form.close()
        raise HTTPException(status_code=400, detail=f"Provide between 1 and {MAX_BULK_FILES} files")
    results: list[dict] = []
    total_bytes = 0
    for upload in uploads:
        if len(results) >= MAX_BULK_FILES:
            results.append({"filename": "batch", "status": "error", "error": "Maximum expanded file count reached"})
            break
        filename = getattr(upload, "filename", "") or "resume.txt"
        raw = await upload.read(MAX_BULK_BYTES + 1 if filename.lower().endswith(".zip") else MAX_RESUME_BYTES + 1)
        total_bytes += len(raw)
        if total_bytes > MAX_BULK_BYTES:
            await form.close()
            raise HTTPException(status_code=413, detail="Bulk upload exceeds total byte budget")
        if filename.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(BytesIO(raw)) as archive:
                    entries = [info for info in archive.infolist() if not info.is_dir() and not Path(info.filename).name.startswith(".")]
                    if len(entries) + len(results) > MAX_BULK_FILES or sum(info.file_size for info in entries) > MAX_BULK_BYTES:
                        raise ValueError("Archive exceeds file count or decompressed byte budget")
                    for info in entries:
                        try:
                            if info.file_size > MAX_RESUME_BYTES or info.file_size > max(1, info.compress_size) * 100:
                                raise ValueError("Archive entry exceeds size or compression ratio limit")
                            with archive.open(info) as entry:
                                candidate = create_uploaded_candidate(entry.read(MAX_RESUME_BYTES + 1), info.filename, None, user)
                            results.append({"filename": info.filename, "status": "success", "candidate": candidate})
                        except (ValueError, zipfile.BadZipFile, RuntimeError) as exc:
                            results.append({"filename": info.filename, "status": "error", "error": str(exc)})
            except (ValueError, zipfile.BadZipFile) as exc:
                results.append({"filename": filename, "status": "error", "error": str(exc)})
            continue
        try:
            results.append({"filename": filename, "status": "success", "candidate": create_uploaded_candidate(raw, filename, None, user)})
        except ValueError as exc:
            results.append({"filename": filename, "status": "error", "error": str(exc)})
    await form.close()
    return {"results": results, "succeeded": sum(item["status"] == "success" for item in results), "failed": sum(item["status"] == "error" for item in results)}


@app.get("/api/candidates")
def candidates(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), search: str = Query("", max_length=120),
    sort: str = Query("created_at", pattern="^(created_at|name)$"), user: dict = Depends(require_roles("ADMIN", "RECRUITER")),
) -> dict:
    with connect() as db:
        return paginate_rows(db, "candidates", candidate_out, page, page_size, search, sort, ("name", "email", "resume_text"))


@app.get("/api/jobs")
def jobs(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), search: str = Query("", max_length=120),
    sort: str = Query("created_at", pattern="^(created_at|title|status)$"), status: str | None = Query(None, pattern="^(draft|open|closed|archived)$"), user: dict = Depends(get_current_user),
) -> dict:
    with connect() as db:
        if user["role"] == "CANDIDATE":
            status = "open"
        return paginate_rows(db, "jobs", job_out, page, page_size, search, sort, ("title", "company", "description"), {"status": status} if status else None)


@app.post("/api/jobs/create")
def create_job(payload: JobCreateRequest, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    parsed = parse_jd(payload.description, payload.title, payload.company)
    parsed["status"] = payload.status
    with connect() as db:
        job = create_job_record(db, parsed)
    audit_log(user, "job_created", "job", job["id"], {"required_skills": job["required_skills"], "domain": job["domain"]})
    return job


@app.patch("/api/jobs/{job_id}/status")
def update_job_status(job_id: int, payload: JobStatusUpdateRequest, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    with connect() as db:
        job = get_job_row(db, job_id)
        previous_status = job["status"]
        db.execute("UPDATE jobs SET status=? WHERE id=?", (payload.status, job_id))
        db.commit()
    invalidate_cache(f"rankings:{job_id}")
    audit_log(user, "job_status_changed", "job", job_id, {"from": previous_status, "to": payload.status})
    return {"id": job_id, "status": payload.status}


@app.post("/api/match/candidate")
def match_candidate(payload: MatchRequest, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    with connect() as db:
        candidate = get_candidate_row(db, payload.candidate_id)
        job = get_job_row(db, payload.job_id)
        result = compute_and_store_match(db, candidate, job, payload.bias_safe)
    invalidate_cache(f"rankings:{payload.job_id}")
    audit_log(
        user,
        "candidate_matched",
        "match_result",
        result["id"],
        {"candidate_id": payload.candidate_id, "job_id": payload.job_id, "final_score": result["final_score"]},
    )
    return result


@app.get("/api/jobs/{job_id}/rank-candidates")
def rank_candidates(job_id: int, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> list[dict]:
    rows = rank_candidates_internal(job_id)
    audit_log(user, "job_ranked", "job", job_id, {"ranked_candidates": len(rows), "top_score": rows[0]["final_score"] if rows else None})
    return rows


@app.patch("/api/match/{match_id}/stage")
def update_match_stage(match_id: int, payload: StageUpdateRequest, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    with connect() as db:
        match = db.execute("SELECT * FROM match_results WHERE id=?", (match_id,)).fetchone()
        if not match:
            raise HTTPException(status_code=404, detail="Match result not found")
        previous_stage = match["pipeline_stage"]
        db.execute("UPDATE match_results SET pipeline_stage=? WHERE id=?", (payload.pipeline_stage, match_id))
        db.commit()
    invalidate_cache(f"rankings:{match['job_id']}")
    audit_log(user, "match_stage_changed", "match_result", match_id, {"from": previous_stage, "to": payload.pipeline_stage})
    notify("stage_changed", candidate_id=str(match["candidate_id"]), match_id=match_id, from_stage=previous_stage, to_stage=payload.pipeline_stage)
    return {"id": match_id, "candidate_id": match["candidate_id"], "job_id": match["job_id"], "pipeline_stage": payload.pipeline_stage}


def rank_candidates_internal(job_id: int) -> list[dict]:
    cache_key = f"rankings:{job_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    with connect() as db:
        job = get_job_row(db, job_id)
        if job["status"] != "open":
            raise HTTPException(status_code=409, detail="Only open jobs can be ranked")
        rows = []
        for candidate in db.execute("SELECT * FROM candidates").fetchall():
            match = compute_and_store_match(db, candidate, job, True, commit=False)
            rows.append(match)
            if match["status"] == "Strong Match":
                notify("candidate_shortlisted", candidate_id=str(candidate["id"]), job_id=job_id, final_score=match["final_score"])
        ranked = sorted(rows, key=lambda item: item["final_score"], reverse=True)
    cache_set(cache_key, ranked)
    return ranked


@app.get("/api/candidates/{candidate_id}/skill-gap/{job_id}")
def skill_gap(candidate_id: int, job_id: int, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    with connect() as db:
        match = score_match(candidate_out(get_candidate_row(db, candidate_id)), job_out(get_job_row(db, job_id)), True)
    return build_skill_gap_response(match)


def build_skill_gap_response(match: dict) -> dict:
    resources = {
        "Python": ["https://docs.python.org/3/tutorial/"],
        "FastAPI": ["https://fastapi.tiangolo.com/tutorial/"],
        "SQL": ["https://sqlbolt.com/"],
        "Machine Learning": ["https://scikit-learn.org/stable/getting_started.html"],
        "NLP": ["https://huggingface.co/learn/nlp-course/chapter1/1"],
        "Docker": ["https://docs.docker.com/get-started/"],
    }
    roadmap = [
        {"week": i + 1, "skill": skill, "action": f"Build a role-specific artifact proving {skill} and add metrics.", "resources": resources.get(skill, ["https://roadmap.sh/"])}
        for i, skill in enumerate(match["missing_skills"][:6])
    ]
    return {
        "strong_skills": match["matched_skills"],
        "partial_skills": match["partial_skills"],
        "missing_skills": match["missing_skills"],
        "roadmap": roadmap,
    }


@app.post("/api/interview/generate")
def interview(payload: InterviewRequest, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    with connect() as db:
        candidate = candidate_out(get_candidate_row(db, payload.candidate_id))
        job = job_out(get_job_row(db, payload.job_id))
        match = score_match(candidate, job, True)
    questions = []
    for skill in (match["matched_skills"] or job["required_skills"])[:4]:
        questions.append(question("technical", f"How have you used {skill} in a real project?", "Implementation detail, tradeoffs and evidence."))
    for project in candidate["projects"][:2]:
        questions.append(question("project", f"Walk me through this resume evidence: {project[:140]}", "Ownership, tools, dataset/API decisions and outcomes."))
    for skill in match["missing_skills"][:3]:
        questions.append(question("skill_gap", f"If this role needs {skill}, how would you become productive in two weeks?", "Practical learning plan and honest scope."))
    questions.append(question("hr", "Tell me about a time you improved a model, API or workflow after feedback.", "Iteration and communication."))
    if not payload.include_answer_hints:
        for item in questions:
            item.pop("expected_signal", None)
    audit_log(
        user,
        "interview_kit_generated",
        "candidate",
        payload.candidate_id,
        {"job_id": payload.job_id, "questions": min(len(questions), 10), "fit_status": match["status"]},
    )
    notify("interview_kit_generated", candidate_id=str(payload.candidate_id), job_id=payload.job_id)
    return {"candidate_name": candidate["name"], "role": job["title"], "fit_status": match["status"], "questions": questions[:10]}


@app.get("/api/candidate/interview-kit/{job_id}/export")
def candidate_interview_kit_export(job_id: int, format: str = Query("csv", pattern="^(csv|pdf)$"), candidate_id: int | None = None, user: dict = Depends(require_roles("CANDIDATE", "ADMIN"))):
    with connect() as db:
        candidate = candidate_out(get_owned_candidate_row(db, user, candidate_id))
        job = job_out(get_job_row(db, job_id, user))
    match = score_match(candidate, job, True)
    questions = [question("technical", f"How have you used {skill} in a real project?", "Implementation detail, tradeoffs and evidence.") for skill in (match["matched_skills"] or job["required_skills"])[:4]]
    if format == "csv":
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["type", "question", "expected_signal"])
        writer.writeheader()
        writer.writerows(questions)
        return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=interview-kit-{job_id}.csv"})
    return pdf_response(f"Interview kit: {job['title']}", [item["question"] for item in questions], f"interview-kit-{job_id}.pdf")


@app.get("/api/analytics/job/{job_id}")
def analytics(job_id: int, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    rankings = rank_candidates_internal(job_id)
    missing = Counter(skill for row in rankings for skill in row["missing_skills"])
    status = Counter(row["status"] for row in rankings)
    avg = round(sum(row["final_score"] for row in rankings) / max(1, len(rankings)), 1)
    strong = sum(1 for row in rankings if row["status"] == "Strong Match")
    return {
        "job_id": job_id,
        "total_candidates": len(rankings),
        "average_score": avg,
        "shortlist_ratio": round(strong / max(1, len(rankings)) * 100, 1),
        "status_distribution": dict(status),
        "common_missing_skills": [{"skill": skill, "count": count} for skill, count in missing.most_common(8)],
        "top_candidates": rankings[:10],
    }


@app.post("/api/chat/hr")
def hr_chat(payload: ChatRequest, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    with connect() as db:
        docs = []
        for row in db.execute("SELECT * FROM candidates").fetchall():
            candidate = candidate_out(row)
            docs.append(
                {
                    "candidate_id": candidate["id"],
                    "candidate_name": candidate["name"],
                    "text": " ".join(candidate["skills"] + candidate["projects"] + candidate["experience"]) + " " + candidate["resume_text"][:1200],
                }
            )
    ranked = sorted(
        [{**doc, "retrieval_score": round(cosine(payload.question, doc["text"]) * 100, 1)} for doc in docs],
        key=lambda item: item["retrieval_score"],
        reverse=True,
    )[:5]
    names = [item["candidate_name"] for item in ranked[:3] if item["retrieval_score"] > 0]
    audit_log(user, "hr_chat_queried", "candidate_search", None, {"job_id": payload.job_id, "evidence_count": len(ranked)})
    return {
        "question": payload.question,
        "job_id": payload.job_id,
        "answer": "Top grounded matches: " + ", ".join(names) if names else "No matching candidate evidence is available yet.",
        "evidence": ranked,
    }


@app.get("/api/reports/job/{job_id}")
def report(job_id: int, format: str = Query("json", pattern="^(json|csv)$"), user: dict = Depends(require_roles("RECRUITER", "ADMIN"))):
    rows = rank_candidates_internal(job_id)
    audit_log(user, "report_exported", "job", job_id, {"format": format, "rows": len(rows)})
    if format == "json":
        return {"job_id": job_id, "rows": rows}
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["candidate_name", "role", "final_score", "shortlist_probability", "status", "matched_skills", "missing_skills"])
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "candidate_name": csv_cell(row["candidate_name"]),
                "role": csv_cell(row["role"]),
                "final_score": row["final_score"],
                "shortlist_probability": row["shortlist_probability"],
                "status": row["status"],
                "matched_skills": ", ".join(row["matched_skills"]),
                "missing_skills": ", ".join(row["missing_skills"]),
            }
        )
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=vireon-job-{job_id}.csv"})


@app.get("/api/candidate/skill-gap/{job_id}/export")
def candidate_skill_gap_export(job_id: int, format: str = Query("csv", pattern="^(csv|pdf)$"), candidate_id: int | None = None, user: dict = Depends(require_roles("CANDIDATE", "ADMIN"))):
    gap = candidate_skill_gap(job_id, candidate_id, user)
    if format == "csv":
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["week", "skill", "action", "resources"])
        writer.writeheader()
        for item in gap["roadmap"]:
            writer.writerow(item)
        return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=skill-gap-{job_id}.csv"})
    lines = [f"Strong skills: {', '.join(gap['strong_skills'])}", f"Missing skills: {', '.join(gap['missing_skills'])}"]
    lines.extend(f"Week {item['week']}: {item['skill']} - {item['action']}" for item in gap["roadmap"])
    return pdf_response(f"Skill gap roadmap for job {job_id}", lines, f"skill-gap-{job_id}.pdf")


@app.get("/api/model/experiment")
def model_experiment(user: dict = Depends(require_roles("ADMIN", "RECRUITER"))) -> dict:
    with connect() as db:
        row = db.execute("SELECT * FROM model_experiments ORDER BY created_at DESC, id DESC LIMIT 1").fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No model evaluation has been run")
    parameters = load(row["parameters_json"], {})
    return {
        "model_name": row["model_name"],
        "accuracy": row["accuracy"],
        "precision": row["precision"],
        "recall": row["recall"],
        "f1_score": row["f1_score"],
        "parameters": parameters,
        "evaluation_status": "synthetic_labels" if parameters.get("label_rule") else "unevaluated_fixture",
        "created_at": row["created_at"],
        "features": ["semantic_score", "skill_score", "project_score", "experience_score", "keyword_score", "education_score", "final_score"],
    }


@app.get("/api/admin/users")
def admin_users(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), search: str = Query("", max_length=120),
    sort: str = Query("created_at", pattern="^(created_at|name|email|role)$"), user: dict = Depends(require_roles("ADMIN")),
) -> dict:
    return list_users(page, page_size, search, sort)


@app.get("/api/admin/candidates")
def admin_candidates(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), search: str = Query("", max_length=120),
    sort: str = Query("created_at", pattern="^(created_at|name)$"), user: dict = Depends(require_roles("ADMIN")),
) -> dict:
    with connect() as db:
        return paginate_rows(db, "candidates", candidate_out, page, page_size, search, sort, ("name", "email", "resume_text"))


@app.get("/api/admin/jobs")
def admin_jobs(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), search: str = Query("", max_length=120),
    sort: str = Query("created_at", pattern="^(created_at|title|status)$"), status: str | None = Query(None, pattern="^(draft|open|closed|archived)$"), user: dict = Depends(require_roles("ADMIN")),
) -> dict:
    with connect() as db:
        return paginate_rows(db, "jobs", job_out, page, page_size, search, sort, ("title", "company", "description"), {"status": status} if status else None)


@app.get("/api/admin/analytics")
def admin_analytics(user: dict = Depends(require_roles("ADMIN"))) -> dict:
    with connect() as db:
        jobs_rows = db.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        candidate_count = db.execute("SELECT COUNT(*) AS c FROM candidates").fetchone()["c"]
        match_count = db.execute("SELECT COUNT(*) AS c FROM match_results").fetchone()["c"]
    job_summaries = []
    for row in jobs_rows[:10]:
        rankings = rank_candidates_internal(row["id"])
        avg = round(sum(item["final_score"] for item in rankings) / max(1, len(rankings)), 1)
        job_summaries.append({"job_id": row["id"], "title": row["title"], "candidates": len(rankings), "average_score": avg})
    return {"users": list_users(page_size=1)["total"], "candidates": candidate_count, "jobs": len(jobs_rows), "matches": match_count, "job_summaries": job_summaries}


@app.get("/api/admin/platform-data")
def admin_platform_data(user: dict = Depends(require_roles("ADMIN"))) -> dict:
    with connect() as db:
        return {
            "database": str(DB_PATH),
            "users": db.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"],
            "candidates": db.execute("SELECT COUNT(*) AS c FROM candidates").fetchone()["c"],
            "jobs": db.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"],
            "matches": db.execute("SELECT COUNT(*) AS c FROM match_results").fetchone()["c"],
            "audit_events": db.execute("SELECT COUNT(*) AS c FROM audit_logs").fetchone()["c"],
            "cache": cache_snapshot(),
            "traffic": http_metrics_snapshot(),
        }


@app.get("/api/recruiter/dashboard")
def recruiter_dashboard(user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    with connect() as db:
        candidate_count = db.execute("SELECT COUNT(*) AS c FROM candidates").fetchone()["c"]
        jobs_rows = db.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    latest_job = job_out(jobs_rows[0]) if jobs_rows else None
    return {"recruiter": user, "candidate_count": candidate_count, "job_count": len(jobs_rows), "latest_job": latest_job}


@app.get("/api/recruiter/jobs")
def recruiter_jobs(user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> list[dict]:
    with connect() as db:
        return [job_out(row) for row in db.execute("SELECT * FROM jobs ORDER BY created_at DESC")]


@app.get("/api/recruiter/candidates")
def recruiter_candidates(user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> list[dict]:
    with connect() as db:
        return [candidate_out(row) for row in db.execute("SELECT * FROM candidates ORDER BY created_at DESC")]


@app.get("/api/recruiter/analytics/{job_id}")
def recruiter_analytics(job_id: int, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    return analytics(job_id, user)


@app.get("/api/candidate/profile")
def candidate_profile(user: dict = Depends(require_roles("CANDIDATE", "ADMIN"))) -> dict:
    with connect() as db:
        rows = db.execute("SELECT * FROM candidates WHERE owner_user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall()
    return {"user": user, "resumes": [candidate_out(row) for row in rows]}


@app.get("/api/candidate/ats-score")
def candidate_ats_score(
    job_id: int,
    candidate_id: int | None = None,
    user: dict = Depends(require_roles("CANDIDATE", "ADMIN")),
) -> dict:
    with connect() as db:
        candidate = get_owned_candidate_row(db, user, candidate_id)
        job = get_job_row(db, job_id, user)
        match = score_match(candidate_out(candidate), job_out(job), True)
    return {"candidate": candidate_out(candidate), "job": job_out(job), "ats_score": match["final_score"], "status": match["status"], "match": match}


@app.get("/api/candidate/skill-gap/{job_id}")
def candidate_skill_gap(job_id: int, candidate_id: int | None = None, user: dict = Depends(require_roles("CANDIDATE", "ADMIN"))) -> dict:
    with connect() as db:
        candidate = get_owned_candidate_row(db, user, candidate_id)
        job = get_job_row(db, job_id, user)
        match = score_match(candidate_out(candidate), job_out(job), True)
    return build_skill_gap_response(match)


@app.get("/api/candidate/resume-improvement/{job_id}")
def candidate_resume_improvement(job_id: int, candidate_id: int | None = None, user: dict = Depends(require_roles("CANDIDATE", "ADMIN"))) -> dict:
    gap = candidate_skill_gap(job_id, candidate_id, user)
    suggestions = [f"Add measurable project evidence for {skill}." for skill in gap["missing_skills"][:6]]
    if not suggestions:
        suggestions = ["Your resume aligns well. Add more metrics, links, and concrete outcomes to strengthen recruiter trust."]
    return {"missing_skills": gap["missing_skills"], "suggestions": suggestions, "roadmap": gap["roadmap"]}


def check_rate_limit(request: Request) -> int | None:
    if RATE_LIMIT_PER_MINUTE <= 0:
        return None
    path = request.url.path
    if path in {"/health", "/api/health", "/ready", "/api/ready"}:
        return None
    if path.startswith(("/docs", "/openapi", "/redoc")):
        return None
    now = time.time()
    client = request.client.host if request.client else "local"
    if REDIS_URL:
        try:
            global REDIS_CLIENT
            if REDIS_CLIENT is None:
                import redis
                REDIS_CLIENT = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=0.2)
            bucket_key = f"vireon:rate:{client}:{int(now // 60)}"
            count = int(REDIS_CLIENT.incr(bucket_key))
            if count == 1:
                REDIS_CLIENT.expire(bucket_key, 61)
            if count > RATE_LIMIT_PER_MINUTE:
                return max(1, int(60 - (now % 60)))
            return None
        except Exception:
            REDIS_CLIENT = None
    with RUNTIME_LOCK:
        bucket = RATE_BUCKETS.setdefault(client, deque())
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_PER_MINUTE:
            return max(1, int(60 - (now - bucket[0])))
        bucket.append(now)
    return None


def record_http_metric(request: Request, status_code: int, latency_ms: float) -> None:
    route = request.scope.get("route")
    path_key = f"{request.method} {getattr(route, 'path', 'unmatched')} {status_code // 100}xx"
    with RUNTIME_LOCK:
        HTTP_METRICS["requests"] += 1
        if status_code >= 500:
            HTTP_METRICS["server_errors"] += 1
        elif status_code >= 400:
            HTTP_METRICS["client_errors"] += 1
        PATH_METRICS[path_key] += 1
        LATENCY_MS.append(round(latency_ms, 2))


def uptime_seconds() -> int:
    return int((datetime.utcnow() - STARTED_AT).total_seconds())


def readiness() -> dict:
    checks = []
    try:
        with connect() as db:
            db.execute("SELECT 1").fetchone()
        checks.append({"name": "sqlite", "status": "ok"})
    except (sqlite3.Error, OSError):
        checks.append({"name": "sqlite", "status": "fail", "detail": "Database unavailable"})
    checks.append({"name": "data_dir", "status": "ok" if DATA_DIR.exists() else "fail"})
    checks.append({"name": "resume_dir", "status": "ok" if RESUME_DIR.exists() else "fail"})
    status_value = "ready" if all(item["status"] == "ok" for item in checks) else "not_ready"
    payload = {"status": status_value, "checks": checks, "generated_at": datetime.utcnow().isoformat()}
    if status_value != "ready":
        raise HTTPException(status_code=503, detail=payload)
    return payload


def table_counts(db: sqlite3.Connection) -> dict:
    return {
        "users": db.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"],
        "candidates": db.execute("SELECT COUNT(*) AS c FROM candidates").fetchone()["c"],
        "jobs": db.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"],
        "matches": db.execute("SELECT COUNT(*) AS c FROM match_results").fetchone()["c"],
        "model_experiments": db.execute("SELECT COUNT(*) AS c FROM model_experiments").fetchone()["c"],
    }


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(percentile_value / 100 * len(ordered)) - 1))
    return round(ordered[index], 2)


def http_metrics_snapshot() -> dict:
    with RUNTIME_LOCK:
        latencies = list(LATENCY_MS)
        requests = int(HTTP_METRICS["requests"])
        server_errors = int(HTTP_METRICS["server_errors"])
        client_errors = int(HTTP_METRICS["client_errors"])
        top_paths = [{"route": route, "count": count} for route, count in PATH_METRICS.most_common(8)]
    return {
        "requests": requests,
        "server_errors": server_errors,
        "client_errors": client_errors,
        "error_rate_percent": round(server_errors / max(1, requests) * 100, 2),
        "p50_latency_ms": percentile(latencies, 50),
        "p95_latency_ms": percentile(latencies, 95),
        "top_paths": top_paths,
    }


def cache_get(key: str) -> Any | None:
    if CACHE_TTL_SECONDS <= 0:
        with RUNTIME_LOCK:
            CACHE_STATS["misses"] += 1
        return None
    now = time.time()
    with RUNTIME_LOCK:
        entry = CACHE.get(key)
        if not entry:
            CACHE_STATS["misses"] += 1
            return None
        if entry["expires_at"] < now:
            CACHE.pop(key, None)
            CACHE_STATS["misses"] += 1
            return None
        CACHE_STATS["hits"] += 1
        return copy.deepcopy(entry["value"])


def cache_set(key: str, value: Any) -> None:
    if CACHE_TTL_SECONDS <= 0:
        return
    with RUNTIME_LOCK:
        CACHE[key] = {"expires_at": time.time() + CACHE_TTL_SECONDS, "value": copy.deepcopy(value)}
        CACHE_STATS["sets"] += 1


def invalidate_cache(prefix: str | None = None) -> int:
    with RUNTIME_LOCK:
        keys = [key for key in CACHE if prefix is None or key.startswith(prefix)]
        for key in keys:
            CACHE.pop(key, None)
        CACHE_STATS["invalidations"] += len(keys)
    return len(keys)


def cache_snapshot() -> dict:
    with RUNTIME_LOCK:
        return {
            "ttl_seconds": CACHE_TTL_SECONDS,
            "entries": len(CACHE),
            "stats": dict(CACHE_STATS),
            "keys": sorted(CACHE.keys())[:10],
        }


def audit_log(user: dict | None, action: str, resource_type: str, resource_id: Any = None, metadata: dict | None = None) -> None:
    with connect() as db:
        db.execute(
            """
            INSERT INTO audit_logs (
              event_id, actor_user_id, actor_role, action, resource_type, resource_id,
              metadata_json, request_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                user.get("id") if user else None,
                user.get("role") if user else None,
                action,
                resource_type,
                str(resource_id) if resource_id is not None else None,
                dump(metadata or {}),
                REQUEST_ID_CONTEXT.get(),
                datetime.utcnow().isoformat(),
            ),
        )
        db.commit()


def architecture_topology() -> list[dict]:
    return [
        {
            "name": "React recruiter console",
            "type": "frontend",
            "responsibility": "Role-specific workflows, uploads, rankings, analytics, and candidate review.",
            "scale_unit": "Static assets behind CDN or Nginx replicas",
        },
        {
            "name": "FastAPI gateway",
            "type": "api",
            "responsibility": "JWT auth, RBAC, request tracing, validation, orchestration, and reporting.",
            "scale_unit": "Stateless Uvicorn workers",
        },
        {
            "name": "Matching engine",
            "type": "domain service",
            "responsibility": "Bias-safe parsing, feature scoring, shortlist calibration, and explanations.",
            "scale_unit": "Async workers for production ranking bursts",
        },
        {
            "name": "Operational cache",
            "type": "cache",
            "responsibility": "TTL cache for expensive ranking reads and repeated analytics calls.",
            "scale_unit": "Redis cluster in production",
        },
        {
            "name": "SQLite data store",
            "type": "database",
            "responsibility": "Users, candidates, jobs, match results, model experiments, and audit logs.",
            "scale_unit": "PostgreSQL primary plus read replicas in production",
        },
        {
            "name": "Resume object store",
            "type": "blob storage",
            "responsibility": "Uploaded resumes with size limits and metadata stored in the database.",
            "scale_unit": "S3-compatible object storage in production",
        },
    ]


def extract_file_text(raw: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        try:
            import fitz

            with fitz.open(stream=raw, filetype="pdf") as doc:
                return "\n".join(page.get_text() for page in doc)
        except Exception as exc:
            raise ValueError("Could not read PDF; provide an unencrypted document with selectable text") from exc
    if suffix == ".docx":
        try:
            from docx import Document
            from io import BytesIO

            with zipfile.ZipFile(BytesIO(raw)) as archive:
                if sum(info.file_size for info in archive.infolist()) > MAX_BULK_BYTES:
                    raise ValueError("DOCX exceeds decompressed byte budget")
            return "\n".join(p.text for p in Document(BytesIO(raw)).paragraphs)
        except Exception as exc:
            raise ValueError("Could not read DOCX; provide a valid document") from exc
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def safe_resume_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFC", Path(filename).name)
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", normalized)[:160] or "resume.txt"


def validate_resume_bytes(raw: bytes, filename: str) -> None:
    if len(raw) > MAX_RESUME_BYTES:
        raise ValueError(f"Resume upload exceeds {MAX_RESUME_BYTES // (1024 * 1024)} MB limit")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".txt", ".pdf", ".docx"}:
        raise ValueError("Only TXT, PDF, and DOCX resumes are supported")
    if raw.startswith(b"MZ") or raw.startswith(b"#!"):
        raise ValueError("Executable or script content is not a valid resume")
    signatures = {".pdf": raw.startswith(b"%PDF"), ".docx": raw.startswith(b"PK"), ".txt": True}
    if not signatures[suffix]:
        raise ValueError("File content does not match its declared resume type")


def create_uploaded_candidate(raw: bytes, filename: str, candidate_name: str | None, user: dict) -> dict:
    validate_resume_bytes(raw, filename)
    text = extract_file_text(raw, filename)
    if len(text.strip()) < 20 or len(text) > 100000:
        raise ValueError("Resume must contain between 20 and 100000 characters of readable text")
    if candidate_name is not None and (not isinstance(candidate_name, str) or len(candidate_name) > 120):
        raise ValueError("Candidate name must be text of at most 120 characters")
    safe_name = safe_resume_filename(filename)
    path = RESUME_DIR / f"{uuid.uuid4().hex}_{safe_name}"
    path.write_bytes(raw)
    parsed = parse_resume(text, candidate_name)
    parsed["resume_file_path"] = str(path)
    parsed["owner_user_id"] = user["id"] if user["role"] == "CANDIDATE" else None
    try:
        with connect() as db:
            candidate = create_candidate_record(db, parsed)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    audit_log(user, "candidate_created", "candidate", candidate["id"], {"source": "upload", "filename": filename, "bytes": len(raw)})
    return candidate


def csv_cell(value: str) -> str:
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else value


def pdf_response(title: str, lines: list[str], filename: str) -> Response:
    try:
        import fitz
        document = fitz.open()
        page = document.new_page()
        y = 50
        page.insert_text((50, y), title, fontsize=16)
        for line in lines:
            y += 22
            if y > 760:
                page = document.new_page()
                y = 50
            page.insert_text((50, y), line[:150], fontsize=10)
        content = document.tobytes()
        document.close()
        return Response(content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF export unavailable: {exc}") from exc


def parse_resume(text: str, name: str | None = None) -> dict:
    clean = normalize(text.replace("\r", "\n"))
    lines = [line.strip(" -\t") for line in clean.splitlines() if line.strip()]
    email = first(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", clean))
    phone = first(re.findall(r"(?:\+?\d[\s-]?){9,15}", clean))
    links = sorted(set(re.findall(r"https?://[^\s)]+|(?:github|linkedin)\.com/[^\s)]+", clean, re.I)))
    return {
        "name": name or infer_name(lines, email),
        "email": email,
        "phone": phone,
        "links": links,
        "skills": extract_skills(clean),
        "projects": section_items(lines, ["project", "portfolio"]),
        "experience": section_items(lines, ["experience", "internship", "work"]),
        "education": section_items(lines, ["education", "degree", "university", "college"]),
        "certifications": section_items(lines, ["certification", "course", "credential"]),
        "resume_text": clean,
        "resume_file_path": None,
    }


def parse_jd(description: str, title: str | None = None, company: str | None = None) -> dict:
    clean = normalize(description)
    skills = extract_skills(clean)
    responsibilities = [
        normalize(line).strip("-*0123456789. ")
        for line in description.splitlines()
        if len(normalize(line)) > 18 and re.search(r"\b(build|design|train|evaluate|develop|analyze|document|deploy|implement|optimize|create)\b", line, re.I)
    ][:10]
    counts = Counter({skill: max(1, sum(clean.lower().count(alias) for alias in aliases)) for skill, aliases in SKILLS.items() if skill in skills})
    total = sum(counts.values()) or 1
    return {
        "title": title or infer_title(description),
        "company": company,
        "description": clean,
        "required_skills": skills,
        "responsibilities": responsibilities,
        "tools": [skill for skill in skills if skill in {"FastAPI", "FAISS", "Gemini API", "Pandas", "NumPy", "Scikit-learn", "PyTorch", "TensorFlow", "Docker", "SQL"}],
        "skill_weightage": {skill: round(count / total * 100, 1) for skill, count in counts.items()},
        "level": level(clean),
        "domain": "HR Tech" if re.search(r"\b(ats|recruit|hiring|hrms)\b", clean, re.I) else "AI Platform",
        "jd_quality_score": quality_score(clean, skills, responsibilities),
    }


def score_match(candidate: dict, job: dict, bias_safe: bool = True) -> dict:
    resume_text = remove_bias(candidate["resume_text"]) if bias_safe else candidate["resume_text"]
    required = set(job["required_skills"])
    candidate_skills = set(candidate["skills"]) | set(extract_skills(resume_text))
    matched = sorted(candidate_skills & required)
    missing = sorted(required - candidate_skills)
    partial = sorted(skill for skill in missing if any(word.lower() in resume_text.lower() for word in skill.split() if len(word) > 2))
    missing = [skill for skill in missing if skill not in partial]

    semantic = semantic_similarity(resume_text, job["description"], cosine) * 100
    skill_score = len(matched) / max(1, len(required)) * 100
    project_score = min(100, 20 + sum(12 for key in ["ai", "ml", "nlp", "rag", "resume", "ats", "backend", "api", "dataset", "model"] if key in " ".join(candidate["projects"]).lower()))
    experience_score = min(100, 25 + sum(10 for key in ["intern", "backend", "api", "model", "data", "automation"] if key in " ".join(candidate["experience"]).lower()))
    keyword_pool = set(job["required_skills"]) | {word for item in job["responsibilities"] for word in item.split() if len(word) > 6}
    keyword_score = sum(1 for word in keyword_pool if word.lower() in resume_text.lower()) / max(1, len(keyword_pool)) * 100
    education_score = min(100, 20 + sum(15 for key in ["computer", "data", "ai", "machine", "software", "certification", "course"] if key in " ".join(candidate["education"] + candidate["certifications"]).lower()))
    final = 0.35 * semantic + 0.25 * skill_score + 0.15 * project_score + 0.10 * experience_score + 0.10 * keyword_score + 0.05 * education_score
    status = "Strong Match" if final >= 75 else "Maybe" if final >= 58 else "Reject"
    probability = 1 / (1 + math.exp(-0.09 * (final - 58))) * 100
    explanation = (
        f"{candidate['name']} is a {status.lower()} for {job['title']}. Strong evidence: "
        f"{', '.join(matched[:5]) or 'limited direct skill evidence'}. Main gaps: {', '.join(missing[:4]) or 'none obvious'}."
    )
    return {
        "semantic_score": round(semantic, 1),
        "skill_score": round(skill_score, 1),
        "project_score": round(project_score, 1),
        "experience_score": round(experience_score, 1),
        "keyword_score": round(keyword_score, 1),
        "education_score": round(education_score, 1),
        "final_score": round(final, 1),
        "shortlist_probability": round(probability, 1),
        "status": status,
        "matched_skills": matched,
        "partial_skills": partial,
        "missing_skills": missing,
        "explanation": explanation,
    }


def compute_and_store_match(db: sqlite3.Connection, candidate_row: sqlite3.Row, job_row: sqlite3.Row, bias_safe: bool, commit: bool = True) -> dict:
    candidate = candidate_out(candidate_row)
    job = job_out(job_row)
    result = score_match(candidate, job, bias_safe)
    now = datetime.utcnow().isoformat()
    db.execute(
        """
        INSERT INTO match_results (
          candidate_id, job_id, semantic_score, skill_score, project_score, experience_score, keyword_score,
          education_score, final_score, shortlist_probability, status, matched_skills_json, partial_skills_json,
          missing_skills_json, explanation, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(candidate_id, job_id) DO UPDATE SET
          semantic_score=excluded.semantic_score, skill_score=excluded.skill_score,
          project_score=excluded.project_score, experience_score=excluded.experience_score,
          keyword_score=excluded.keyword_score, education_score=excluded.education_score,
          final_score=excluded.final_score, shortlist_probability=excluded.shortlist_probability,
          status=excluded.status, matched_skills_json=excluded.matched_skills_json,
          partial_skills_json=excluded.partial_skills_json, missing_skills_json=excluded.missing_skills_json,
          explanation=excluded.explanation, created_at=excluded.created_at
        """,
        (
            candidate["id"],
            job["id"],
            result["semantic_score"],
            result["skill_score"],
            result["project_score"],
            result["experience_score"],
            result["keyword_score"],
            result["education_score"],
            result["final_score"],
            result["shortlist_probability"],
            result["status"],
            dump(result["matched_skills"]),
            dump(result["partial_skills"]),
            dump(result["missing_skills"]),
            result["explanation"],
            now,
        ),
    )
    if commit:
        db.commit()
    match_id = db.execute("SELECT id FROM match_results WHERE candidate_id=? AND job_id=?", (candidate["id"], job["id"])).fetchone()["id"]
    stored = db.execute("SELECT pipeline_stage FROM match_results WHERE id=?", (match_id,)).fetchone()
    return {"id": match_id, "candidate_id": candidate["id"], "job_id": job["id"], "candidate_name": candidate["name"], "role": job["title"], "pipeline_stage": stored["pipeline_stage"], **result, "created_at": now}


def create_candidate_record(db: sqlite3.Connection, parsed: dict) -> dict:
    cur = db.execute(
        """
        INSERT INTO candidates (
          name, email, phone, links_json, education_json, skills_json, projects_json, experience_json,
          certifications_json, resume_text, resume_file_path, owner_user_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            parsed["name"],
            parsed["email"],
            parsed["phone"],
            dump(parsed["links"]),
            dump(parsed["education"]),
            dump(parsed["skills"]),
            dump(parsed["projects"]),
            dump(parsed["experience"]),
            dump(parsed["certifications"]),
            parsed["resume_text"],
            parsed.get("resume_file_path"),
            parsed.get("owner_user_id"),
            datetime.utcnow().isoformat(),
        ),
    )
    db.commit()
    invalidate_cache("rankings:")
    return candidate_out(db.execute("SELECT * FROM candidates WHERE id=?", (cur.lastrowid,)).fetchone())


def create_job_record(db: sqlite3.Connection, parsed: dict) -> dict:
    cur = db.execute(
        """
        INSERT INTO jobs (
          title, company, description, required_skills_json, responsibilities_json, tools_json,
                    skill_weightage_json, level, domain, jd_quality_score, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            parsed["title"],
            parsed["company"],
            parsed["description"],
            dump(parsed["required_skills"]),
            dump(parsed["responsibilities"]),
            dump(parsed["tools"]),
            dump(parsed["skill_weightage"]),
            parsed["level"],
            parsed["domain"],
            parsed["jd_quality_score"],
            parsed.get("status", "open"),
            datetime.utcnow().isoformat(),
        ),
    )
    db.commit()
    invalidate_cache("rankings:")
    return job_out(db.execute("SELECT * FROM jobs WHERE id=?", (cur.lastrowid,)).fetchone())


def ensure_experiment(db: sqlite3.Connection) -> None:
    if db.execute("SELECT id FROM model_experiments LIMIT 1").fetchone():
        return
    db.execute(
        "INSERT INTO model_experiments (model_name, accuracy, precision, recall, f1_score, parameters_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("DemoFixtureUnvalidated", 0, 0, 0, 0, dump({"source": "demo_fixture", "evaluated": False}), datetime.utcnow().isoformat()),
    )
    db.commit()


def candidate_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "links": load(row["links_json"], []),
        "education": load(row["education_json"], []),
        "skills": load(row["skills_json"], []),
        "projects": load(row["projects_json"], []),
        "experience": load(row["experience_json"], []),
        "certifications": load(row["certifications_json"], []),
        "resume_text": row["resume_text"],
        "resume_file_path": row["resume_file_path"],
        "owner_user_id": row["owner_user_id"] if "owner_user_id" in row.keys() else None,
        "created_at": row["created_at"],
    }


def job_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "company": row["company"],
        "description": row["description"],
        "required_skills": load(row["required_skills_json"], []),
        "responsibilities": load(row["responsibilities_json"], []),
        "tools": load(row["tools_json"], []),
        "skill_weightage": load(row["skill_weightage_json"], {}),
        "level": row["level"],
        "domain": row["domain"],
        "jd_quality_score": row["jd_quality_score"],
        "status": row["status"] if "status" in row.keys() else "open",
        "created_at": row["created_at"],
    }


def get_candidate_row(db: sqlite3.Connection, candidate_id: int) -> sqlite3.Row:
    row = db.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return row


def get_job_row(db: sqlite3.Connection, job_id: int, user: dict | None = None) -> sqlite3.Row:
    row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row or (user and user["role"] == "CANDIDATE" and row["status"] != "open"):
        raise HTTPException(status_code=404, detail="Job not found")
    return row


def paginate_rows(db: sqlite3.Connection, table: str, serializer: Any, page: int, page_size: int, search: str, sort: str, search_columns: tuple[str, ...], filters: dict[str, str] | None = None) -> dict:
    if table not in {"candidates", "jobs"}:
        raise ValueError("Unsupported pagination table")
    clauses: list[str] = []
    params: list[Any] = []
    if search:
        clauses.append("(" + " OR ".join(f"{column} LIKE ?" for column in search_columns) + ")")
        params.extend([f"%{search}%"] * len(search_columns))
    for column, value in (filters or {}).items():
        clauses.append(f"{column}=?")
        params.append(value)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    order_column = sort if sort in {"created_at", "name", "title", "status"} else "created_at"
    total = db.execute(f"SELECT COUNT(*) AS count FROM {table}{where}", params).fetchone()["count"]
    rows = db.execute(f"SELECT * FROM {table}{where} ORDER BY {order_column} DESC LIMIT ? OFFSET ?", [*params, page_size, (page - 1) * page_size]).fetchall()
    return {"items": [serializer(row) for row in rows], "total": total, "page": page, "page_size": page_size}


def get_owned_candidate_row(db: sqlite3.Connection, user: dict, candidate_id: int | None = None) -> sqlite3.Row:
    if user["role"] == "ADMIN" and candidate_id:
        return get_candidate_row(db, candidate_id)
    if candidate_id:
        row = db.execute("SELECT * FROM candidates WHERE id=? AND owner_user_id=?", (candidate_id, user["id"])).fetchone()
    else:
        row = db.execute("SELECT * FROM candidates WHERE owner_user_id=? ORDER BY created_at DESC LIMIT 1", (user["id"],)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Upload your resume before requesting candidate insights")
    return row


def question(kind: str, prompt: str, signal: str) -> dict:
    return {"type": kind, "question": prompt, "expected_signal": signal}


def extract_skills(text: str) -> list[str]:
    lower = f" {normalize(text).lower()} "
    found = []
    for skill, aliases in SKILLS.items():
        if any(re.search(r"(?<![a-z0-9+#.])" + re.escape(alias) + r"(?![a-z0-9+#.])", lower) for alias in aliases):
            found.append(skill)
    return sorted(set(found))


def cosine(left: str, right: str) -> float:
    a = Counter(tokens(left))
    b = Counter(tokens(right))
    if not a or not b:
        return 0.0
    dot = sum(a[key] * b[key] for key in set(a) & set(b))
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", (text or "").lower())


def normalize(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text or "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_bias(text: str) -> str:
    return re.sub(r"\b(age|gender|marital|religion|caste|photo|address|nationality)\b", " ", text or "", flags=re.I)


def infer_name(lines: list[str], email: str | None) -> str:
    for line in lines[:8]:
        low = line.lower()
        if (email and email.lower() in low) or "linkedin" in low or "github" in low or "resume" in low:
            continue
        if 1 < len(line.split()) <= 5 and not any(ch.isdigit() for ch in line):
            return normalize(line)
    return "Candidate"


def infer_title(description: str) -> str:
    for line in description.splitlines()[:8]:
        clean = normalize(line).strip(":-")
        if 3 <= len(clean) <= 80 and re.search(r"\b(intern|engineer|developer|analyst|scientist|manager)\b", clean, re.I):
            return clean
    return "AI Hiring Role"


def section_items(lines: list[str], markers: list[str]) -> list[str]:
    items = []
    for line in lines:
        low = line.lower()
        if any(marker in low for marker in markers) and len(line) > 18:
            items.append(normalize(line))
    return items[:12]


def quality_score(text: str, skills: list[str], responsibilities: list[str]) -> float:
    checks = [
        bool(skills),
        len(skills) >= 4,
        bool(responsibilities),
        len(text.split()) >= 60,
        bool(re.search(r"\b(duration|month|stipend|salary|remote|onsite|hybrid)\b", text, re.I)),
        bool(re.search(r"\b(evaluate|metric|metrics|accuracy|deliverable|deliverables|report|reports|documentation)\b", text, re.I)),
    ]
    return round(sum(checks) / len(checks) * 100, 1)


def level(text: str) -> str:
    low = text.lower()
    if re.search(r"\b(intern|trainee|fresher|entry)\b", low):
        return "Internship"
    if re.search(r"\b(senior|lead|architect|5\+)\b", low):
        return "Advanced"
    if re.search(r"\b(2\+|3\+|intermediate)\b", low):
        return "Intermediate"
    return "Beginner"


def dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def load(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value) if value else fallback
    except json.JSONDecodeError:
        return fallback


def first(values: list[str]) -> str | None:
    return values[0].strip() if values else None
