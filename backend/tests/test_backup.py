import sqlite3

import pytest

from scripts.backup import backup


def test_backup_preserves_database_and_resumes(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    source = live / "vireon.sqlite"
    db = sqlite3.connect(source)
    db.execute("CREATE TABLE example (value TEXT)")
    db.execute("INSERT INTO example VALUES ('retained')")
    db.commit()
    db.close()
    (live / "resumes").mkdir()
    (live / "resumes" / "sample.txt").write_text("Resume evidence")
    output = backup(source, tmp_path / "snapshot")
    restored = sqlite3.connect(output / source.name)
    try:
        assert restored.execute("SELECT value FROM example").fetchone()[0] == "retained"
    finally:
        restored.close()
    assert (output / "resumes" / "sample.txt").read_text() == "Resume evidence"
    with pytest.raises(FileExistsError):
        backup(source, output)
    with pytest.raises(ValueError):
        backup(source, live / "backup")
