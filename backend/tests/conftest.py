import os
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-chars")

import pytest
from fastapi.testclient import TestClient

import app.main as main
import auth.auth_service as auth_service


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DB_PATH", data_dir / "vireon.sqlite")
    monkeypatch.setattr(main, "RESUME_DIR", data_dir / "resumes")
    monkeypatch.setattr(auth_service, "DATA_DIR", data_dir)
    monkeypatch.setattr(auth_service, "DB_PATH", data_dir / "vireon.sqlite")
    main.CACHE.clear()
    main.RATE_BUCKETS.clear()
    main.CACHE_STATS.clear()
    main.HTTP_METRICS.clear()
    main.PATH_METRICS.clear()
    main.LATENCY_MS.clear()
    main.init_db()
    with TestClient(main.app) as test_client:
        yield test_client


def seed_and_login(client: TestClient, email: str = "recruiter@vireon.ai", password: str = "recruiter123") -> dict:
    client.post("/api/demo/seed-users")
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
