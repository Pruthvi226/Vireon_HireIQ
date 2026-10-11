import io
import sqlite3
import zipfile

import pytest

import app.main as main
from auth.security import create_access_token
from .conftest import seed_and_login


@pytest.mark.parametrize("role", ["ADMIN", "RECRUITER"])
def test_public_registration_cannot_create_staff(client, role):
    response = client.post("/api/auth/register", json={"name": "Attacker", "email": "attacker@example.com", "password": "password123", "role": role})
    assert response.status_code == 403
    assert client.post("/api/auth/login", json={"email": "attacker@example.com", "password": "password123"}).status_code == 401


def test_candidate_signup_and_ownership(client):
    registered = client.post("/api/auth/register", json={"name": "Jane Doe", "email": "jane@example.com", "password": "password123"})
    assert registered.status_code == 200
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    recruiter = seed_and_login(client)
    seeded = client.post("/api/demo/seed", headers=recruiter).json()
    other_id = seeded["ranked"][0]["candidate_id"]
    assert client.get(f"/api/candidate/ats-score?job_id={seeded['job_id']}&candidate_id={other_id}", headers=headers).status_code == 404
    assert client.get("/api/candidates", headers=headers).status_code == 403


def test_production_cannot_seed(client, monkeypatch):
    monkeypatch.setattr(main, "APP_ENV", "production")
    assert client.post("/api/demo/seed").status_code == 404
    assert client.post("/api/demo/seed-users").status_code == 404


def test_malformed_subject_is_unauthorized(client):
    headers = {"Authorization": f"Bearer {create_access_token('not-a-number')}"}
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_password_byte_limit(client):
    response = client.post("/api/auth/register", json={"name": "Jane", "email": "jane@example.com", "password": "é" * 40})
    assert response.status_code == 422


def test_whitespace_names_are_rejected(client):
    response = client.post("/api/auth/register", json={"name": "   ", "email": "jane@example.com", "password": "password123"})
    assert response.status_code == 422


def test_transport_body_budget_returns_413(client):
    headers = seed_and_login(client)
    headers["Content-Length"] = str(main.MAX_BULK_BYTES + 1024 * 1024 + 1)
    assert client.post("/api/resumes/upload", headers=headers, content=b"unused").status_code == 413


def test_demo_metrics_are_explicitly_unevaluated(client):
    headers = seed_and_login(client)
    client.post("/api/demo/seed", headers=headers)
    report = client.get("/api/model/experiment", headers=headers).json()
    assert report["evaluation_status"] == "unevaluated_fixture"
    assert report["accuracy"] == 0


@pytest.mark.parametrize("filename,content", [("bad.exe", b"MZbad"), ("bad.pdf", b"%PDF broken document"), ("empty.txt", b"")])
def test_bad_uploads_return_client_error_and_store_nothing(client, filename, content):
    headers = seed_and_login(client)
    response = client.post("/api/resumes/upload", headers=headers, files={"file": (filename, content)})
    assert response.status_code == 400
    assert client.get("/api/candidates", headers=headers).json()["total"] == 0
    assert list(main.RESUME_DIR.iterdir()) == []


def test_upload_size_limit(client, monkeypatch):
    headers = seed_and_login(client)
    monkeypatch.setattr(main, "MAX_RESUME_BYTES", 32)
    response = client.post("/api/resumes/upload", headers=headers, files={"file": ("resume.txt", b"x" * 100)})
    assert response.status_code == 400


def test_zip_decompression_limits(client):
    headers = seed_and_login(client)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bomb.txt", "x" * 100000)
    response = client.post("/api/resumes/bulk", headers=headers, files={"files": ("resumes.zip", buffer.getvalue())})
    assert response.status_code == 200
    assert response.json()["failed"] == 1
    assert response.json()["succeeded"] == 0


def test_stage_update_invalidates_cached_rankings(client):
    headers = seed_and_login(client)
    seeded = client.post("/api/demo/seed", headers=headers).json()
    match_id = seeded["ranked"][0]["id"]
    assert client.patch(f"/api/match/{match_id}/stage", headers=headers, json={"pipeline_stage": "Interview"}).status_code == 200
    ranking = client.get(f"/api/jobs/{seeded['job_id']}/rank-candidates", headers=headers).json()
    assert next(row for row in ranking if row["id"] == match_id)["pipeline_stage"] == "Interview"


def test_candidate_job_list_only_exposes_open_jobs(client):
    recruiter = seed_and_login(client)
    client.post("/api/jobs/create", headers=recruiter, json={"description": "Build Python FastAPI services with SQL databases", "status": "draft"})
    candidate = seed_and_login(client, "candidate@vireon.ai", "candidate123")
    assert client.get("/api/jobs?status=draft", headers=candidate).json()["total"] == 0


def test_candidate_cannot_inspect_unpublished_job_by_id(client):
    recruiter = seed_and_login(client)
    job = client.post("/api/jobs/create", headers=recruiter, json={"description": "Build Python FastAPI services with SQL databases", "status": "draft"}).json()
    candidate = seed_and_login(client, "candidate@vireon.ai", "candidate123")
    resume = client.post("/api/resumes/text", headers=candidate, json={"resume_text": "Python FastAPI backend API engineering evidence"}).json()
    assert client.get(f"/api/candidate/ats-score?job_id={job['id']}&candidate_id={resume['id']}", headers=candidate).status_code == 404


def test_legacy_candidate_schema_gets_ownership_before_index(client):
    with main.connect() as db:
        db.execute("DROP INDEX idx_candidates_owner_created")
        db.execute("ALTER TABLE candidates DROP COLUMN owner_user_id")
    main.init_db()
    with main.connect() as db:
        assert "owner_user_id" in {row["name"] for row in db.execute("PRAGMA table_info(candidates)")}
        assert db.execute("SELECT name FROM sqlite_master WHERE name='idx_candidates_owner_created'").fetchone()


def test_connection_is_closed_after_context(client):
    with main.connect() as db:
        db.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        db.execute("SELECT 1")


def test_csv_export_neutralizes_formula_names(client):
    headers = seed_and_login(client)
    seeded = client.post("/api/demo/seed", headers=headers).json()
    client.post("/api/resumes/text", headers=headers, json={"name": "=1+1", "resume_text": "Python FastAPI SQL backend API engineer"})
    exported = client.get(f"/api/reports/job/{seeded['job_id']}?format=csv", headers=headers)
    assert "'=1+1" in exported.text
