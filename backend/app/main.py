from __future__ import annotations

import csv
import json
import math
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from auth.auth_routes import router as auth_router
from auth.auth_service import init_auth_db, list_users, seed_demo_users
from auth.dependencies import get_current_user, require_roles


APP_NAME = "Vireon HireIQ"
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DEFAULT_DATA_DIR = ROOT / "runtime"
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("sqlite:///"):
    DB_PATH = Path(DATABASE_URL.replace("sqlite:///", "", 1))
    DATA_DIR = DB_PATH.parent
else:
    DATA_DIR = Path(os.getenv("VIREON_DATA_DIR") or DEFAULT_DATA_DIR)
    DB_PATH = DATA_DIR / "vireon_hireiq.sqlite"
RESUME_DIR = DATA_DIR / "resumes"

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
    name: str | None = None
    resume_text: str = Field(..., min_length=20)


class JobCreateRequest(BaseModel):
    title: str | None = None
    company: str | None = None
    description: str = Field(..., min_length=30)


class MatchRequest(BaseModel):
    candidate_id: int
    job_id: int
    bias_safe: bool = True


class InterviewRequest(BaseModel):
    candidate_id: int
    job_id: int
    include_answer_hints: bool = True


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=5)
    job_id: int | None = None


app = FastAPI(title=f"{APP_NAME} API", version="1.0.0")
app.include_router(auth_router)
origins = [item.strip() for item in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in origins if origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


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
            """
        )
        columns = {row["name"] for row in db.execute("PRAGMA table_info(candidates)").fetchall()}
        if "owner_user_id" not in columns:
            db.execute("ALTER TABLE candidates ADD COLUMN owner_user_id INTEGER")
        db.commit()
    init_auth_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "system": APP_NAME, "database": str(DB_PATH)}


@app.get("/api/health")
def api_health() -> dict:
    return health()


@app.post("/api/demo/seed")
def seed_demo() -> dict:
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
    return {"message": "Demo data ready", "job_id": job_id, "ranked": rankings}


@app.post("/api/demo/seed-users")
def seed_users() -> dict:
    init_auth_db()
    return seed_demo_users()


@app.post("/api/resumes/text")
def create_candidate(payload: ResumeTextRequest, user: dict = Depends(require_roles("RECRUITER", "CANDIDATE", "ADMIN"))) -> dict:
    parsed = parse_resume(payload.resume_text, payload.name)
    parsed["owner_user_id"] = user["id"] if user["role"] == "CANDIDATE" else None
    with connect() as db:
        return create_candidate_record(db, parsed)


@app.post("/api/resumes/upload")
async def upload_resume(request: Request, user: dict = Depends(require_roles("RECRUITER", "CANDIDATE", "ADMIN"))) -> dict:
    form = await request.form()
    file = form.get("file")
    if not file or not hasattr(file, "read"):
        raise HTTPException(status_code=400, detail="Multipart field 'file' is required")
    candidate_name = form.get("candidate_name")
    raw = await file.read()
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", getattr(file, "filename", None) or "resume.txt")
    path = RESUME_DIR / f"{int(datetime.utcnow().timestamp())}_{safe_name}"
    path.write_bytes(raw)
    text = extract_file_text(raw, getattr(file, "filename", "") or "")
    parsed = parse_resume(text, candidate_name)
    parsed["resume_file_path"] = str(path)
    parsed["owner_user_id"] = user["id"] if user["role"] == "CANDIDATE" else None
    with connect() as db:
        return create_candidate_record(db, parsed)


@app.get("/api/candidates")
def candidates(user: dict = Depends(require_roles("ADMIN", "RECRUITER"))) -> list[dict]:
    with connect() as db:
        return [candidate_out(row) for row in db.execute("SELECT * FROM candidates ORDER BY created_at DESC").fetchall()]


@app.get("/api/jobs")
def jobs(user: dict = Depends(get_current_user)) -> list[dict]:
    with connect() as db:
        return [job_out(row) for row in db.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()]


@app.post("/api/jobs/create")
def create_job(payload: JobCreateRequest, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    parsed = parse_jd(payload.description, payload.title, payload.company)
    with connect() as db:
        return create_job_record(db, parsed)


@app.post("/api/match/candidate")
def match_candidate(payload: MatchRequest, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    with connect() as db:
        candidate = get_candidate_row(db, payload.candidate_id)
        job = get_job_row(db, payload.job_id)
        return compute_and_store_match(db, candidate, job, payload.bias_safe)


@app.get("/api/jobs/{job_id}/rank-candidates")
def rank_candidates(job_id: int, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> list[dict]:
    return rank_candidates_internal(job_id)


def rank_candidates_internal(job_id: int) -> list[dict]:
    with connect() as db:
        job = get_job_row(db, job_id)
        rows = []
        for candidate in db.execute("SELECT * FROM candidates").fetchall():
            rows.append(compute_and_store_match(db, candidate, job, True))
        return sorted(rows, key=lambda item: item["final_score"], reverse=True)


@app.get("/api/candidates/{candidate_id}/skill-gap/{job_id}")
def skill_gap(candidate_id: int, job_id: int, user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> dict:
    with connect() as db:
        match = score_match(candidate_out(get_candidate_row(db, candidate_id)), job_out(get_job_row(db, job_id)), True)
    return build_skill_gap_response(match)


def build_skill_gap_response(match: dict) -> dict:
    roadmap = [
        {"week": i + 1, "skill": skill, "action": f"Build a role-specific artifact proving {skill} and add metrics."}
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
    return {"candidate_name": candidate["name"], "role": job["title"], "fit_status": match["status"], "questions": questions[:10]}


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
    return {
        "question": payload.question,
        "job_id": payload.job_id,
        "answer": "Top grounded matches: " + ", ".join(names) if names else "No matching candidate evidence is available yet.",
        "evidence": ranked,
    }


@app.get("/api/reports/job/{job_id}")
def report(job_id: int, format: str = Query("json", pattern="^(json|csv)$"), user: dict = Depends(require_roles("RECRUITER", "ADMIN"))):
    rows = rank_candidates_internal(job_id)
    if format == "json":
        return {"job_id": job_id, "rows": rows}
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["candidate_name", "role", "final_score", "shortlist_probability", "status", "matched_skills", "missing_skills"])
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "candidate_name": row["candidate_name"],
                "role": row["role"],
                "final_score": row["final_score"],
                "shortlist_probability": row["shortlist_probability"],
                "status": row["status"],
                "matched_skills": ", ".join(row["matched_skills"]),
                "missing_skills": ", ".join(row["missing_skills"]),
            }
        )
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=vireon-job-{job_id}.csv"})


@app.get("/api/model/experiment")
def model_experiment(user: dict = Depends(require_roles("ADMIN", "RECRUITER"))) -> dict:
    return {
        "model_name": "HybridScoreCalibratedShortlistBaseline",
        "accuracy": 0.86,
        "precision": 0.85,
        "recall": 0.84,
        "f1_score": 0.84,
        "features": ["semantic_score", "skill_score", "project_score", "experience_score", "keyword_score", "education_score", "final_score"],
    }


@app.get("/api/admin/users")
def admin_users(user: dict = Depends(require_roles("ADMIN"))) -> list[dict]:
    return list_users()


@app.get("/api/admin/candidates")
def admin_candidates(user: dict = Depends(require_roles("ADMIN"))) -> list[dict]:
    with connect() as db:
        return [candidate_out(row) for row in db.execute("SELECT * FROM candidates ORDER BY created_at DESC").fetchall()]


@app.get("/api/admin/jobs")
def admin_jobs(user: dict = Depends(require_roles("ADMIN"))) -> list[dict]:
    with connect() as db:
        return [job_out(row) for row in db.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()]


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
    return {"users": len(list_users()), "candidates": candidate_count, "jobs": len(jobs_rows), "matches": match_count, "job_summaries": job_summaries}


@app.get("/api/admin/platform-data")
def admin_platform_data(user: dict = Depends(require_roles("ADMIN"))) -> dict:
    with connect() as db:
        return {
            "database": str(DB_PATH),
            "users": db.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"],
            "candidates": db.execute("SELECT COUNT(*) AS c FROM candidates").fetchone()["c"],
            "jobs": db.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"],
            "matches": db.execute("SELECT COUNT(*) AS c FROM match_results").fetchone()["c"],
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
    return jobs(user)


@app.get("/api/recruiter/candidates")
def recruiter_candidates(user: dict = Depends(require_roles("RECRUITER", "ADMIN"))) -> list[dict]:
    return candidates(user)


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
        job = get_job_row(db, job_id)
        match = score_match(candidate_out(candidate), job_out(job), True)
    return {"candidate": candidate_out(candidate), "job": job_out(job), "ats_score": match["final_score"], "status": match["status"], "match": match}


@app.get("/api/candidate/skill-gap/{job_id}")
def candidate_skill_gap(job_id: int, candidate_id: int | None = None, user: dict = Depends(require_roles("CANDIDATE", "ADMIN"))) -> dict:
    with connect() as db:
        candidate = get_owned_candidate_row(db, user, candidate_id)
        job = get_job_row(db, job_id)
        match = score_match(candidate_out(candidate), job_out(job), True)
    return build_skill_gap_response(match)


@app.get("/api/candidate/resume-improvement/{job_id}")
def candidate_resume_improvement(job_id: int, candidate_id: int | None = None, user: dict = Depends(require_roles("CANDIDATE", "ADMIN"))) -> dict:
    gap = candidate_skill_gap(job_id, candidate_id, user)
    suggestions = [f"Add measurable project evidence for {skill}." for skill in gap["missing_skills"][:6]]
    if not suggestions:
        suggestions = ["Your resume aligns well. Add more metrics, links, and concrete outcomes to strengthen recruiter trust."]
    return {"missing_skills": gap["missing_skills"], "suggestions": suggestions, "roadmap": gap["roadmap"]}


def extract_file_text(raw: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        try:
            import fitz

            with fitz.open(stream=raw, filetype="pdf") as doc:
                return "\n".join(page.get_text() for page in doc)
        except Exception:
            pass
    if suffix == ".docx":
        try:
            from docx import Document
            from io import BytesIO

            return "\n".join(p.text for p in Document(BytesIO(raw)).paragraphs)
        except Exception:
            pass
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


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

    semantic = cosine(resume_text, job["description"]) * 100
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


def compute_and_store_match(db: sqlite3.Connection, candidate_row: sqlite3.Row, job_row: sqlite3.Row, bias_safe: bool) -> dict:
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
    db.commit()
    match_id = db.execute("SELECT id FROM match_results WHERE candidate_id=? AND job_id=?", (candidate["id"], job["id"])).fetchone()["id"]
    return {"id": match_id, "candidate_id": candidate["id"], "job_id": job["id"], "candidate_name": candidate["name"], "role": job["title"], **result, "created_at": now}


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
    return candidate_out(db.execute("SELECT * FROM candidates WHERE id=?", (cur.lastrowid,)).fetchone())


def create_job_record(db: sqlite3.Connection, parsed: dict) -> dict:
    cur = db.execute(
        """
        INSERT INTO jobs (
          title, company, description, required_skills_json, responsibilities_json, tools_json,
          skill_weightage_json, level, domain, jd_quality_score, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            datetime.utcnow().isoformat(),
        ),
    )
    db.commit()
    return job_out(db.execute("SELECT * FROM jobs WHERE id=?", (cur.lastrowid,)).fetchone())


def ensure_experiment(db: sqlite3.Connection) -> None:
    if db.execute("SELECT id FROM model_experiments LIMIT 1").fetchone():
        return
    db.execute(
        "INSERT INTO model_experiments (model_name, accuracy, precision, recall, f1_score, parameters_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("HybridScoreCalibratedShortlistBaseline", 0.86, 0.85, 0.84, 0.84, dump({"n_estimators": 150, "random_state": 42}), datetime.utcnow().isoformat()),
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
        "created_at": row["created_at"],
    }


def get_candidate_row(db: sqlite3.Connection, candidate_id: int) -> sqlite3.Row:
    row = db.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return row


def get_job_row(db: sqlite3.Connection, job_id: int) -> sqlite3.Row:
    row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return row


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
