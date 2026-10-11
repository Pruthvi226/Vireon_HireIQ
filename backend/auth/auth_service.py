from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from app.config import DATA_DIR, DB_PATH, SQLITE_JOURNAL_MODE, DEVELOPMENT
from app.database import open_database
from fastapi import HTTPException, status

from auth.security import create_refresh_token, hash_password, hash_token, verify_password
from models.user_model import VALID_ROLES, User
from schemas.auth_schema import LoginRequest, RegisterRequest


def connect() -> sqlite3.Connection:
    return open_database(DB_PATH, SQLITE_JOURNAL_MODE)


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


        columns = {row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        if "failed_login_attempts" not in columns:
            db.execute("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0")
        if "locked_until" not in columns:
            db.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS refresh_tokens (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              token_hash TEXT NOT NULL UNIQUE,
              expires_at TEXT NOT NULL,
              revoked_at TEXT,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              token_hash TEXT NOT NULL UNIQUE,
              expires_at TEXT NOT NULL,
              used_at TEXT,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id, revoked_at);
            CREATE INDEX IF NOT EXISTS idx_reset_tokens_hash ON password_reset_tokens(token_hash, used_at);
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


def list_users(page: int = 1, page_size: int = 25, search: str = "", sort: str = "created_at") -> dict:
    with connect() as db:
        allowed_sort = sort if sort in {"created_at", "name", "email", "role"} else "created_at"
        where = " WHERE name LIKE ? OR email LIKE ? OR role LIKE ?" if search else ""
        params = [f"%{search}%"] * 3 if search else []
        total = db.execute(f"SELECT COUNT(*) AS count FROM users{where}", params).fetchone()["count"]
        rows = db.execute(f"SELECT id, name, email, role, company_name, created_at FROM users{where} ORDER BY {allowed_sort} DESC LIMIT ? OFFSET ?", [*params, page_size, (page - 1) * page_size]).fetchall()
        return {"items": [dict(row) for row in rows], "total": total, "page": page, "page_size": page_size}


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
            ON CONFLICT(email) DO NOTHING
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
        if cursor.rowcount == 0:
            raise HTTPException(status_code=409, detail="Email already registered")
        db.commit()
        user = db.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict(user)


def authenticate_user(payload: LoginRequest) -> dict:
    user = get_user_by_email(payload.email)
    now = datetime.utcnow()
    if user and user.get("locked_until") and datetime.fromisoformat(user["locked_until"]) > now:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account temporarily locked")
    if not user or not verify_password(payload.password, user["password_hash"]):
        if user:
            attempts = int(user.get("failed_login_attempts") or 0) + 1
            locked_until = (now + timedelta(minutes=15)).isoformat() if attempts >= 5 else None
            with connect() as db:
                db.execute("UPDATE users SET failed_login_attempts=?, locked_until=? WHERE id=?", (attempts, locked_until, user["id"]))
                db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    with connect() as db:
        db.execute("UPDATE users SET failed_login_attempts=0, locked_until=NULL WHERE id=?", (user["id"],))
        db.commit()
    return user


def issue_refresh_token(user_id: int) -> str:
    token = create_refresh_token()
    now = datetime.utcnow()
    with connect() as db:
        db.execute(
            "INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (user_id, hash_token(token), (now + timedelta(days=7)).isoformat(), now.isoformat()),
        )
        db.commit()
    return token


def rotate_refresh_token(token: str) -> dict:
    now = datetime.utcnow()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM refresh_tokens WHERE token_hash=? AND revoked_at IS NULL", (hash_token(token),)).fetchone()
        if not row or datetime.fromisoformat(row["expires_at"]) <= now:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        db.execute("UPDATE refresh_tokens SET revoked_at=? WHERE id=?", (now.isoformat(), row["id"]))
        user_row = db.execute("SELECT * FROM users WHERE id=?", (row["user_id"],)).fetchone()
        db.commit()
    if not user_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return dict(user_row)


def revoke_refresh_tokens(user_id: int) -> None:
    with connect() as db:
        db.execute("UPDATE refresh_tokens SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (datetime.utcnow().isoformat(), user_id))
        db.commit()


def create_password_reset_token(email: str) -> str:
    user = get_user_by_email(email)
    token = secrets.token_urlsafe(32)
    if not user:
        return token
    now = datetime.utcnow()
    with connect() as db:
        db.execute("INSERT INTO password_reset_tokens (user_id, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?)", (user["id"], hash_token(token), (now + timedelta(minutes=30)).isoformat(), now.isoformat()))
        db.commit()
    return token


def reset_password(token: str, password: str) -> None:
    now = datetime.utcnow()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM password_reset_tokens WHERE token_hash=? AND used_at IS NULL", (hash_token(token),)).fetchone()
        if not row or datetime.fromisoformat(row["expires_at"]) <= now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
        db.execute("UPDATE users SET password_hash=?, failed_login_attempts=0, locked_until=NULL WHERE id=?", (hash_password(password), row["user_id"]))
        db.execute("UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL", (now.isoformat(), row["user_id"]))
        db.execute("UPDATE refresh_tokens SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (now.isoformat(), row["user_id"]))
        db.commit()


def ensure_user(name: str, email: str, password: str, role: str, company_name: str | None = None) -> None:
    if get_user_by_email(email):
        return
    register_user(RegisterRequest(name=name, email=email, password=password, role=role, company_name=company_name))


def seed_demo_users() -> dict:
    if not DEVELOPMENT:
        raise RuntimeError("Demo accounts cannot be provisioned outside development")
    ensure_user("Vireon Admin", "admin@vireon.ai", "admin123", "ADMIN", "Vireon")
    ensure_user("QuickHyre Recruiter", "recruiter@vireon.ai", "recruiter123", "RECRUITER", "QuickHyre AI")
    ensure_user("Demo Candidate", "candidate@vireon.ai", "candidate123", "CANDIDATE", None)
    return {"message": "Demo users ready", "users": ["admin@vireon.ai", "recruiter@vireon.ai", "candidate@vireon.ai"]}
