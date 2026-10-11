import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("updates,message", [
    ({"APP_ENV": "production", "JWT_SECRET_KEY": ""}, "JWT_SECRET_KEY"),
    ({"DATABASE_URL": "postgresql://example.invalid/db"}, "Only sqlite:///"),
    ({"VIREON_SQLITE_JOURNAL_MODE": "OFF"}, "OFF is not permitted"),
])
def test_invalid_runtime_configuration_fails_closed(updates, message):
    env = dict(os.environ)
    env.update({"DATABASE_URL": "", "VIREON_SQLITE_JOURNAL_MODE": "MEMORY", "JWT_SECRET_KEY": "test-config-secret-with-more-than-32-characters", "APP_ENV": "test"})
    env.update(updates)
    result = subprocess.run([sys.executable, "-c", "import app.config"], cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert message in result.stderr
