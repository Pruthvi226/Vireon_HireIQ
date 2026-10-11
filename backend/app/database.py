"""SQLite connections that commit/roll back and close on context exit."""
import sqlite3
from pathlib import Path


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def open_database(path: Path, journal_mode: str) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5, factory=ClosingConnection)
    try:
        db.execute(f"PRAGMA journal_mode={journal_mode}")
        db.execute("PRAGMA synchronous=NORMAL")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=5000")
        db.row_factory = sqlite3.Row
        return db
    except Exception:
        db.close()
        raise
