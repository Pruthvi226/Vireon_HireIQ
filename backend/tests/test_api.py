from .conftest import seed_and_login


RESUME = b"Test Candidate\ntest@example.com\nPython, FastAPI\nProjects: built an API\nEducation: Computer Science"
JOB = {"title": "Backend Engineer", "company": "Test Co", "description": "Build and deploy Python FastAPI services with SQL and Docker."}


def test_pagination_and_job_filtering(client):
    headers = seed_and_login(client)
    client.post("/api/demo/seed", headers=headers)
    candidates = client.get("/api/candidates?page=1&page_size=1", headers=headers)
    jobs = client.get("/api/jobs?page=1&page_size=1&status=open", headers=headers)
    assert candidates.status_code == 200
    assert set(candidates.json()) == {"items", "total", "page", "page_size"}
    assert len(candidates.json()["items"]) <= 1
    assert jobs.status_code == 200
    assert all(item["status"] == "open" for item in jobs.json()["items"])
    job_id = jobs.json()["items"][0]["id"]
    closed = client.patch(f"/api/jobs/{job_id}/status", headers=headers, json={"status": "closed"})
    assert closed.status_code == 200
    assert client.get(f"/api/jobs/{job_id}/rank-candidates", headers=headers).status_code == 409


def test_rbac_and_bulk_upload_isolation(client):
    recruiter = seed_and_login(client)
    client.post("/api/demo/seed", headers=recruiter)
    candidate = client.post("/api/auth/login", json={"email": "candidate@vireon.ai", "password": "candidate123"}).json()
    candidate_headers = {"Authorization": f"Bearer {candidate['access_token']}"}
    assert client.get("/api/admin/users", headers=candidate_headers).status_code == 403
    response = client.post("/api/resumes/bulk", headers=recruiter, files=[("files", ("good.txt", RESUME, "text/plain")), ("files", ("bad.exe", b"MZbad", "application/octet-stream"))])
    assert response.status_code == 200
    assert response.json()["succeeded"] == 1
    assert response.json()["failed"] == 1


def test_stage_transition_and_audit(client):
    headers = seed_and_login(client)
    seeded = client.post("/api/demo/seed", headers=headers).json()
    match_id = seeded["ranked"][0]["id"]
    response = client.patch(f"/api/match/{match_id}/stage", headers=headers, json={"pipeline_stage": "Interview"})
    assert response.status_code == 200
    assert response.json()["pipeline_stage"] == "Interview"
    admin_login = client.post("/api/auth/login", json={"email": "admin@vireon.ai", "password": "admin123"}).json()
    audit = client.get("/api/system/audit", headers={"Authorization": f"Bearer {admin_login['access_token']}"})
    assert any(item["action"] == "match_stage_changed" for item in audit.json())


def test_candidate_exports(client):
    headers = seed_and_login(client)
    client.post("/api/demo/seed", headers=headers)
    candidate_login = client.post("/api/auth/login", json={"email": "candidate@vireon.ai", "password": "candidate123"}).json()
    candidate_headers = {"Authorization": f"Bearer {candidate_login['access_token']}"}
    client.post("/api/resumes/text", headers=candidate_headers, json={"resume_text": RESUME.decode()})
    job_id = client.get("/api/jobs", headers=candidate_headers).json()["items"][0]["id"]
    export = client.get(f"/api/candidate/skill-gap/{job_id}/export?format=csv", headers=candidate_headers)
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]
