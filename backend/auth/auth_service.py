from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException, status

from auth.security import hash_password, verify_password
from models.user_model import VALID_ROLES, User
from schemas.auth_schema import LoginRequest, RegisterRequest


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
SQLITE_JOURNAL_MODE = os.getenv("VIREON_SQLITE_JOURNAL_MODE", "MEMORY").upper()
if SQLITE_JOURNAL_MODE not in {"DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"}:
    SQLITE_JOURNAL_MODE = "MEMORY"


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(f"PRAGMA journal_mode={SQLITE_JOURNAL_MODE}")
    except sqlite3.OperationalError:
        conn.close()
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=MEMORY")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db() -> None:
    with connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              email TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL CHECK(role IN ('ADMIN', 'RECRUITER', 'CANDIDATE')),
              company_name TEXT,
              created_at TEXT NOT NULL
            )
            """
        )
        db.commit()


def row_to_user(row: sqlite3.Row | None) -> User | None:
    return User.from_row(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    with connect() as db:
        row = db.execute("SELECT * FROM users WHERE lower(email)=lower(?)", (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with connect() as db:
        row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def list_users() -> list[dict]:
    with connect() as db:
        rows = db.execute("SELECT id, name, email, role, company_name, created_at FROM users ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "company_name": user.get("company_name"),
        "created_at": user["created_at"],
    }


def register_user(payload: RegisterRequest) -> dict:
    role = payload.role.upper()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    if get_user_by_email(payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO users (name, email, password_hash, role, company_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name.strip(),
                payload.email.lower(),
                hash_password(payload.password),
                role,
                payload.company_name.strip() if payload.company_name else None,
                datetime.utcnow().isoformat(),
            ),
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict(user)


def authenticate_user(payload: LoginRequest) -> dict:
    user = get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return user


def ensure_user(name: str, email: str, password: str, role: str, company_name: str | None = None) -> None:
    if get_user_by_email(email):
        return
    register_user(RegisterRequest(name=name, email=email, password=password, role=role, company_name=company_name))


def seed_demo_users() -> dict:
    ensure_user("Vireon Admin", "admin@vireon.ai", "admin123", "ADMIN", "Vireon")
    ensure_user("QuickHyre Recruiter", "recruiter@vireon.ai", "recruiter123", "RECRUITER", "QuickHyre AI")
    ensure_user("Demo Candidate", "candidate@vireon.ai", "candidate123", "CANDIDATE", None)
    return {"message": "Demo users ready", "users": ["admin@vireon.ai", "recruiter@vireon.ai", "candidate@vireon.ai"]}
