"""Create an SQLite snapshot and copy uploaded resumes; never overwrite backups."""
import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import DATA_DIR, DB_PATH


def backup(source: Path, output: Path) -> Path:
    source, output = source.resolve(), output.resolve()
    if not source.is_file():
        raise ValueError("Source database does not exist")
    if output == source.parent or source.parent in output.parents:
        raise ValueError("Backup destination must be outside the live data directory")
    output.mkdir(parents=True, exist_ok=False)
    target = output / source.name
    origin = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)
    destination = sqlite3.connect(target)
    try:
        origin.backup(destination)
        if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Backup integrity check failed")
    finally:
        destination.close()
        origin.close()
    resumes = source.parent / "resumes"
    if resumes.exists():
        shutil.copytree(resumes, output / "resumes")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(f"Backup created: {backup(DB_PATH, args.output)}")
