"""Shared runtime settings. Unsupported storage must never silently fall back."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
APP_ENV = os.getenv("APP_ENV", "local").lower()
DEVELOPMENT = APP_ENV in {"local", "dev", "development", "test"}
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL and not DATABASE_URL.startswith("sqlite:///"):
    raise RuntimeError("Only sqlite:/// DATABASE_URL is supported; PostgreSQL requires a repository migration")
DB_PATH = (Path(DATABASE_URL.removeprefix("sqlite:///")) if DATABASE_URL else
           Path(os.getenv("VIREON_DATA_DIR") or ROOT / "runtime") / "vireon_hireiq.sqlite")
DATA_DIR = DB_PATH.parent
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not JWT_SECRET_KEY and DEVELOPMENT:
    JWT_SECRET_KEY = secrets.token_urlsafe(48)
if len(JWT_SECRET_KEY) < 32 or JWT_SECRET_KEY.lower() in {
    "replace-with-a-long-random-secret-before-production", "change-me", "secret"
}:
    raise RuntimeError("JWT_SECRET_KEY must be a non-placeholder value of at least 32 characters")
SQLITE_JOURNAL_MODE = os.getenv("VIREON_SQLITE_JOURNAL_MODE", "MEMORY").upper()
if SQLITE_JOURNAL_MODE not in {"DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL"}:
    raise RuntimeError("Unsupported VIREON_SQLITE_JOURNAL_MODE; OFF is not permitted")
